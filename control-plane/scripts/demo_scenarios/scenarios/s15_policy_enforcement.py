from ..common import *

def run_s15_policy_enforcement():
    s15_name = "15. Policy Enforcement"
    create_scenario(
        title=s15_name,
        description="Demonstrate network restriction and security baseline enforcement.",
        resource_order=[{"type": "vpc", "label": "Restricted VPC"}]
    )
    res_vpc_id = create_vpc("Restricted VPC", "10.140.0.0/16", scenario=s15_name)
    if res_vpc_id:
        create_subnet(res_vpc_id, "Compliant Subnet", "10.140.1.0/24", cdc="CDC-1")
        create_subnet(res_vpc_id, "Policy: No External IPv6", "10.140.2.0/24", cdc="CDC-1")
