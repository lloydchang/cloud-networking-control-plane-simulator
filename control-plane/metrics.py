from prometheus_client import Counter, Gauge, Histogram

# ============================================================================
# Centralized Prometheus Metrics for Cloud Networking Controller
# ============================================================================

METRICS = {
    "vpcs_total": Gauge("control_plane_vpcs_total", "Total count of active VPCs"),
    "subnets_total": Gauge("control_plane_subnets_total", "Total count of active subnets"),
    "routes_total": Gauge("control_plane_routes_total", "Total count of active routes"),
    "security_groups_total": Gauge("control_plane_security_groups_total", "Total count of security groups"),
    "nat_gateways_total": Gauge("control_plane_nat_gateways_total", "Total count of NAT gateways"),
    "internet_gateways_total": Gauge("control_plane_internet_gateways_total", "Total count of internet gateways"),
    "vpn_gateways_total": Gauge("control_plane_vpn_gateways_total", "Total count of VPN Gateways"),
    "mesh_nodes_total": Gauge("control_plane_mesh_nodes_total", "Total count of Mesh Nodes"),
    "reconciliation_latency": Histogram(
        "control_plane_reconciliation_duration_ms",
        "Time taken for reconciliation in milliseconds",
        buckets=(10, 50, 100, 250, 500, 1000, 2500, 5000),
    ),
    "api_requests": Counter(
        "control_plane_api_requests_total",
        "Total REST API requests",
        ["method", "endpoint"],
    ),
    "reconciliation_actions": Counter(
        "control_plane_reconciliation_actions_total",
        "Count of reconciliation actions",
        ["action_type"],
    ),
}
