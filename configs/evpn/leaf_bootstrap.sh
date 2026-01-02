#!/bin/bash
# Leaf Switch Isolation Bootstrap Script

# Dynamically find interfaces based on assigned IPs
ETH_FABRIC=$(ip -4 addr show | grep 'inet 10.0.0.' | awk '{print $NF}')
ETH_VPC_100=$(ip -4 addr show | grep 'inet 10.1.' | awk '{print $NF}')
ETH_VPC_200=$(ip -4 addr show | grep 'inet 10.2.' | awk '{print $NF}')

echo "Interfaces found: Fabric=$ETH_FABRIC, vpc-100=$ETH_VPC_100, vpc-200=$ETH_VPC_200"

# Clear existing rules just in case
iptables -F FORWARD
iptables -F INPUT

# 1. Apply Logical VPC Isolation (Forwarding)
# In this Simulator, isolation is enforced via iptables rules on the leaf switches
# to prevent cross-VPC communication, acting as a logical VPC boundary.
if [ -n "$ETH_VPC_100" ] && [ -n "$ETH_VPC_200" ]; then
    echo "Applying VPC isolation rules between vpc-100 and vpc-200..."
    iptables -A FORWARD -i "$ETH_VPC_100" -o "$ETH_VPC_200" -j REJECT --reject-with icmp-admin-prohibited
    iptables -A FORWARD -i "$ETH_VPC_200" -o "$ETH_VPC_100" -j REJECT --reject-with icmp-admin-prohibited
    
    # 2. Block Local Routing (Input to other VPC subnet)
    # This ensures the switch doesn't bridge VPCs at Layer 3 locally
    iptables -A INPUT -i "$ETH_VPC_100" -d 10.2.0.0/16 -j REJECT
    iptables -A INPUT -i "$ETH_VPC_200" -d 10.1.0.0/16 -j REJECT
fi

# 3. Install and start node_exporter for metrics
if ! which node_exporter > /dev/null; then
    apk add --no-cache prometheus-node-exporter
fi
node_exporter > /var/log/node_exporter.log 2>&1 &

# 4. Ensure vtysh.conf exists
touch /etc/frr/vtysh.conf
chown frr:frr /etc/frr/vtysh.conf
chmod 664 /etc/frr/vtysh.conf

# 5. Start FRR using the original entrypoint
exec /sbin/tini -- /usr/lib/frr/docker-start
