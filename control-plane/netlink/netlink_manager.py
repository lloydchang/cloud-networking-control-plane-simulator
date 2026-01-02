#!/usr/bin/env python3
"""
Linux Datapath Manager

Uses netlink (via pyroute2) to manage Linux network constructs:
- Network namespaces (for VRF isolation)
- VXLAN devices (layer 2 overlay)
- Bridge interfaces (layer 2 switching)
- veth pairs (layer 2 patch cables)
- IP addresses and routes (layer 3)
- iptables/nftables rules (layer 4)

This simulates the host-level networking that runs on compute nodes.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import subprocess
import json

# Note: pyroute2 import is optional for Simulator
# In production, you'd use: from pyroute2 import IPRoute, NetNS, IPDB


@dataclass
class NetworkNamespace:
    """Represents a network namespace (like a VRF context)."""

    name: str
    interfaces: List[str]
    routes: List[Dict[str, Any]]


@dataclass
class VXLANDevice:
    """Represents a VXLAN tunnel endpoint."""

    name: str
    vni: int
    local_ip: str
    remote_ip: Optional[str] = None
    group: Optional[str] = None  # Multicast group
    port: int = 4789


@dataclass
class VethPair:
    """Represents a virtual ethernet pair."""

    name: str
    peer_name: str
    namespace: Optional[str] = None


class NetlinkManager:
    """
    Manages Linux network constructs via netlink.

    In production, this uses pyroute2 for:
    - Low-level netlink operations
    - Atomic network configuration
    - Event monitoring
    """

    def __init__(self):
        self.namespaces: Dict[str, NetworkNamespace] = {}
        self.vxlan_devices: Dict[str, VXLANDevice] = {}
        self.veth_pairs: Dict[str, VethPair] = {}

        # In production:
        # self.ipr = IPRoute()
        # self.ipdb = IPDB()

    def create_namespace(self, name: str) -> NetworkNamespace:
        """
        Create a network namespace.

        Network namespaces provide isolation for:
        - Routing tables
        - Firewall rules
        - Network interfaces
        """
        print(f"NetlinkManager: Creating namespace {name}")

        # In production with pyroute2:
        # ns = NetNS(name)
        # ns.close()

        # Simulator via subprocess
        try:
            subprocess.run(
                ["ip", "netns", "add", name], check=True, capture_output=True
            )
        except subprocess.CalledProcessError:
            pass  # Namespace may already exist

        ns = NetworkNamespace(name=name, interfaces=[], routes=[])
        self.namespaces[name] = ns
        return ns

    def delete_namespace(self, name: str):
        """Delete a network namespace."""
        print(f"NetlinkManager: Deleting namespace {name}")

        try:
            subprocess.run(
                ["ip", "netns", "del", name], check=True, capture_output=True
            )
        except subprocess.CalledProcessError:
            pass

        if name in self.namespaces:
            del self.namespaces[name]

    def create_vxlan(
        self,
        name: str,
        vni: int,
        local_ip: str,
        remote_ip: Optional[str] = None,
        group: Optional[str] = None,
    ) -> VXLANDevice:
        """
        Create a VXLAN tunnel device.

        VXLAN provides L2 overlay over L3 underlay.
        Used for tenant isolation in cloud networks.
        """
        print(f"NetlinkManager: Creating VXLAN {name} VNI={vni}")

        # Build the ip link add command
        cmd = [
            "ip",
            "link",
            "add",
            name,
            "type",
            "vxlan",
            "id",
            str(vni),
            "local",
            local_ip,
            "dstport",
            "4789",
        ]

        if remote_ip:
            cmd.extend(["remote", remote_ip])
        elif group:
            cmd.extend(["group", group])

        # In production with pyroute2:
        # self.ipr.link("add", ifname=name, kind="vxlan",
        #               vxlan_id=vni, vxlan_local=local_ip)

        try:
            subprocess.run(cmd, check=True, capture_output=True)
            subprocess.run(
                ["ip", "link", "set", name, "up"], check=True, capture_output=True
            )
        except subprocess.CalledProcessError as e:
            print(f"  Error creating VXLAN: {e}")

        device = VXLANDevice(
            name=name, vni=vni, local_ip=local_ip, remote_ip=remote_ip, group=group
        )
        self.vxlan_devices[name] = device
        return device

    def delete_vxlan(self, name: str):
        """Delete a VXLAN device."""
        print(f"NetlinkManager: Deleting VXLAN {name}")

        try:
            subprocess.run(["ip", "link", "del", name], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            pass

        if name in self.vxlan_devices:
            del self.vxlan_devices[name]

    def create_veth_pair(
        self, name: str, peer_name: str, namespace: Optional[str] = None
    ) -> VethPair:
        """
        Create a veth pair.

        Veth pairs connect namespaces or act as patch cables.
        One end can be in a namespace, the other in root ns.
        """
        print(f"NetlinkManager: Creating veth pair {name} <-> {peer_name}")

        try:
            subprocess.run(
                ["ip", "link", "add", name, "type", "veth", "peer", "name", peer_name],
                check=True,
                capture_output=True,
            )

            if namespace:
                subprocess.run(
                    ["ip", "link", "set", peer_name, "netns", namespace],
                    check=True,
                    capture_output=True,
                )

            subprocess.run(
                ["ip", "link", "set", name, "up"], check=True, capture_output=True
            )

        except subprocess.CalledProcessError as e:
            print(f"  Error creating veth: {e}")

        pair = VethPair(name=name, peer_name=peer_name, namespace=namespace)
        self.veth_pairs[name] = pair
        return pair

    def add_ip_address(
        self, interface: str, address: str, namespace: Optional[str] = None
    ):
        """Add an IP address to an interface."""
        print(f"NetlinkManager: Adding {address} to {interface}")

        cmd = ["ip", "addr", "add", address, "dev", interface]

        if namespace:
            cmd = ["ip", "netns", "exec", namespace] + cmd

        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError:
            pass  # Address may already exist

    def add_route(
        self,
        destination: str,
        gateway: str,
        interface: Optional[str] = None,
        namespace: Optional[str] = None,
        table: Optional[int] = None,
    ):
        """Add a route."""
        print(f"NetlinkManager: Adding route {destination} via {gateway}")

        cmd = ["ip", "route", "add", destination, "via", gateway]

        if interface:
            cmd.extend(["dev", interface])
        if table:
            cmd.extend(["table", str(table)])

        if namespace:
            cmd = ["ip", "netns", "exec", namespace] + cmd

        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError:
            pass  # Route may already exist

    def del_route(self, destination: str, namespace: Optional[str] = None):
        """Delete a route."""
        cmd = ["ip", "route", "del", destination]

        if namespace:
            cmd = ["ip", "netns", "exec", namespace] + cmd

        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError:
            pass

    def get_routes(self, namespace: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all routes, optionally in a namespace."""
        cmd = ["ip", "-j", "route", "list"]

        if namespace:
            cmd = ["ip", "netns", "exec", namespace] + cmd

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return json.loads(result.stdout)
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            return []

    def get_interfaces(self, namespace: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all interfaces, optionally in a namespace."""
        cmd = ["ip", "-j", "link", "list"]

        if namespace:
            cmd = ["ip", "netns", "exec", namespace] + cmd

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return json.loads(result.stdout)
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            return []

    def create_bridge(self, name: str, namespace: Optional[str] = None):
        """Create a bridge device."""
        print(f"NetlinkManager: Creating bridge {name}")

        cmd = ["ip", "link", "add", name, "type", "bridge"]

        if namespace:
            cmd = ["ip", "netns", "exec", namespace] + cmd

        try:
            subprocess.run(cmd, check=True, capture_output=True)

            set_cmd = ["ip", "link", "set", name, "up"]
            if namespace:
                set_cmd = ["ip", "netns", "exec", namespace] + set_cmd
            subprocess.run(set_cmd, check=True, capture_output=True)

        except subprocess.CalledProcessError:
            pass

    def add_bridge_port(
        self, bridge: str, interface: str, namespace: Optional[str] = None
    ):
        """Add an interface to a bridge."""
        cmd = ["ip", "link", "set", interface, "master", bridge]

        if namespace:
            cmd = ["ip", "netns", "exec", namespace] + cmd

        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError:
            pass


class IPTablesManager:
    """
    Manages iptables/nftables rules for:
    - NAT (SNAT/DNAT)
    - Firewall rules
    - Connection tracking
    """

    def __init__(self, use_nftables: bool = True):
        self.use_nftables = use_nftables

    def add_snat_rule(
        self, source_cidr: str, snat_ip: str, out_interface: str = "eth0"
    ):
        """Add a SNAT rule."""
        print(f"IPTablesManager: Adding SNAT {source_cidr} -> {snat_ip}")

        if self.use_nftables:
            cmd = [
                "nft",
                "add",
                "rule",
                "ip",
                "nat",
                "postrouting",
                "ip",
                "saddr",
                source_cidr,
                "oifname",
                out_interface,
                "snat",
                "to",
                snat_ip,
            ]
        else:
            cmd = [
                "iptables",
                "-t",
                "nat",
                "-A",
                "POSTROUTING",
                "-s",
                source_cidr,
                "-o",
                out_interface,
                "-j",
                "SNAT",
                "--to-source",
                snat_ip,
            ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"  Error adding SNAT rule: {e}")

    def add_dnat_rule(
        self,
        dest_ip: str,
        dnat_ip: str,
        protocol: str = "tcp",
        port: Optional[int] = None,
    ):
        """Add a DNAT rule."""
        print(f"IPTablesManager: Adding DNAT {dest_ip} -> {dnat_ip}")

        if self.use_nftables:
            rule = f"ip daddr {dest_ip}"
            if protocol != "all" and port:
                rule += f" {protocol} dport {port}"
            rule += f" dnat to {dnat_ip}"

            cmd = ["nft", "add", "rule", "ip", "nat", "prerouting"] + rule.split()
        else:
            cmd = ["iptables", "-t", "nat", "-A", "PREROUTING", "-d", dest_ip]
            if protocol != "all":
                cmd.extend(["-p", protocol])
                if port:
                    cmd.extend(["--dport", str(port)])
            cmd.extend(["-j", "DNAT", "--to-destination", dnat_ip])

        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"  Error adding DNAT rule: {e}")

    def add_firewall_rule(
        self,
        chain: str,
        source: Optional[str] = None,
        dest: Optional[str] = None,
        protocol: str = "all",
        port: Optional[int] = None,
        action: str = "accept",
    ):
        """Add a firewall rule."""
        if self.use_nftables:
            table = "filter"
            rule_parts = []

            if source:
                rule_parts.append(f"ip saddr {source}")
            if dest:
                rule_parts.append(f"ip daddr {dest}")
            if protocol != "all":
                rule_parts.append(f"ip protocol {protocol}")
                if port:
                    rule_parts.append(f"{protocol} dport {port}")
            rule_parts.append(action)

            cmd = ["nft", "add", "rule", "ip", table, chain] + " ".join(
                rule_parts
            ).split()
        else:
            cmd = ["iptables", "-A", chain.upper()]
            if source:
                cmd.extend(["-s", source])
            if dest:
                cmd.extend(["-d", dest])
            if protocol != "all":
                cmd.extend(["-p", protocol])
                if port:
                    cmd.extend(["--dport", str(port)])
            cmd.extend(["-j", action.upper()])

        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"  Error adding firewall rule: {e}")


# Singleton instances
_netlink_manager: Optional[NetlinkManager] = None
_iptables_manager: Optional[IPTablesManager] = None


def get_netlink_manager() -> NetlinkManager:
    global _netlink_manager
    if _netlink_manager is None:
        _netlink_manager = NetlinkManager()
    return _netlink_manager


def get_iptables_manager() -> IPTablesManager:
    global _iptables_manager
    if _iptables_manager is None:
        _iptables_manager = IPTablesManager()
    return _iptables_manager
