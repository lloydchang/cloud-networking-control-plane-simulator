from ..common import *

def run_s19_hub_gateway_transit():
    s19_name = "19. Hub Gateway Transit"
    create_scenario(
        title=s19_name,
        description="Spokes use a central hub's VPN gateway.",
        resource_order=[
            {"type": "standalone_dc", "label": "On-Premises Data Center"},
            {"type": "hub", "label": "Central Hybrid Hub"},
            {"type": "vpc", "label": "Remote Spoke VPC"}
        ]
    )
    corp_dc_id = create_standalone_dc("On-Premises Data Center", "192.168.10.0/24", scenario=s19_name)
    hybrid_hub_id = create_hub("Central Hybrid Hub", scenario=s19_name)
    remote_spoke_id = create_vpc("Remote Spoke VPC", "10.201.0.0/16", scenario=s19_name)
    if corp_dc_id and hybrid_hub_id and remote_spoke_id:
        create_standalone_dc_subnet(corp_dc_id, "Mainframe Link", "192.168.10.50/32", odc="ODC-1")
        create_subnet(remote_spoke_id, "Cloud App Server", "10.201.1.10/32", cdc="CDC-11")
        create_route(corp_dc_id, "10.0.0.0/8", hybrid_hub_id, "vpn_gateway")
        create_hub_route(hybrid_hub_id, "192.168.10.0/24", corp_dc_id, "vpn_gateway")
        create_route(remote_spoke_id, "192.168.10.0/24", hybrid_hub_id, "cloud_routing_hub")
        create_hub_route(hybrid_hub_id, "10.201.0.0/16", remote_spoke_id, "cloud_routing_hub")
