#!/usr/bin/env python3
"""
Device Configuration Generator

Generates configuration templates for networking devices.
Currently implementation is focused on FRRouting (FRR).
Includes non-functional placeholders for SONiC ConfigDB support (future-proofing).
The active simulator stack is 100% FRR-based.
Implements template-based config generation for:
- BGP configuration
- EVPN-VXLAN setup
- VRF creation
- Route injection
- Policy configuration
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from jinja2 import Template
import json


@dataclass
class SwitchConfig:
    """Represents a switch configuration."""

    hostname: str
    router_id: str
    asn: int
    config_text: str


@dataclass
class VRFConfig:
    """VRF configuration."""

    name: str
    vni: int
    rd: str
    rt_import: List[str]
    rt_export: List[str]


# FRR Configuration Templates
FRR_BASE_TEMPLATE = """
!
frr version 8.5
frr defaults datacenter
hostname {{ hostname }}
log syslog informational
service integrated-vtysh-config
!
{% for vrf in vrfs %}
vrf {{ vrf.name }}
 vni {{ vrf.vni }}
exit-vrf
!
{% endfor %}
router bgp {{ asn }}
 bgp router-id {{ router_id }}
 bgp bestpath as-path multipath-relax
 no bgp ebgp-requires-policy
 no bgp default ipv4-unicast
 !
{% for neighbor in neighbors %}
 neighbor {{ neighbor.ip }} remote-as {{ neighbor.remote_asn }}
{% if neighbor.peer_group %}
 neighbor {{ neighbor.ip }} peer-group {{ neighbor.peer_group }}
{% endif %}
{% endfor %}
 !
 address-family ipv4 unicast
  redistribute connected
{% for neighbor in neighbors %}
  neighbor {{ neighbor.ip }} activate
{% endfor %}
 exit-address-family
 !
 address-family l2vpn evpn
{% for neighbor in neighbors %}
  neighbor {{ neighbor.ip }} activate
{% endfor %}
  advertise-all-vni
 exit-address-family
exit
!
{% for vrf in vrfs %}
router bgp {{ asn }} vrf {{ vrf.name }}
 bgp router-id {{ router_id }}
 !
 address-family ipv4 unicast
  redistribute connected
  redistribute static
 exit-address-family
 !
 address-family l2vpn evpn
  advertise ipv4 unicast
  rd {{ vrf.rd }}
{% for rt in vrf.rt_import %}
  route-target import {{ rt }}
{% endfor %}
{% for rt in vrf.rt_export %}
  route-target export {{ rt }}
{% endfor %}
 exit-address-family
exit
!
{% endfor %}
{% for static_route in static_routes %}
ip route {{ static_route.prefix }} {{ static_route.next_hop }}{% if static_route.vrf %} vrf {{ static_route.vrf }}{% endif %}

{% endfor %}
"""

SONIC_CONFIG_TEMPLATE = """
{
  "DEVICE_METADATA": {
    "localhost": {
      "hostname": "{{ hostname }}",
      "type": "ToRRouter",
      "hwsku": "Force10-S6000"
    }
  },
  "LOOPBACK_INTERFACE": {
    "Loopback0": {},
    "Loopback0|{{ router_id }}/32": {}
  },
  "BGP_GLOBALS": {
    "default": {
      "local_asn": {{ asn }},
      "router_id": "{{ router_id }}"
    }
  },
  "BGP_NEIGHBOR": {
{% for neighbor in neighbors %}
    "{{ neighbor.ip }}": {
      "asn": {{ neighbor.remote_asn }},
      "name": "{{ neighbor.name }}"
    }{% if not loop.last %},{% endif %}
{% endfor %}
  },
  "VXLAN_TUNNEL": {
    "vtep1": {
      "src_ip": "{{ router_id }}"
    }
  },
  "VXLAN_TUNNEL_MAP": {
{% for vrf in vrfs %}
    "vtep1|map_{{ vrf.vni }}_{{ vrf.name }}": {
      "vni": {{ vrf.vni }},
      "vlan": "{{ vrf.name }}"
    }{% if not loop.last %},{% endif %}
{% endfor %}
  },
  "VRF": {
{% for vrf in vrfs %}
    "{{ vrf.name }}": {
      "vni": {{ vrf.vni }}
    }{% if not loop.last %},{% endif %}
{% endfor %}
  }
}
"""


class ConfigGenerator:
    """
    Generates switch configurations from high-level intent.

    Supports:
    - FRRouting (CLI-based config)
    - SONiC (Unimplemented placeholder for JSON ConfigDB)
    """

    def __init__(self):
        self.frr_template = Template(FRR_BASE_TEMPLATE)
        self.sonic_template = Template(SONIC_CONFIG_TEMPLATE)

    def generate_frr_config(
        self,
        hostname: str,
        router_id: str,
        asn: int,
        neighbors: List[Dict[str, Any]],
        vrfs: List[VRFConfig],
        static_routes: List[Dict[str, Any]] = None,
    ) -> SwitchConfig:
        """
        Generate FRR configuration.

        Args:
            hostname: Switch hostname
            router_id: BGP router ID
            asn: Local AS number
            neighbors: List of BGP neighbor configurations
            vrfs: List of VRF configurations
            static_routes: Optional list of static routes
        """
        config_text = self.frr_template.render(
            hostname=hostname,
            router_id=router_id,
            asn=asn,
            neighbors=neighbors,
            vrfs=[
                {
                    "name": v.name,
                    "vni": v.vni,
                    "rd": v.rd,
                    "rt_import": v.rt_import,
                    "rt_export": v.rt_export,
                }
                for v in vrfs
            ],
            static_routes=static_routes or [],
        )

        return SwitchConfig(
            hostname=hostname, router_id=router_id, asn=asn, config_text=config_text
        )

    def generate_sonic_config(
        self,
        hostname: str,
        router_id: str,
        asn: int,
        neighbors: List[Dict[str, Any]],
        vrfs: List[VRFConfig],
    ) -> str:
        """
        Generate SONiC ConfigDB JSON (Unimplemented Placeholder).
        """
        config_json = self.sonic_template.render(
            hostname=hostname,
            router_id=router_id,
            asn=asn,
            neighbors=neighbors,
            vrfs=[
                {
                    "name": v.name,
                    "vni": v.vni,
                    "rd": v.rd,
                    "rt_import": v.rt_import,
                    "rt_export": v.rt_export,
                }
                for v in vrfs
            ],
        )

        return config_json

    def generate_all_configs(self, topology: Dict[str, Any]) -> Dict[str, SwitchConfig]:
        """
        Generate configurations for all switches in a topology.
        """
        configs = {}

        for switch_name, switch_data in topology.get("switches", {}).items():
            vrfs = [
                VRFConfig(
                    name=vrf["name"],
                    vni=vrf["vni"],
                    rd=vrf["rd"],
                    rt_import=vrf.get("rt_import", []),
                    rt_export=vrf.get("rt_export", []),
                )
                for vrf in switch_data.get("vrfs", [])
            ]

            config = self.generate_frr_config(
                hostname=switch_name,
                router_id=switch_data["router_id"],
                asn=switch_data["asn"],
                neighbors=switch_data.get("neighbors", []),
                vrfs=vrfs,
                static_routes=switch_data.get("static_routes", []),
            )

            configs[switch_name] = config

        return configs

    def diff_configs(self, current: str, desired: str) -> List[str]:
        """
        Compute the difference between current and desired configuration.

        Returns a list of commands needed to transform current to desired.
        """
        # Simplified diff - in production, use a proper config parser
        current_lines = set(current.strip().split("\n"))
        desired_lines = set(desired.strip().split("\n"))

        to_remove = current_lines - desired_lines
        to_add = desired_lines - current_lines

        commands = []

        # Generate removal commands (prefix with 'no')
        for line in to_remove:
            line = line.strip()
            if line and not line.startswith("!"):
                commands.append(f"no {line}")

        # Generate addition commands
        for line in to_add:
            line = line.strip()
            if line and not line.startswith("!"):
                commands.append(line)

        return commands


class DeviceOnboarding:
    """
    Handles Zero Touch Provisioning (ZTP) for new devices.

    Simulates:
    - Device discovery
    - Initial configuration push
    - Inventory registration
    """

    def __init__(self, config_generator: ConfigGenerator):
        self.config_generator = config_generator
        self.inventory: Dict[str, Dict[str, Any]] = {}

    def discover_device(self, mac_address: str, ip_address: str) -> Dict[str, Any]:
        """
        Simulate device discovery.

        In production, this would be triggered by DHCP or LLDP.
        """
        print(f"DeviceOnboarding: Discovered device MAC={mac_address} IP={ip_address}")

        device = {
            "mac_address": mac_address,
            "ip_address": ip_address,
            "status": "discovered",
            "model": "generic-switch",
            "serial": f"SN-{mac_address.replace(':', '')}",
        }

        self.inventory[mac_address] = device
        return device

    def assign_role(
        self, mac_address: str, role: str, rack_id: str, position: int
    ) -> Dict[str, Any]:
        """
        Assign a role to a discovered device.

        Roles: spine, leaf, border-leaf
        """
        if mac_address not in self.inventory:
            raise ValueError(f"Device {mac_address} not in inventory")

        device = self.inventory[mac_address]
        device["role"] = role
        device["rack_id"] = rack_id
        device["position"] = position
        device["status"] = "assigned"

        # Generate hostname based on role and position
        device["hostname"] = f"{role}{position}"

        print(f"DeviceOnboarding: Assigned role {role} to {mac_address}")

        return device

    def provision_device(
        self, mac_address: str, topology: Dict[str, Any]
    ) -> SwitchConfig:
        """
        Generate and push initial configuration to a device.
        """
        if mac_address not in self.inventory:
            raise ValueError(f"Device {mac_address} not in inventory")

        device = self.inventory[mac_address]

        if device["status"] != "assigned":
            raise ValueError(f"Device {mac_address} not yet assigned a role")

        hostname = device["hostname"]

        # Get switch config from topology
        switch_data = topology.get("switches", {}).get(hostname)
        if not switch_data:
            raise ValueError(f"No topology data for {hostname}")

        # Generate configuration
        vrfs = [
            VRFConfig(
                name=vrf["name"],
                vni=vrf["vni"],
                rd=vrf["rd"],
                rt_import=vrf.get("rt_import", []),
                rt_export=vrf.get("rt_export", []),
            )
            for vrf in switch_data.get("vrfs", [])
        ]

        config = self.config_generator.generate_frr_config(
            hostname=hostname,
            router_id=switch_data["router_id"],
            asn=switch_data["asn"],
            neighbors=switch_data.get("neighbors", []),
            vrfs=vrfs,
        )

        device["status"] = "provisioned"
        device["config"] = config.config_text

        print(f"DeviceOnboarding: Provisioned {hostname}")

        return config

    def get_inventory(self) -> Dict[str, Dict[str, Any]]:
        """Get current device inventory."""
        return self.inventory


# Singleton instances
_config_generator: Optional[ConfigGenerator] = None
_device_onboarding: Optional[DeviceOnboarding] = None


def get_config_generator() -> ConfigGenerator:
    global _config_generator
    if _config_generator is None:
        _config_generator = ConfigGenerator()
    return _config_generator


def get_device_onboarding() -> DeviceOnboarding:
    global _device_onboarding
    if _device_onboarding is None:
        _device_onboarding = DeviceOnboarding(get_config_generator())
    return _device_onboarding
