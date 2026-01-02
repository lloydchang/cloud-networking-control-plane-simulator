from ..common import *

def run_s22_shared_cluster():
    s22_name = "22. Shared Cluster Infrastructure"
    create_scenario(
        title=s22_name,
        description="Shared VPC for multiple teams with governance.",
        resource_order=[{"type": "vpc", "label": "Enterprise Shared VPC"}]
    )
    shared_vpc_id = create_vpc("Enterprise Shared VPC", "10.90.0.0/16", scenario=s22_name)
    if shared_vpc_id:
        create_subnet(shared_vpc_id, "Control Plane (Shared)", "10.90.1.0/24", cdc="CDC-1")
        create_subnet(shared_vpc_id, "Team Alpha Pool", "10.90.2.0/24", cdc="CDC-1")
        create_subnet(shared_vpc_id, "Team Beta Pool", "10.90.3.0/24", cdc="CDC-2")
        create_subnet(shared_vpc_id, "Shared LB Tier", "10.90.4.0/24", cdc="CDC-1")
        create_subnet(shared_vpc_id, "Alpha App Server", "10.90.2.10/32", cdc="CDC-1")
        create_subnet(shared_vpc_id, "Beta App Server", "10.90.3.50/32", cdc="CDC-2")
