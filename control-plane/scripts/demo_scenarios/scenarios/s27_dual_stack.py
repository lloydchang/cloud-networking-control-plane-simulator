from ..common import *

def run_s27_dual_stack():
    s27_name = "27. Dual-Stack Infrastructure: IPv4 & IPv6 Coexistence"
    create_scenario(
        title=s27_name,
        description="Modern network design supporting concurrent IPv4 and IPv6 traffic flows",
        resource_order=[{"type": "vpc", "label": "Dual-Stack VPC"}]
    )
    ds_vpc_id = create_vpc("Dual-Stack VPC", "10.180.0.0/16 & 2001:db8::1/64", scenario=s27_name)
    if ds_vpc_id:
        create_subnet(ds_vpc_id, "Dual-Stack Subnet", "10.180.1.0/24", cdc="CDC-1")
        create_subnet(ds_vpc_id, "IPv6 Resource", "2001:db8:1::10/128", cdc="CDC-1")
