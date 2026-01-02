from ..common import *

def run_s31_remote_access_vpn():
    s31_name = "31. Remote Access VPN"
    create_scenario(
        title=s31_name,
        description="Road Warrior connectivity via IKEv2/IPsec.",
        resource_order=[{"type": "vpc", "label": "Remote Access Hub VPC"}]
    )
    rw_vpc_id = create_vpc("Remote Access Hub VPC", "10.200.0.0/16", scenario=s31_name)
    if rw_vpc_id:
        create_subnet(rw_vpc_id, "VPN Endpoints Pool", "192.5.2.0/24", cdc="CDC-1")
        create_subnet(rw_vpc_id, "Internal Services", "10.200.1.0/24", cdc="CDC-1")
        create_subnet(rw_vpc_id, "Identity Server", "10.200.1.5/32", cdc="CDC-1")
        create_route(rw_vpc_id, "192.5.2.0/24", "vpn-auto", "vpn_gateway")
