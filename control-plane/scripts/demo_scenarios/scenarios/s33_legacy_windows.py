from ..common import *

def run_s33_legacy_windows():
    s33_name = "33. Legacy Windows Integration"
    create_scenario(
        title=s33_name,
        description="Legacy workloads with multiple interfaces.",
        resource_order=[{"type": "vpc", "label": "Legacy Windows VPC"}]
    )
    win_vpc_id = create_vpc("Legacy Windows VPC", "10.49.96.0/24", scenario=s33_name)
    if win_vpc_id:
        create_subnet(win_vpc_id, "Public Mgmt", "10.49.96.0/28", cdc="CDC-1")
        create_subnet(win_vpc_id, "Private Data", "10.49.96.16/28", cdc="CDC-1")
        create_subnet(win_vpc_id, "Windows AD DC", "10.49.96.4/32", cdc="CDC-1")
        create_subnet(win_vpc_id, "Windows SQL", "10.49.96.20/32", cdc="CDC-1")
        create_route(win_vpc_id, "10.49.96.0/28", "igw-auto", "internet_gateway")
        create_route(win_vpc_id, "10.0.0.0/8", "vpn-auto", "vpn_gateway")
