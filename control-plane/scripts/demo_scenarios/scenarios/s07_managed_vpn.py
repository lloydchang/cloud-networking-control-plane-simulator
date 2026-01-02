from ..common import *

def create_vpn_gateway(vpc_id, endpoint, pubkey, allowed_ips):
    # Per-VPC endpoint instead of global /vpn-gateways
    run_request("POST", f"/vpcs/{vpc_id}/vpn_gateways", data={
        "endpoint": endpoint,
        "public_key": pubkey,
        "allowed_ips": allowed_ips
    })

def run_s07_managed_vpn():
    s7_name = "7. Managed VPN"
    create_scenario(
        title=s7_name,
        description="Secure cloud-to-on-prem or region-to-region connectivity.",
        resource_order=[
            {"type": "vpc", "label": "us-east-vpc"},
            {"type": "vpc", "label": "us-west-vpc"}
        ]
    )
    west_id = create_vpc("us-west-vpc", "172.16.2.0/24", region="us-west", scenario=s7_name)
    east_id = create_vpc("us-east-vpc", "172.16.1.0/24", region="us-east", scenario=s7_name)
    
    if west_id: create_subnet(west_id, "Primary", "172.16.2.0/24", cdc="CDC-11")
    if east_id: create_subnet(east_id, "Primary", "172.16.1.0/24", cdc="CDC-1")
    
    if west_id and east_id:
        create_vpn_gateway(west_id, "192.0.2.1:51820", "US_WEST_PUB_KEY", "10.10.0.1/32")
        create_vpn_gateway(east_id, "192.0.2.2:51820", "US_EAST_PUB_KEY", "10.10.0.2/32")
        create_route(west_id, "172.16.1.0/24", east_id, "vpn_gateway")
