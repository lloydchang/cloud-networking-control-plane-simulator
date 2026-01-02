#!/usr/bin/env python3
"""
Security Groups / Firewall Controller

Translates high-level security group rules into nftables rules.
Watches for changes and reconciles desired state with actual state.

Simulates firewall feature:
- Per-instance security groups
- Ingress/Egress rules
- Protocol/Port/CIDR based filtering
"""

import json
import subprocess
import time
import os
from pathlib import Path
from typing import Dict, List, Any

# Security Group definitions (would come from API in production)
SECURITY_GROUPS: Dict[str, Dict[str, Any]] = {
    "sg-web": {
        "name": "Web Servers",
        "description": "Allow HTTP/HTTPS inbound",
        "rules": [
            {"direction": "ingress", "protocol": "tcp", "port": 80, "cidr": "0.0.0.0/0"},
            {"direction": "ingress", "protocol": "tcp", "port": 443, "cidr": "0.0.0.0/0"},
            {"direction": "ingress", "protocol": "icmp", "cidr": "0.0.0.0/0"},
            {"direction": "egress", "protocol": "all", "cidr": "0.0.0.0/0"},
        ]
    },
    "sg-ssh": {
        "name": "SSH Access",
        "description": "Allow SSH from management CIDR",
        "rules": [
            {"direction": "ingress", "protocol": "tcp", "port": 22, "cidr": "10.0.0.0/8"},
            {"direction": "egress", "protocol": "all", "cidr": "0.0.0.0/0"},
        ]
    },
    "sg-internal": {
        "name": "Internal Traffic",
        "description": "Allow all traffic within VPC",
        "rules": [
            {"direction": "ingress", "protocol": "all", "cidr": "10.1.0.0/16"},
            {"direction": "ingress", "protocol": "all", "cidr": "10.2.0.0/16"},
            {"direction": "egress", "protocol": "all", "cidr": "0.0.0.0/0"},
        ]
    },
    "sg-database": {
        "name": "Database Servers",
        "description": "Allow DB ports from app tier only",
        "rules": [
            {"direction": "ingress", "protocol": "tcp", "port": 5432, "cidr": "10.1.1.0/24"},
            {"direction": "ingress", "protocol": "tcp", "port": 3306, "cidr": "10.1.1.0/24"},
            {"direction": "egress", "protocol": "all", "cidr": "0.0.0.0/0"},
        ]
    }
}

# Instance to Security Group mappings (would come from API)
INSTANCE_SG_MAPPINGS: Dict[str, List[str]] = {
    "10.1.1.10": ["sg-web", "sg-ssh"],      # server-1
    "10.1.2.10": ["sg-internal"],            # server-2
    "10.1.3.10": ["sg-database", "sg-ssh"],  # server-3
    "10.2.1.10": ["sg-internal"],            # server-4
    "10.2.2.10": ["sg-web"],                 # server-5
    "10.2.3.10": ["sg-internal"],            # server-6
}


def run_nft(command: str) -> bool:
    """Execute an nft command."""
    try:
        result = subprocess.run(
            ["nft"] + command.split(),
            capture_output=True,
            text=True,
            check=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"nft error: {e.stderr}")
        return False


def init_nftables():
    """Initialize base nftables structure."""
    print("Initializing nftables structure...")
    
    # Create base tables and chains
    commands = [
        "add table ip security_groups",
        "add chain ip security_groups input { type filter hook input priority filter; policy drop; }",
        "add chain ip security_groups forward { type filter hook forward priority filter; policy drop; }",
        "add chain ip security_groups output { type filter hook output priority filter; policy accept; }",
        
        # Allow established connections
        "add rule ip security_groups input ct state established,related accept",
        "add rule ip security_groups forward ct state established,related accept",
        
        # Allow loopback
        "add rule ip security_groups input iifname lo accept",
        
        # Allow Prometheus scraping (port 9100)
        "add rule ip security_groups input tcp dport 9100 accept",
    ]
    
    # Clear existing rules first
    subprocess.run(["nft", "flush", "ruleset"], capture_output=True)
    
    for cmd in commands:
        run_nft(cmd)


def generate_nft_rules(instance_ip: str, sg_ids: List[str]) -> List[str]:
    """Generate nftables rules for an instance based on its security groups."""
    rules = []
    
    for sg_id in sg_ids:
        sg = SECURITY_GROUPS.get(sg_id)
        if not sg:
            continue
            
        for rule in sg["rules"]:
            direction = rule["direction"]
            protocol = rule["protocol"]
            cidr = rule["cidr"]
            port = rule.get("port")
            
            if direction == "ingress":
                # Ingress: allow traffic TO this instance
                nft_rule = f"add rule ip security_groups forward ip daddr {instance_ip}"
                
                if protocol != "all":
                    if protocol == "icmp":
                        nft_rule += " ip protocol icmp"
                    else:
                        nft_rule += f" ip protocol {protocol}"
                        if port:
                            nft_rule += f" {protocol} dport {port}"
                
                if cidr != "0.0.0.0/0":
                    nft_rule += f" ip saddr {cidr}"
                    
                nft_rule += " accept"
                rules.append(nft_rule)
                
            elif direction == "egress":
                # Egress: allow traffic FROM this instance
                nft_rule = f"add rule ip security_groups forward ip saddr {instance_ip}"
                
                if protocol != "all":
                    nft_rule += f" ip protocol {protocol}"
                    if port:
                        nft_rule += f" {protocol} dport {port}"
                
                if cidr != "0.0.0.0/0":
                    nft_rule += f" ip daddr {cidr}"
                    
                nft_rule += " accept"
                rules.append(nft_rule)
    
    return rules


def apply_security_groups():
    """Apply all security group rules."""
    print("Applying security group rules...")
    
    for instance_ip, sg_ids in INSTANCE_SG_MAPPINGS.items():
        print(f"  Instance {instance_ip}: {sg_ids}")
        rules = generate_nft_rules(instance_ip, sg_ids)
        for rule in rules:
            run_nft(rule)


def show_rules():
    """Display current nftables rules."""
    result = subprocess.run(
        ["nft", "list", "ruleset"],
        capture_output=True,
        text=True
    )
    print("\n=== Current Security Group Rules ===")
    print(result.stdout)


def reconciliation_loop():
    """
    Main reconciliation loop.
    In production, this would:
    - Watch for API changes
    - Compare desired vs actual state
    - Apply corrective actions
    """
    while True:
        try:
            # In production: fetch desired state from API
            # desired = fetch_from_api("/security-groups")
            
            # In production: get actual state from nftables
            # actual = parse_nft_rules()
            
            # In production: compute diff and apply changes
            # diff = compute_diff(desired, actual)
            # apply_changes(diff)
            
            time.sleep(30)  # Reconcile every 30 seconds
            
        except Exception as e:
            print(f"Reconciliation error: {e}")
            time.sleep(5)


def main():
    print("=== Security Groups Controller Starting ===")
    
    # Initialize nftables
    init_nftables()
    
    # Apply initial security groups
    apply_security_groups()
    
    # Show applied rules
    show_rules()
    
    print("\n=== Security Groups Controller Ready ===")
    print("Entering reconciliation loop...")
    
    # Enter reconciliation loop
    reconciliation_loop()


if __name__ == "__main__":
    main()
