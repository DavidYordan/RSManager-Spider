# name_space.py

import subprocess
from collections import deque
import re

class NamespaceManager(object):
    def __init__(self, max_namespaces=10, subnet_base='10.200.0.0/16'):
        self.namespaces = deque()
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
                except Exception as e:
                    pass

            # 删除所有带 "veth" 的接口
            self.delete_all_veth_interfaces()

        except Exception as e:
            pass

    def delete_all_veth_interfaces(self):
        """删除所有名称包含 'veth' 的接口"""
        try:
            # 获取所有网络接口
            output = self.run_cmd("ip link show")
            interfaces = []
            for line in output.splitlines():
                match = re.match(r'\d+: ([^:@]+)', line)
                if match:
                    interfaces.append(match.group(1))

            # 筛选并删除包含 "veth" 的接口
            veth_interfaces = [if_name for if_name in interfaces if if_name.startswith("veth")]

            for if_name in set(veth_interfaces):  # 使用 set 避免重复删除
                try:
                    self.run_cmd(f"ip link delete {if_name}")
                except Exception as e:
                    pass
        except Exception as e:
            pass

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
            pass

    def create_namespace(self, index):
        """创建网络命名空间及相关资源"""
        ns_name = f"ns{index}"
        self.run_cmd(f"ip netns add {ns_name}")
        self.namespaces.append(ns_name)

        # 创建 veth 对
        host_veth = f"veth{index}"
        ns_veth = f"veth{index}_ns"
        self.run_cmd(f"ip link add {host_veth} type veth peer name {ns_veth}")
        self.run_cmd(f"ip link set {ns_veth} netns {ns_name}")

        # 配置主机端
        host_ip = f"10.200.{index}.1/24"
        self.run_cmd(f"ip addr add {host_ip} dev {host_veth}")
        self.run_cmd(f"ip link set {host_veth} up")

        # 配置命名空间端
        ns_ip = f"10.200.{index}.2/24"
        self.run_cmd(f"ip netns exec {ns_name} ip addr add {ns_ip} dev {ns_veth}")
        self.run_cmd(f"ip netns exec {ns_name} ip link set {ns_veth} up")
        self.run_cmd(f"ip netns exec {ns_name} ip link set lo up")

        # 设置默认路由
        default_via = f"10.200.{index}.1"
        self.run_cmd(f"ip netns exec {ns_name} ip route add default via {default_via}")

    def enable_ip_forwarding(self):
        """启用主机的 IP 转发"""
        try:
            self.run_cmd("sysctl -w net.ipv4.ip_forward=1")
        except Exception as e:
            pass

    def get_external_interface(self):
        """获取主机的外部网络接口名称"""
        try:
            output = self.run_cmd("ip route | grep default")
            # 默认路由通常类似于: default via 192.168.1.1 dev eth0
            parts = output.strip().split()
            dev_index = parts.index('dev') + 1
            external_iface = parts[dev_index]
            return external_iface
        except Exception as e:
            return None

    def acquire_namespace(self):
        """获取一个可用的命名空间，如果全部在用则等待"""
        if not self.namespaces:
            return None
        ns_name = self.namespaces.popleft()
        return ns_name

    def release_namespace(self, ns_name):
        """释放命名空间，放回队列末尾以供复用"""
        self.namespaces.append(ns_name)

    def set_namespace_proxy(self, ns_name, proxy):
        """
        设置指定命名空间的 http_proxy 和 https_proxy 环境变量
        :param ns_name: 命名空间名称
        :param proxy: 代理地址
        """
        try:
            # 设置环境变量命令
            self.run_cmd(
                f"ip netns exec {ns_name} bash -c \"echo 'export http_proxy={proxy}' >> /etc/profile && echo 'export https_proxy={proxy}' >> /etc/profile\""
            )
        except Exception as e:
            pass
