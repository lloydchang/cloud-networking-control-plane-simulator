from ..common import *

def run_s30_standard_ipsec_vpn():
    s30_name = "30. Standard IPsec VPN (Site-to-Site)"
    create_scenario(
        title=s30_name,
        description="Secure IPsec tunnel between a VPC and on-prem.",
        resource_order=[
            {"type": "vpc", "label": "Cloud VPC"},
            {"type": "standalone_dc", "label": "On-Premises Network"}
        ]
    )
    cloud_s2s_vpc_id = create_vpc("Cloud VPC", "203.0.113.0/24", scenario=s30_name)
    on_prem_s2s_id = create_standalone_dc("On-Premises Network", "192.168.1.0/24", scenario=s30_name)
    if cloud_s2s_vpc_id and on_prem_s2s_id:
        create_subnet(cloud_s2s_vpc_id, "VPC VPN Gateway", "203.0.113.2/32", cdc="CDC-1")
        create_subnet(cloud_s2s_vpc_id, "App Server (Debian)", "203.0.113.3/32", cdc="CDC-1")
        create_standalone_dc_subnet(on_prem_s2s_id, "On-Prem VPN Gateway", "192.168.1.1/32", odc="ODC-1")
        create_standalone_dc_subnet(on_prem_s2s_id, "Windows Client", "192.168.1.2/32", odc="ODC-1")
        create_route(cloud_s2s_vpc_id, "192.168.1.0/24", on_prem_s2s_id, "vpn_gateway")
        create_route(on_prem_s2s_id, "203.0.113.0/24", cloud_s2s_vpc_id, "vpn_gateway")
