from ..common import *

def run_s32_private_dns():
    s32_name = "32. Private DNS Discovery"
    create_scenario(
        title=s32_name,
        description="Internal zone management with private resolution.",
        resource_order=[{"type": "vpc", "label": "DNS Managed VPC"}]
    )
    dns_vpc_id = create_vpc("DNS Managed VPC", "10.49.144.0/24", scenario=s32_name)
    if dns_vpc_id:
        create_subnet(dns_vpc_id, "DNS Server (Bind9)", "10.49.144.3/32", cdc="CDC-1")
        create_subnet(dns_vpc_id, "ftp.example.com", "10.49.144.4/32", cdc="CDC-1")
        create_subnet(dns_vpc_id, "web.example.com", "10.49.144.5/32", cdc="CDC-1")
        create_route(dns_vpc_id, "example.com", "10.49.144.3", "private_link")
