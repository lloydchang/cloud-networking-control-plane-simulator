from ..common import *

def run_s20_data_scale_network():
    s20_name = "20. Data-Scale Network: Secondary CIDR Expansion & Pre-initialized Instances"
    create_scenario(
        title=s20_name,
        description="High-density networking with secondary CIDR ranges to provide ready-state instance pools",
        resource_order=[{"type": "vpc", "label": "High-Density Cluster VPC"}]
    )
    # Using RFC 6598 range (100.64.0.0/10) for carrier-grade NAT / secondary expansion as per typical large scale k8s patterns
    data_scale_vpc_id = create_vpc("High-Density Cluster VPC", "10.22.0.0/16 & 100.64.0.0/10", secondary_cidrs=["100.64.0.0/10"], scenario=s20_name)
    if data_scale_vpc_id:
        create_subnet(data_scale_vpc_id, "Management Subnet", "10.22.1.0/24", cdc="CDC-1")
        # Ready-State Pool Subnets (Dense)
        create_subnet(data_scale_vpc_id, "Compute Pool 1 (Dense)", "100.64.0.0/18", cdc="CDC-1")
        create_subnet(data_scale_vpc_id, "Compute Pool 2 (Dense)", "100.64.64.0/18", cdc="CDC-2")
        # Pre-initialized instances
        create_subnet(data_scale_vpc_id, "Dense Resource 1", "100.64.1.10/32", cdc="CDC-1")
        create_subnet(data_scale_vpc_id, "Dense Resource 2", "100.64.65.20/32", cdc="CDC-2")
