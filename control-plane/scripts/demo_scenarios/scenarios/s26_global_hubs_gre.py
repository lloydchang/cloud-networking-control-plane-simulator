from ..common import *

def run_s26_global_hubs_gre():
    s26_name = "26. Global Transit: Multi-Region Hubs with GRE Support"
    create_scenario(
        title=s26_name,
        description="Integration of SASE and SD-WAN using GRE tunneling over global transit hubs",
        resource_order=[
            {"type": "hub", "label": "Regional Hub A"},
            {"type": "hub", "label": "Regional Hub B"},
            {"type": "vpc", "label": "Security Appliance VPC"}
        ]
    )
    hub_a_id = create_hub("Regional Hub A", region="us-east", scenario=s26_name)
    hub_b_id = create_hub("Regional Hub B", region="us-west", scenario=s26_name)
    sec_vpc_id = create_vpc("Security Appliance VPC", "10.170.0.0/16", scenario=s26_name)
    if hub_a_id and hub_b_id and sec_vpc_id:
        create_subnet(sec_vpc_id, "GRE Termination", "10.170.1.0/24", cdc="CDC-1")
        create_hub_route(hub_a_id, "10.170.0.0/16", sec_vpc_id, "cloud_routing_hub")
        create_hub_route(hub_b_id, "10.170.0.0/16", sec_vpc_id, "cloud_routing_hub")
        create_hub_route(hub_a_id, "0.0.0.0/0", hub_b_id, "hub_peer")
