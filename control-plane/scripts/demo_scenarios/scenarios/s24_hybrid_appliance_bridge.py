from ..common import *

def run_s24_hybrid_appliance_bridge():
    s24_name = "24. Hybrid Appliance Bridge"
    create_scenario(
        title=s24_name,
        description="Managed cloud VPN connecting to a custom software appliance.",
        resource_order=[
            {"type": "vpc", "label": "Provider Network (Managed)"},
            {"type": "vpc", "label": "Consumer Network (Software Appliance)"}
        ]
    )
    prov_net_id = create_vpc("Provider Network (Managed)", "10.241.0.0/16", scenario=s24_name)
    cons_net_id = create_vpc("Consumer Network (Software Appliance)", "10.242.0.0/16", scenario=s24_name)
    if prov_net_id and cons_net_id:
        create_subnet(prov_net_id, "Cloud Services", "10.241.1.0/24", cdc="CDC-1")
        create_subnet(cons_net_id, "Appliance Subnet", "10.242.1.0/24", cdc="CDC-1")
        create_subnet(cons_net_id, "Software Gateway Server", "10.242.1.10/32", cdc="CDC-1")
        create_route(prov_net_id, "10.242.0.0/16", cons_net_id, "vpn_gateway")
        create_route(cons_net_id, "10.241.0.0/16", prov_net_id, "vpn_gateway")
