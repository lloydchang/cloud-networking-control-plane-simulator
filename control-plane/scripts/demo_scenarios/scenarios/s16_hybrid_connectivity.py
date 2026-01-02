from ..common import *

def run_s16_hybrid_connectivity():
    s16_name = "16. Hybrid Connectivity: Dedicated & Redundant VPN"
    create_scenario(
        title=s16_name,
        description="High-speed dedicated cloud connectivity with encrypted fallback.",
        resource_order=[
            {"type": "vpc", "label": "Corporate Hub VPC"},
            {"type": "standalone_dc", "label": "MegaCorp DC"}
        ]
    )
    corp_vpc_id = create_vpc("Corporate Hub VPC", "10.150.0.0/16", scenario=s16_name)
    mega_dc_id = create_standalone_dc("MegaCorp DC", "192.168.0.0/16", scenario=s16_name)
    if corp_vpc_id and mega_dc_id:
        create_subnet(corp_vpc_id, "Hybrid Gateway", "10.150.1.0/24", cdc="CDC-1")
        create_standalone_dc_subnet(mega_dc_id, "On-Prem Core", "192.168.1.0/24", odc="ODC-1")
        create_route(corp_vpc_id, "192.168.0.0/16", mega_dc_id, "vpn_gateway")
        create_route(corp_vpc_id, "192.168.1.0/24", mega_dc_id, "service_endpoint")
