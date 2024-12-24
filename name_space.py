# name_space.py

import subprocess
import re
import asyncio
from custom_globals import Globals

class NamespaceManager(object):
    def __init__(self, max_namespaces=10, subnet_base='10.200.0.0/16'):
        self.namespace_queue = asyncio.Queue()
        self.max_namespaces = max_namespaces
        self.user = 'NamespaceManager'
        self.subnet_base = subnet_base  # 使用 /16 子网覆盖多个命名空间
        # 清理所有现有的网络命名空间及相关资源
        self.cleanup_all_namespaces()
        # 创建新的网络命名空间
        self.create_namespaces()
        # 启用 IP 转发
        self.enable_ip_forwarding()

    def cleanup_all_namespaces(self):
        """清理所有网络命名空间及其相关资源"""
        try:
            # 获取所有命名空间列表
            output = self.run_cmd("ip netns list")
            namespaces = [line.split()[0] for line in output.splitlines()]

            # 删除每个命名空间
            for ns_name in namespaces:
                try:
                    self.run_cmd(f"ip netns delete {ns_name}")
                    Globals.logger.debug(f"Deleted namespace: {ns_name}", self.user)
                except Exception as e:
                    Globals.logger.error(f"Failed to delete namespace {ns_name}: {e}", self.user)

            # 删除所有带 "veth_ns_" 的接口
            self.delete_all_veth_interfaces()
        except Exception as e:
            Globals.logger.error(f"Error during cleanup_all_namespaces: {e}", self.user)

    def delete_all_veth_interfaces(self):
        """删除所有名称包含 'veth_ns_' 的接口"""
        try:
            # 获取所有网络接口
            output = self.run_cmd("ip link show")
            interfaces = []
            for line in output.splitlines():
                match = re.match(r'\d+: ([^:@]+)', line)
                if match:
                    interfaces.append(match.group(1))

            # 筛选并删除包含 "veth_ns_" 的接口
            veth_interfaces = [if_name for if_name in interfaces if if_name.startswith("veth_ns_")]

            for if_name in set(veth_interfaces):  # 使用 set 避免重复删除
                try:
                    self.run_cmd(f"ip link delete {if_name}")
                    Globals.logger.debug(f"Deleted veth interface: {if_name}", self.user)
                except Exception as e:
                    Globals.logger.error(f"Failed to delete veth interface {if_name}: {e}", self.user)
        except Exception as e:
            Globals.logger.error(f"Error during delete_all_veth_interfaces: {e}", self.user)

    def run_cmd(self, cmd):
        """运行系统命令并返回输出"""
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            raise Exception(f"Command failed: {cmd}\nError: {result.stderr.decode().strip()}")
        return result.stdout.decode()

    def create_namespaces(self):
        """创建新的网络命名空间"""
        try:
            for i in range(self.max_namespaces):
                self.create_namespace(i)
        except Exception as e:
            Globals.logger.error(f"Error during create_namespaces: {e}", self.user)

    def create_namespace(self, index):
        """创建网络命名空间及相关资源"""
        ns_name = f"ns{index}"
        try:
            self.run_cmd(f"ip netns add {ns_name}")
            Globals.logger.debug(f"Created namespace: {ns_name}", self.user)
            self.namespace_queue.put_nowait(ns_name)
        except Exception as e:
            Globals.logger.error(f"Failed to create namespace {ns_name}: {e}", self.user)
            return

        # 创建 veth 对
        host_veth = f"veth_ns_{index}_host"
        ns_veth = f"veth_ns_{index}_ns"
        try:
            self.run_cmd(f"ip link add {host_veth} type veth peer name {ns_veth}")
            self.run_cmd(f"ip link set {ns_veth} netns {ns_name}")
            Globals.logger.debug(f"Created veth pair: {host_veth} <-> {ns_veth}", self.user)
        except Exception as e:
            Globals.logger.error(f"Failed to create veth pair for {ns_name}: {e}", self.user)
            self.run_cmd(f"ip netns delete {ns_name}")
            return

        # 配置主机端
        host_ip = f"10.200.{index}.1/24"
        try:
            self.run_cmd(f"ip addr add {host_ip} dev {host_veth}")
            self.run_cmd(f"ip link set {host_veth} up")
            Globals.logger.debug(f"Configured host veth {host_veth} with IP {host_ip}", self.user)
        except Exception as e:
            Globals.logger.error(f"Failed to configure host veth {host_veth}: {e}", self.user)
            self.run_cmd(f"ip link delete {host_veth}")
            self.run_cmd(f"ip netns delete {ns_name}")
            return

        # 配置命名空间端
        ns_ip = f"10.200.{index}.2/24"
        try:
            self.run_cmd(f"ip netns exec {ns_name} ip addr add {ns_ip} dev {ns_veth}")
            self.run_cmd(f"ip netns exec {ns_name} ip link set {ns_veth} up")
            self.run_cmd(f"ip netns exec {ns_name} ip link set lo up")
            Globals.logger.debug(f"Configured namespace {ns_name} veth {ns_veth} with IP {ns_ip}", self.user)
        except Exception as e:
            Globals.logger.error(f"Failed to configure namespace veth {ns_veth}: {e}", self.user)
            self.run_cmd(f"ip link delete {host_veth}")
            self.run_cmd(f"ip netns delete {ns_name}")
            return

        # 设置默认路由
        default_via = f"10.200.{index}.1"
        try:
            self.run_cmd(f"ip netns exec {ns_name} ip route add default via {default_via}")
            Globals.logger.debug(f"Set default route for {ns_name} via {default_via}", self.user)
        except Exception as e:
            Globals.logger.error(f"Failed to set default route for {ns_name}: {e}", self.user)
            self.run_cmd(f"ip netns exec {ns_name} ip link delete {ns_veth}")
            self.run_cmd(f"ip link delete {host_veth}")
            self.run_cmd(f"ip netns delete {ns_name}")
            return

    def enable_ip_forwarding(self):
        """启用主机的 IP 转发"""
        try:
            self.run_cmd("sysctl -w net.ipv4.ip_forward=1")
            Globals.logger.debug("Enabled IP forwarding", self.user)
        except Exception as e:
            Globals.logger.error(f"Failed to enable IP forwarding: {e}", self.user)

    def get_external_interface(self):
        """获取主机的外部网络接口名称"""
        try:
            output = self.run_cmd("ip route | grep default")
            # 默认路由通常类似于: default via 192.168.1.1 dev eth0
            parts = output.strip().split()
            dev_index = parts.index('dev') + 1
            external_iface = parts[dev_index]
            Globals.logger.debug(f"External interface: {external_iface}", self.user)
            return external_iface
        except Exception as e:
            Globals.logger.error(f"Failed to get external interface: {e}", self.user)
            return None

    async def acquire_namespace(self):
        """获取一个可用的命名空间，如果全部在用则等待"""
        try:
            ns_name = await self.namespace_queue.get()
            Globals.logger.debug(f"Acquired namespace: {ns_name}", self.user)
            return ns_name
        except Exception as e:
            Globals.logger.error(f"Error acquiring namespace: {e}", self.user)
            return None

    async def release_namespace(self, ns_name):
        """释放命名空间，放回队列末尾以供复用"""
        try:
            await self.namespace_queue.put(ns_name)
            Globals.logger.debug(f"Released namespace: {ns_name}", self.user)
        except Exception as e:
            Globals.logger.error(f"Error releasing namespace {ns_name}: {e}", self.user)

    def set_namespace_proxy(self, ns_name, proxy):
        """
        设置指定命名空间的 http_proxy 和 https_proxy 环境变量
        :param ns_name: 命名空间名称
        :param proxy: 代理地址
        """
        try:
            # 推荐在启动子进程时传递环境变量，而不是修改 /etc/profile
            # 因此，这里可以考虑移除此方法或重新设计
            Globals.logger.warning("set_namespace_proxy method is deprecated. Use environment variables instead.", self.user)
        except Exception as e:
            Globals.logger.error(f"Failed to set proxy for namespace {ns_name}: {e}", self.user)
