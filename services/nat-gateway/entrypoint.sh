#!/bin/bash
set -e

echo "=== NAT Gateway Starting ==="

# Enable IP forwarding
echo 1 > /proc/sys/net/ipv4/ip_forward

# Load nftables configuration
if [ -f /etc/nftables.conf ]; then
    echo "Loading nftables rules..."
    nft -f /etc/nftables.conf
    echo "NAT rules applied successfully"
else
    echo "No nftables.conf found, creating default rules..."
    nft add table ip nat
    nft add chain ip nat postrouting { type nat hook postrouting priority srcnat \; }
    # SNAT for vpc-100 (10.1.0.0/16)
    nft add rule ip nat postrouting ip saddr 10.1.0.0/16 oifname "eth1" masquerade
    # SNAT for vpc-200 (10.2.0.0/16)
    nft add rule ip nat postrouting ip saddr 10.2.0.0/16 oifname "eth1" masquerade
fi

echo "Current NAT rules:"
nft list ruleset

# Install and start node_exporter for metrics
if ! which node_exporter > /dev/null; then
    echo "Installing prometheus-node-exporter..."
    apk add --no-cache prometheus-node-exporter
fi

echo "Starting node_exporter..."
node_exporter > /var/log/node_exporter.log 2>&1 &

echo "=== NAT Gateway Ready ==="

# Keep container running and log NAT translations
exec tail -f /dev/null
