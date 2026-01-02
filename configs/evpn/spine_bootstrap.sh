#!/bin/bash
# Spine Switch Bootstrap Script

# Install and start node_exporter for metrics
if ! which node_exporter > /dev/null; then
    apk add --no-cache prometheus-node-exporter
fi

# Start node_exporter in background
node_exporter > /var/log/node_exporter.log 2>&1 &

# Ensure vtysh.conf exists
touch /etc/frr/vtysh.conf
chown frr:frr /etc/frr/vtysh.conf
chmod 664 /etc/frr/vtysh.conf

# Start FRR using the original entrypoint
exec /sbin/tini -- /usr/lib/frr/docker-start
