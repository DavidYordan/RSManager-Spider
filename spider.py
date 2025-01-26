import asyncio
import subprocess
import json
import socket
import time
from collections import deque

from async_tiktok_data_manager import AsyncTikTokDataManager
from custom_globals import Globals
from name_space import NamespaceManager

class Session(object):
    """封装 TikTokApi 会话及其相关代理信息，并使用网络命名空间隔离流量。"""
    def __init__(self, namespace_manager: NamespaceManager, data_manager: AsyncTikTokDataManager, session_id: int, timeout=60):
        self.namespace_manager = namespace_manager
        self.data_manager = data_manager
        self.namespace = None
        self.proxy = None
        self.playwright_process = None
        self.in_use = False
        self.user = f'Session-{session_id}'  # 为每个会话分配唯一的用户标识
        self.timeout = timeout  # 会话重建的超时时间（秒）
        self.last_active = time.time()  # 用于健康检查
        self.rebuilding = False

    async def create(self):
        """初始化会话，包括分配命名空间和代理，并启动Playwright会话在该命名空间内。"""
        Globals.logger.debug("Creating session...", self.user)
        # Acquire a namespace
        self.namespace = await self.namespace_manager.acquire_namespace()
        if not self.namespace:
            raise Exception("No available namespaces.")

        # Get an available proxy
        self.proxy = await self.data_manager.get_available_proxy()
        if not self.proxy:
            await self.namespace_manager.release_namespace(self.namespace)
            self.namespace = None
            raise Exception("No available proxies.")

        local_ip = await self.get_local_ip()
        if not local_ip:
            await self.close()
            raise Exception("Failed to get local IP.")

        # Prepare environment variables
        proxy_url = f"http://{local_ip}:{self.proxy['current_port']}"

        # Construct the command to execute with environment variables
        cmd = (
            f"export http_proxy={proxy_url} && "
            f"export https_proxy={proxy_url} && "
            f"python3 playwright_session.py"
        )

        # Start the Playwright process in the namespace with the environment variables
        self.playwright_process = subprocess.Popen(
            ["ip", "netns", "exec", self.namespace, "bash", "-c", cmd],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1  # Line buffering
        )

        # Asynchronously log child process stderr
        asyncio.create_task(self.log_child_stderr())

        # 更新最后活动时间
        self.last_active = time.time()

    async def get_local_ip(self):
        """获取本机 IP 地址。"""
        try:
            # 创建一个 socket，连接到公网 IP（例如 8.8.8.8），获取本地绑定的 IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))  # 公网 DNS，目标 IP 不会实际发送数据
                return s.getsockname()[0]
        except Exception as e:
            Globals.logger.error(f"获取本机 IP 地址时出错: {e}", self.user)
            return None

    async def log_child_stderr(self):
        """异步读取子进程的stderr并记录日志"""
        while True:
            if self.playwright_process and self.playwright_process.stderr:
                line = await asyncio.get_event_loop().run_in_executor(None, self.playwright_process.stderr.readline)
                if line:
                    Globals.logger.error(f"Child process stderr: {line.strip()}", self.user)
                else:
                    break
            else:
                await asyncio.sleep(0.2)
                break

    async def close(self):
        """关闭会话并释放资源。"""
        Globals.logger.debug("Closing session...", self.user)
        # Mark proxy as not in use
        if self.proxy:
            await self.data_manager.set_proxy_in_use(self.proxy['id'], False)
            self.proxy = None  # 确保代理被释放

        # Terminate Playwright process
        if self.playwright_process:
            self.playwright_process.terminate()
            try:
                await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(None, self.playwright_process.wait),
                    timeout=10
                )
                Globals.logger.debug("Playwright process terminated gracefully.", self.user)
            except asyncio.TimeoutError:
                Globals.logger.warning("Playwright进程终止超时，强制杀死进程", self.user)
                self.playwright_process.kill()
                await asyncio.get_event_loop().run_in_executor(None, self.playwright_process.wait)
            self.playwright_process = None  # 确保进程被释放

        # Release the namespace back to NamespaceManager
        if self.namespace:
            await self.namespace_manager.release_namespace(self.namespace)
            self.namespace = None

        self.in_use = False  # 更新会话状态

    async def rebuild_session(self):
        async with Globals.session_lock:
            if self.rebuilding:
                return
            self.rebuilding = True

            """重建会话，包括清理现有资源并重新初始化。"""
            Globals.logger.debug("Rebuilding session...", self.user)
            try:
                # 关闭当前会话资源
                await self.close()

                # 检查资源是否已释放
                if self.in_use:
                    Globals.logger.error("Session still in use after close. Aborting rebuild.", self.user)
                    return

                # 尝试重建会话，并设置超时
                await asyncio.wait_for(self.create(), timeout=self.timeout)
                self.last_active = time.time()
                Globals.logger.debug("Session rebuilt successfully.", self.user)
            except asyncio.TimeoutError:
                Globals.logger.error("Session rebuild timed out. Forcing cleanup.", self.user)
                await self.force_cleanup()
                raise
            except Exception as e:
                Globals.logger.error(f"Failed to rebuild session: {str(e)}", self.user)
                raise
            finally:
                self.rebuilding = False

    async def force_cleanup(self):
        """强制清理会话资源，包括从进程层面杀死子进程。"""
        Globals.logger.debug("Force cleaning up session...", self.user)
        if self.playwright_process:
            self.playwright_process.kill()
            await asyncio.get_event_loop().run_in_executor(None, self.playwright_process.wait)
            self.playwright_process = None
        if self.namespace:
            await self.namespace_manager.release_namespace(self.namespace)
            self.namespace = None
        if self.proxy:
            await self.data_manager.set_proxy_in_use(self.proxy['id'], False)
            self.proxy = None
        self.in_use = False

    async def send_command(self, command: dict):
        """向子进程发送命令并等待响应。"""
        if not self.playwright_process or self.playwright_process.poll() is not None:
            raise Exception("Playwright子进程未运行")

        # 发送命令
        command_str = json.dumps(command) + "\n"
        self.playwright_process.stdin.write(command_str)
        self.playwright_process.stdin.flush()

        # 监听响应
        try:
            response = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, self.playwright_process.stdout.readline),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            raise Exception("Timed out waiting for response from child process")

        if not response:
            raise Exception("No response from child process")

        # 更新最后活动时间
        self.last_active = time.time()

        # 尝试解析 JSON
        try:
            parsed_response = json.loads(response)
            return parsed_response
        except json.JSONDecodeError:
            # 非 JSON 报文，直接打印
            Globals.logger.info(f"Non-JSON message from child process: {response}", self.user)
            return None

class Spider(object):
    def __init__(self, max_concurrent_sessions=5):
        self.data_manager = AsyncTikTokDataManager()
        self.namespace_manager = NamespaceManager(max_namespaces=max_concurrent_sessions)
        self.user = 'Spider'
        self.account_queue = deque()
        self.max_concurrent_sessions = max_concurrent_sessions
        self.semaphore = asyncio.Semaphore(self.max_concurrent_sessions)
        self.session_pool = []
        self.session_id_counter = 0  # 用于给会话分配唯一的ID
        self.health_check_interval = 3600  # 健康检查的间隔时间（秒）

    async def initialize_namespace_and_sessions(self):
        """初始化网络命名空间和会话池。"""
        Globals.logger.debug("Initializing namespace and sessions...", self.user)
        # 创建 sessions up to max_concurrent_sessions
        for _ in range(self.max_concurrent_sessions):
            session = self.create_new_session()
            try:
                await session.create()
                self.session_pool.append(session)
                Globals.logger.debug(f"Session {session.user} created and added to pool.", self.user)
            except Exception as e:
                Globals.logger.error(f"Failed to create session: {e}", self.user)

    def create_new_session(self):
        """创建一个新的会话实例并分配唯一ID。"""
        self.session_id_counter += 1
        return Session(namespace_manager=self.namespace_manager, data_manager=self.data_manager, session_id=self.session_id_counter)

    async def main(self):
        await self.initialize_namespace_and_sessions()
        # 启动后台任务以监控和维护会话池
        asyncio.create_task(self.monitor_sessions())
        asyncio.create_task(self.health_check_sessions())
        try:
            while True:
                accounts = await self.data_manager.get_active_tiktok_accounts()
                if not accounts:
                    Globals.logger.debug("No active accounts found. Sleeping for 5 seconds.", self.user)
                    await asyncio.sleep(5)
                    continue
                await self.process_accounts(accounts)
        finally:
            await self.close_all_sessions()

    async def monitor_sessions(self):
        """监控会话池，确保始终有max_concurrent_sessions个会话在运行。"""
        while True:
            async with Globals.session_lock:
                active_sessions = len(self.session_pool)
                if active_sessions < self.max_concurrent_sessions:
                    to_create = self.max_concurrent_sessions - active_sessions
                    Globals.logger.debug(f"Session pool below max. Creating {to_create} new sessions.", self.user)
                    for _ in range(to_create):
                        session = self.create_new_session()
                        try:
                            await session.create()
                            self.session_pool.append(session)
                            Globals.logger.debug(f"Session {session.user} created and added to pool.", self.user)
                        except Exception as e:
                            Globals.logger.error(f"Failed to create session: {e}", self.user)
            await asyncio.sleep(10)  # 每10秒检查一次

    async def health_check_sessions(self):
        """定期检查会话的健康状态，如果发现会话长时间未活动，则重建会话。"""
        while True:
            async with Globals.session_lock:
                for session in self.session_pool:
                    if time.time() - session.last_active > session.timeout:
                        Globals.logger.warning(f"Session {session.user} is unresponsive. Rebuilding...", self.user)
                        asyncio.create_task(session.rebuild_session())
            await asyncio.sleep(self.health_check_interval)

    async def close_all_sessions(self):
        """关闭所有会话并清理资源。"""
        Globals.logger.debug("Closing all sessions...", self.user)
        for session in self.session_pool:
            await session.close()
        self.session_pool = []

    async def process_accounts(self, accounts):
        """处理账户队列中的所有账户。"""
        for account in accounts:
            if account not in self.account_queue:
                self.account_queue.append(account)

        tasks = []
        while self.account_queue:
            account = self.account_queue.popleft()
            task = asyncio.create_task(self.process_account_semaphore(account))
            tasks.append(task)

        if tasks:
            await asyncio.gather(*tasks)

    async def process_account_semaphore(self, account):
        """使用信号量限制并发会话数量。"""
        async with self.semaphore:
            await self.process_account(account)

    async def get_available_session(self):
        """获取一个可用的会话。如果没有可用会话，则等待。"""
        while True:
            async with Globals.session_lock:
                for session in self.session_pool:
                    if not session.in_use:
                        session.in_use = True
                        return session
            await asyncio.sleep(0.1)

    async def release_session(self, session):
        """释放一个会话，使其可供其他任务使用。"""
        async with Globals.session_lock:
            session.in_use = False

    async def process_account(self, account):
        """处理单个账户，包括获取用户信息和视频。"""
        unique_id = account['unique_id']
        tiktok_id = account['tiktok_id']
        account_name = account['account_name']

        session = await self.get_available_session()
       
        try:
            # 发送获取用户信息的命令到子进程
            Globals.logger.info(f"{session.namespace} with {session.proxy['id']} {session.proxy['current_port']} is processing account {unique_id}", self.user)
            command = {"action": "get_user_info", "username": unique_id, "tiktok_id": tiktok_id}
            user_info = await session.send_command(command)
            if user_info:
                if user_info.get('status') != 'success':
                    message = user_info.get('message', 'Unknown error')
                    if message == "'user'":
                        await self.data_manager.set_comments(account_name, '账号不存在')
                        return
                    elif message == "'id'":
                        await self.data_manager.set_comments(account_name, '账号不存在')
                        return
                    elif 'No response from child process' in message:
                        await session.rebuild_session()
                        return
                    elif 'TikTok returned an empty response' in message:
                        if session.proxy:
                            await self.data_manager.increase_proxy_fail(session.proxy['id'])
                            await self.data_manager.increase_proxy_fail(session.proxy['id'])
                        await session.rebuild_session()
                        return
                    else:
                        Globals.logger.error(f"Unknown error getting user info: {message}", self.user)
                        if session.proxy:
                            await self.data_manager.increase_proxy_fail(session.proxy['id'])
                        await session.rebuild_session()
                        return

                await self.data_manager.insert_or_update_tiktok_account(account_name, user_info['data'])

                # 发送获取用户视频的命令到子进程
                command = {"action": "get_user_videos", "username": unique_id}
                user_videos = await session.send_command(command)
                if user_videos and len(user_videos) > 0:
                    await self.data_manager.insert_or_update_tiktok_video_details(user_videos['data'])

            # 成功，增加代理的 success_count
            if session.proxy:
                await self.data_manager.increase_proxy_success(session.proxy['id'])
        except Exception as e:
            Globals.logger.error(f"Error processing account {unique_id}: {e}", self.user)
            # 失败，增加代理的 fail_count，并重建会话
            if session.proxy:
                await self.data_manager.increase_proxy_fail(session.proxy['id'])
            await session.rebuild_session()
        finally:
            await asyncio.sleep(3)
            await self.release_session(session)
