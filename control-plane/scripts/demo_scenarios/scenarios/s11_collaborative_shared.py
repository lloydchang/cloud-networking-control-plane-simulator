from ..common import *

def run_s11_collaborative_shared():
    s11_name = "11. Collaborative Shared Network"
    create_scenario(
        title=s11_name,
        description="Centralized network management with departmental isolation.",
        resource_order=[{"type": "vpc", "label": "Shared Network VPC"}]
    )
    infra_vpc_id = create_vpc("Shared Network VPC", "11.80.0.0/16", region="us-east-1", scenario=s11_name)
    if infra_vpc_id:
        create_subnet(infra_vpc_id, "Human Resources Subnet", "11.80.1.0/24", cdc="CDC-1")
        create_subnet(infra_vpc_id, "HR Server", "11.80.1.10/32", cdc="CDC-1")
        create_subnet(infra_vpc_id, "Finance Department Subnet", "11.80.2.0/24", cdc="CDC-2")
        create_subnet(infra_vpc_id, "Finance Server", "11.80.2.20/32", cdc="CDC-2")
        create_subnet(infra_vpc_id, "Central IT Admin Subnet", "11.80.3.0/24", cdc="CDC-1")
        create_subnet(infra_vpc_id, "IT Controller", "11.80.3.5/32", cdc="CDC-1")
