from ..common import *

def run_s17_enterprise_hub_spoke():
    s17_name = "17. Enterprise Hub-and-Spoke"
    create_scenario(
        title=s17_name,
        description="Large-scale topology with central policy management.",
        resource_order=[
            {"type": "hub", "label": "Enterprise Policy Hub"},
            {"type": "vpc", "label": "Engineering Spoke"},
            {"type": "vpc", "label": "Finance Spoke"},
            {"type": "vpc", "label": "HR Spoke"},
            {"type": "vpc", "label": "Security Services VPC"}
        ]
    )
    policy_hub_id = create_hub("Enterprise Policy Hub", region="global", scenario=s17_name)
    eng_id = create_vpc("Engineering Spoke", "10.240.0.0/16", scenario=s17_name)
    fin_id = create_vpc("Finance Spoke", "10.255.0.0/16", scenario=s17_name)
    hr_id = create_vpc("HR Spoke", "10.251.0.0/16", scenario=s17_name)
    shared_svcs_id = create_vpc("Security Services VPC", "10.252.0.0/16", scenario=s17_name)

    if policy_hub_id and eng_id and fin_id and hr_id and shared_svcs_id:
        create_subnet(eng_id, "Dev Cluster", "10.240.1.0/24", cdc="CDC-1")
        create_subnet(fin_id, "Billing App", "10.250.1.0/24", cdc="CDC-1")
        create_subnet(hr_id, "Employee Portal", "10.251.1.0/24", cdc="CDC-1")
        create_subnet(shared_svcs_id, "Security Scanner", "10.252.1.0/24", cdc="CDC-1")

        for vpc_id in [eng_id, fin_id, hr_id, shared_svcs_id]:
            create_route(vpc_id, "10.240.0.0/12", policy_hub_id, "cloud_routing_hub")
            create_hub_route(policy_hub_id, "10.240.0.0/12", vpc_id, "cloud_routing_hub")
