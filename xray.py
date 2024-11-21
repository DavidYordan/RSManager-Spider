# xray.py

import asyncio
import base64
import json
import os
import re
from datetime import datetime, timedelta

import aiohttp
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from custom_globals import Globals
from models import AsyncSessionLocal
from models.proxy_url import ProxyUrl
from models.subscribe import SubscribeUrl


class Xray(object):
    def __init__(self):
        access_log = f'access_{datetime.now().strftime("%Y-%m-%d")}.log'
        error_log = f'error_{datetime.now().strftime("%Y-%m-%d")}.log'
        os.makedirs('environment', exist_ok=True)
        open(f'environment/{access_log}', 'a').close()
        open(f'environment/{error_log}', 'a').close()
        self.conf_template = {
            'log': {
                'access': access_log,
                'error': error_log,
                'loglevel': 'debug',
                'dnsLog': True
            },
            'routing': {
                'domainStrategy': 'AsIs',
                'rules': [{
                    "type": "field",
                    "port": 53,
                    "outboundTag": "dns-out"
                }]
            },
            'dns': {
                'servers': ['8.8.8.8', '1.1.1.1']
            },
            'inbounds': [],
            'outbounds': [{
                'protocol': 'dns',
                'tag': 'dns-out'
            }]
        }
        self.conf = {}
        self.port = 40001
        self.user = 'Xray'

    async def base64_decode(self, source):
        try:
            text = source.replace('_', '/').replace('-', '+')
            padding = -len(text) % 4
            text += '=' * padding
            return base64.urlsafe_b64decode(text).decode()
        except Exception:
            return source

    async def deletelogger(self):
        try:
            xray_dir = os.path.join(os.getcwd(), 'environment')
            cutoff_date = datetime.now() - timedelta(days=7)
            for filename in os.listdir(xray_dir):
                match = re.match(r"(access|error)_(\d{4}-\d{2}-\d{2})\.log", filename)
                if match:
                    file_date_str = match.group(2)
                    file_date = datetime.strptime(file_date_str, '%Y-%m-%d')
                    if file_date < cutoff_date:
                        file_path = os.path.join(xray_dir, filename)
                        os.remove(file_path)

        except Exception as e:
            Globals.logger.error(f'Failed to delete log: {e}', self.user)

    async def kill_process_on_ports(self):
        try:
            # 获取当前所有使用的端口
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(ProxyUrl.current_port).where(ProxyUrl.current_port != 0))
                ports = {row[0] for row in result}

            for port in ports:
                # 使用lsof命令查找占用端口的进程
                command = f'lsof -t -i:{port}'
                proc = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await proc.communicate()

                if stdout:
                    pids = stdout.decode().strip().split('\n')
                    for pid in pids:
                        kill_command = f'kill -9 {pid}'
                        await asyncio.create_subprocess_shell(kill_command)
        except Exception as e:
            Globals.logger.error(f'Failed to kill processes on ports: {e}', self.user)

    async def parse_shadowsocks_link(self, link, tag):
        try:
            rest = link[5:]  # 去掉 'ss://' 前缀
            match = re.match(r'(?P<params>.+)@(?P<server>[^:]+):(?P<port>\d+)(?:/\?(?P<extra_params>[^#]+))?(?:#(?P<tag>.+))?', rest)
            if not match:
                Globals.logger.error(f'Link format invalid, failed to parse: {rest}', self.user)
                return {}
            encryption_password = await self.base64_decode(match.group('params'))
            if encryption_password.count(':') != 1:
                Globals.logger.error(f'Invalid encryption-password format in link: {rest}', self.user)
                return {}
            encryption, password = encryption_password.split(':')
            address = match.group('server')
            if address == '9.9.9.9':
                return {}
            port = match.group('port')
            data = {
                'protocol': 'shadowsocks',
                'tag': tag,
                'settings': {
                    'servers': [{
                        'address': address,
                        'port': int(port),
                        'method': encryption,
                        'password': password,
                        'uot': True,
                        'UoTVersion': 2
                    }]
                }
            }
            return data

        except Exception as e:
            Globals.logger.error(f'Error parsing {rest}: {e}', self.user)
            return {}

    async def fetch_and_store_subscribe_links(self):
        """第一步：获取需要解析的订阅链接，解析后存入 ProxyUrl 表"""
        try:
            # 从 ProxyUrl 表中获取已存在的 subscribe_id 列表
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(ProxyUrl.subscribe_id).distinct())
                existing_subscribe_ids = {row[0] for row in result}

                # 获取 SubscribeUrl 表中所有不在 existing_subscribe_ids 中的记录
                result = await session.execute(select(SubscribeUrl).where(SubscribeUrl.id.notin_(existing_subscribe_ids)))
                new_subscribe_urls = result.scalars().all()

            # 解析新的订阅链接
            for subscribe_url_obj in new_subscribe_urls:
                await self.parse_and_store_links(subscribe_url_obj)

        except Exception as e:
            Globals.logger.error(f'Failed to fetch and store subscribe links: {e}', self.user)

    async def parse_and_store_links(self, subscribe_url_obj):
        """解析订阅链接，存储其中的代理链接到 ProxyUrl 表"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(subscribe_url_obj.url) as res:
                    if res.status != 200:
                        Globals.logger.error(f'Failed to fetch URL: {subscribe_url_obj.url}', self.user)
                        return
                    content = await res.text()

            if not content:
                return

            # 解码内容
            if '://' not in content:
                content = await self.base64_decode(content)
            if '://' not in content:
                return

            link_list = content.strip().split('\n')
            async with AsyncSessionLocal() as db_session:
                for link in link_list:
                    link = link.strip()
                    if not link:
                        continue
                    if '://' not in link:
                        link = await self.base64_decode(link)
                    if 'ss://' not in link:
                        Globals.logger.warning(f'Unsupported link: {link}', self.user)
                        continue

                    # 解析链接以提取服务器地址
                    rest = link[5:]
                    match = re.match(r'(?P<params>.+)@(?P<server>[^:]+):(?P<port>\d+)', rest)
                    if not match:
                        Globals.logger.error(f'Link format invalid, failed to parse server address: {link}', self.user)
                        continue

                    server = match.group('server')
                    if server == '9.9.9.9':
                        continue

                    # 将代理链接存入 ProxyUrl 表
                    proxy_url = ProxyUrl(
                        subscribe_id=subscribe_url_obj.id,
                        url=link,
                        type='ss',  # 假设都是 ss 类型
                        comments=''  # 可以根据需要添加备注
                    )
                    db_session.add(proxy_url)

                await db_session.commit()

        except Exception as e:
            Globals.logger.error(f'Failed to parse and store links: {e}', self.user)

    async def generate_xray_config(self):
        """第二步：从 ProxyUrl 表中提取所有记录，解析代理链接，生成 Xray 配置"""
        try:
            self.conf = self.conf_template.copy()

            async with AsyncSessionLocal() as session:
                result = await session.execute(select(ProxyUrl).where(ProxyUrl.is_using == False))
                proxy_urls = result.scalars().all()

                for proxy_url_obj in proxy_urls:
                    link = proxy_url_obj.url.strip()
                    if not link:
                        continue
                    if 'ss://' not in link:
                        Globals.logger.warning(f'Unsupported link in database: {link}', self.user)
                        continue

                    # 解析代理链接，生成 Xray 配置
                    tag = f'{self.port}out'
                    data = await self.parse_shadowsocks_link(link, tag)
                    if not data:
                        continue

                    # 更新 Xray 配置
                    self.conf['inbounds'].append({
                        'tag': f'{self.port}in',
                        'port': self.port,
                        'protocol': 'http',
                        'accounts': []
                    })
                    self.conf['outbounds'].append(data)
                    self.conf['routing']['rules'].append({
                        'type': 'field',
                        'inboundTag': [f'{self.port}in'],
                        'outboundTag': tag
                    })

                    # 更新 ProxyUrl 表中的 current_port、is_using字段
                    await self.update_proxy_url(session, proxy_url_obj.id, self.port)

                    self.port += 1

        except Exception as e:
            Globals.logger.error(f'Failed to generate Xray configuration: {e}', self.user)

    async def update_proxy_url(self, session: AsyncSession, proxy_url_id: int, port: int):
        """更新 ProxyUrl 表中的 current_port 和 is_using 字段"""
        try:
            stmt = (
                update(ProxyUrl).
                where(ProxyUrl.id == proxy_url_id).
                values(current_port=port, is_using=False)
            )
            await session.execute(stmt)
            await session.commit()
        except Exception as e:
            Globals.logger.error(f'Failed to update ProxyUrl ID {proxy_url_id}: {e}', self.user)

    async def clear_proxy_urls(self):
        """运行前清空 proxy_url 表的 current_port 列和 is_using 列"""
        try:
            async with AsyncSessionLocal() as session:
                stmt = (
                    update(ProxyUrl).
                    values(current_port=0, is_using=False)
                )
                await session.execute(stmt)
                await session.commit()
        except Exception as e:
            Globals.logger.error(f'Failed to clear ProxyUrl records: {e}', self.user)

    async def run(self):
        try:
            # 运行前清空 ProxyUrl 表的 current_port 和 is_using 列
            await self.clear_proxy_urls()

            # 第一步：获取并存储订阅链接
            await self.fetch_and_store_subscribe_links()

            # 第二步：生成 Xray 配置
            await self.generate_xray_config()

            # 写入 Xray 配置文件
            with open('environment/config.json', 'w') as f:
                json.dump(self.conf, f, indent=4)

            # 删除旧日志
            await self.deletelogger()

            # 杀掉占用端口的进程
            await self.kill_process_on_ports()

            # 启动 Xray
            await asyncio.create_subprocess_exec('./xray', 'run', cwd='environment')

        except Exception as e:
            Globals.logger.error(f'Failed to start Xray: {e}', self.user)
