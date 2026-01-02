from ..common import *

def run_s10_private_service():
    s10_name = "10. Private Service Connectivity"
    create_scenario(
        title=s10_name,
        description="Private service connectivity without full network peering.",
        resource_order=[
            {"type": "vpc", "label": "Consumer VPC"},
            {"type": "vpc", "label": "Provider VPC"}
        ]
    )
    cons_vpc_id = create_vpc("Consumer VPC", "10.60.0.0/16", region="us-east-1", scenario=s10_name)
    prov_vpc_id = create_vpc("Provider VPC", "10.70.0.0/16", region="us-east-1", scenario=s10_name)
    if cons_vpc_id and prov_vpc_id:
        create_subnet(cons_vpc_id, "App Subnet", "10.60.1.0/24", cdc="CDC-1")
        create_subnet(cons_vpc_id, "App Client", "10.60.1.10/32", cdc="CDC-1")
        create_subnet(prov_vpc_id, "Service Subnet", "10.70.1.0/24", cdc="CDC-1")
        create_subnet(prov_vpc_id, "Service Backend", "10.70.1.50/32", cdc="CDC-1")
        create_route(cons_vpc_id, "10.70.1.50/32", prov_vpc_id, "service_endpoint")
