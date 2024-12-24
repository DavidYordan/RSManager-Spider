import asyncio
import subprocess
import json
import socket
from collections import deque

from async_tiktok_data_manager import AsyncTikTokDataManager
from custom_globals import Globals
from name_space import NamespaceManager

class Session(object):
    """封装 TikTokApi 会话及其相关代理信息，并使用网络命名空间隔离流量。"""
    def __init__(self, namespace_manager: NamespaceManager, data_manager: AsyncTikTokDataManager):
        self.namespace_manager = namespace_manager
        self.data_manager = data_manager
        self.namespace = None
        self.proxy = None
        self.playwright_process = None
        self.in_use = False
        self.user = 'Session'  # 确保 user 属性被初始化

    async def create(self):
        """初始化会话，包括分配命名空间和代理，并启动Playwright会话在该命名空间内。"""
        # Acquire a namespace
        self.namespace = self.namespace_manager.acquire_namespace()
        if not self.namespace:
            raise Exception("No available namespaces.")

        # Get an available proxy
        self.proxy = await self.data_manager.get_available_proxy()
        if not self.proxy:
            self.namespace_manager.release_namespace(self.namespace)
            raise Exception("No available proxies.")

        # Mark proxy as in use
        await self.data_manager.set_proxy_in_use(self.proxy['id'], True)

        local_ip = await self.get_local_ip()

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

    async def get_local_ip(self):
        """获取本机 IP 地址。"""
        try:
            # 创建一个 socket，连接到公网 IP（例如 8.8.8.8），获取本地绑定的 IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))  # 公网 DNS，目标 IP 不会实际发送数据
                return s.getsockname()[0]
        except Exception as e:
            print(f"获取本机 IP 地址时出错: {e}")
            return None

    async def log_child_stderr(self):
        """异步读取子进程的stderr并记录日志"""
        while True:
            if self.playwright_process.stderr:
                line = await asyncio.get_event_loop().run_in_executor(None, self.playwright_process.stderr.readline)
                if line:
                    Globals.logger.error(f"Child process stderr: {line.strip()}", self.user)
                else:
                    break
            else:
                await asyncio.sleep(0.2)
                break

    # async def close(self):
    #     """关闭会话并释放资源。"""
    #     # Mark proxy as not in use
    #     if self.proxy:
    #         await self.data_manager.set_proxy_in_use(self.proxy['id'], False)

    #     # Terminate Playwright process
    #     if self.playwright_process:
    #         self.playwright_process.terminate()
    #         self.playwright_process.wait()

    #     # Release the namespace back to NamespaceManager
    #     if self.namespace:
    #         self.namespace_manager.release_namespace(self.namespace)
    #         self.namespace = None

    #     self.in_use = False

    async def close(self):
        """关闭会话并释放资源。"""
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
            except asyncio.TimeoutError:
                Globals.logger.warning("Playwright进程终止超时，强制杀死进程", self.user)
                self.playwright_process.kill()
                await asyncio.get_event_loop().run_in_executor(None, self.playwright_process.wait)
            self.playwright_process = None  # 确保进程被释放

        # Release the namespace back to NamespaceManager
        if self.namespace:
            self.namespace_manager.release_namespace(self.namespace)
            self.namespace = None

        self.in_use = False  # 更新会话状态

    # async def rebuild_session(self):
    #     """重建会话，包括清理现有资源并重新初始化。"""
        
    #     Globals.logger.debug("Rebuilding session...", self.user)
    #     # 关闭当前会话资源
    #     await self.close()
        
    #     # 调用 create 方法重新初始化会话
    #     try:
    #         await self.create()
    #     except Exception as e:
    #         Globals.logger.error(f"Failed to rebuild session: {str(e)}", self.user)
    #         raise

    async def rebuild_session(self):
        """重建会话，包括清理现有资源并重新初始化。"""

        Globals.logger.debug("Rebuilding session...", self.user)
        # 关闭当前会话资源
        await self.close()

        # 检查资源是否已释放
        if self.in_use:
            Globals.logger.error("Session still in use after close. Aborting rebuild.", self.user)
            return

        # 调用 create 方法重新初始化会话
        try:
            await self.create()
        except Exception as e:
            Globals.logger.error(f"Failed to rebuild session: {str(e)}", self.user)
            raise

    async def send_command(self, command: dict):
        """向子进程发送命令并等待响应。"""
        if not self.playwright_process or self.playwright_process.poll() is not None:
            raise Exception("Playwright子进程未运行")

        # 发送命令
        command_str = json.dumps(command) + "\n"
        self.playwright_process.stdin.write(command_str)
        self.playwright_process.stdin.flush()

        # 监听响应
        while True:
            response = await asyncio.get_event_loop().run_in_executor(None, self.playwright_process.stdout.readline)
            if not response:
                raise Exception("No response from child process")

            # 尝试解析 JSON
            try:
                parsed_response = json.loads(response)
                return parsed_response
            except json.JSONDecodeError:
                # 非 JSON 报文，直接打印
                Globals.logger.info(f"Non-JSON message from child process: {response}", self.user)
                continue

class Spider(object):
    def __init__(self, max_concurrent_sessions=5):
        self.data_manager = AsyncTikTokDataManager()
        self.namespace_manager = NamespaceManager(max_namespaces=max_concurrent_sessions)
        self.user = 'Spider'
        self.account_queue = deque()
        self.max_concurrent_sessions = max_concurrent_sessions
        self.semaphore = asyncio.Semaphore(self.max_concurrent_sessions)
        self.session_pool = []
        self.session_lock = asyncio.Lock()

    async def initialize_namespace_and_sessions(self):
        """初始化网络命名空间和会话池。"""
        # 创建 sessions up to max_concurrent_sessions
        for _ in range(self.max_concurrent_sessions):
            session = Session(namespace_manager=self.namespace_manager, data_manager=self.data_manager)
            try:
                await session.create()
                self.session_pool.append(session)
            except Exception as e:
                Globals.logger.error(f"Failed to create session: {e}", self.user)

    async def main(self):
        await self.initialize_namespace_and_sessions()
        await asyncio.sleep(10)
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

    async def close_all_sessions(self):
        """关闭所有会话并清理资源。"""
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
            async with self.session_lock:
                for session in self.session_pool:
                    if not session.in_use:
                        session.in_use = True
                        return session
            await asyncio.sleep(0.1)

    async def release_session(self, session):
        """释放一个会话，使其可供其他任务使用。"""
        async with self.session_lock:
            session.in_use = False

    async def process_account(self, account):
        """处理单个账户，包括获取用户信息和视频。"""
        unique_id = account['unique_id']
        account_name = account['account_name']
        Globals.logger.info(f"Processing account {unique_id}.", self.user)

        session = await self.get_available_session()
        try:
            # 发送获取用户信息的命令到子进程
            command = {"action": "get_user_info", "username": unique_id}
            user_info = await session.send_command(command)
            if user_info:
                if user_info.get('status') != 'success':
                    message = user_info.get('message', 'Unknown 1')
                    if message == "'user'":
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
                        Globals.logger.error(f"Unknow error getting user info: {message}", self.user)
                        if session.proxy:
                            await self.data_manager.increase_proxy_fail(session.proxy['id'])
                        await session.rebuild_session()
                        return
                
                await self.data_manager.insert_or_update_tiktok_account(account_name, user_info['data'])
                
                # 发送获取用户视频的命令到子进程
                command = {"action": "get_user_videos", "username": unique_id}
                user_videos = await session.send_command(command)
                if (len(user_videos) > 0):
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
            await self.release_session(session)
