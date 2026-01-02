from ..common import *

def run_s29_heterogeneous_lb():
    s29_name = "29. Heterogeneous Load Balancing"
    create_scenario(
        title=s29_name,
        description="Load Balancer distributing traffic across mixed-os backends.",
        resource_order=[{"type": "vpc", "label": "Load Balanced VPC"}]
    )
    het_lb_vpc_id = create_vpc("Load Balanced VPC", "10.49.144.0/20", scenario=s29_name)
    if het_lb_vpc_id:
        create_subnet(het_lb_vpc_id, "Load Balancer", "10.49.144.3/32", cdc="CDC-1")
        create_subnet(het_lb_vpc_id, "Host 1 (Nginx/Ubuntu)", "10.49.144.4/32", cdc="CDC-1")
        create_subnet(het_lb_vpc_id, "Host 2 (Apache/Rocky)", "10.49.144.5/32", cdc="CDC-2")
        create_subnet(het_lb_vpc_id, "Host 3 (Nginx/Debian)", "10.49.144.6/32", cdc="CDC-1")
        create_subnet(het_lb_vpc_id, "Host 4 (Management)", "10.49.144.7/32", cdc="CDC-1")
        create_route(het_lb_vpc_id, "0.0.0.0/0", "10.49.144.3", "internet_gateway")
