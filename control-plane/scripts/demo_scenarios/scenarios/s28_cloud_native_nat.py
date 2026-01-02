from ..common import *

def run_s28_cloud_native_nat():
    s28_name = "28. Cloud Native NAT Router"
    create_scenario(
        title=s28_name,
        description="Linux-based NAT router managing ingress and egress.",
        resource_order=[{"type": "vpc", "label": "NAT Router VPC"}]
    )
    nat_router_vpc_id = create_vpc("NAT Router VPC", "10.49.96.0/20", scenario=s28_name)
    if nat_router_vpc_id:
        create_subnet(nat_router_vpc_id, "Host 1 (NAT Router/DNS)", "10.49.96.3/32", cdc="CDC-1")
        create_subnet(nat_router_vpc_id, "Host 2 (FTP Server)", "10.49.96.4/32", cdc="CDC-1")
        create_subnet(nat_router_vpc_id, "Host 3 (Web Server)", "10.49.96.5/32", cdc="CDC-1")
        create_subnet(nat_router_vpc_id, "Host 4 (Windows Server)", "10.49.96.6/32", cdc="CDC-1")
        create_route(nat_router_vpc_id, "0.0.0.0/0", "10.49.96.3", "instance")
