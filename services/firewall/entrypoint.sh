#!/bin/bash
set -e

echo "=== Firewall Service Starting ==="

# Start prometheus-node-exporter in the background
echo "Starting prometheus-node-exporter..."
prometheus-node-exporter > /var/log/node_exporter.log 2>&1 &

# Start the security groups controller
echo "Starting security groups controller..."
exec python -u security_groups.py
