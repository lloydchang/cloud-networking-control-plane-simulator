from ..common import *

def run_s18_virtual_appliance():
    s18_name = "18. Virtual Appliance Routing"
    create_scenario(
        title=s18_name,
        description="Route traffic through a security appliance in a hub VPC.",
        resource_order=[
            {"type": "vpc", "label": "Spoke Application VPC"},
            {"type": "vpc", "label": "Transit Security VPC"},
            {"type": "hub", "label": "Transit Backbone Hub"}
        ]
    )
    app_vpc_id = create_vpc("Spoke Application VPC", "10.181.0.0/16", scenario=s18_name)
    transit_vpc_id = create_vpc("Transit Security VPC", "10.191.0.0/16", scenario=s18_name)
    transit_hub_id = create_hub("Transit Backbone Hub", scenario=s18_name)
    if app_vpc_id and transit_vpc_id and transit_hub_id:
        create_subnet(transit_vpc_id, "Firewall Appliance", "10.191.1.100/32", cdc="CDC-1")
        create_subnet(app_vpc_id, "App Server", "10.181.1.10/32", cdc="CDC-1")
        create_route(app_vpc_id, "0.0.0.0/0", "10.191.1.100", "instance")
        create_route(transit_vpc_id, "0.0.0.0/0", transit_hub_id, "cloud_routing_hub")
