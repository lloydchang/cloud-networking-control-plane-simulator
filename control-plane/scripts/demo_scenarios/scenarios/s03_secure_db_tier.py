from ..common import *

def run_s03_secure_db_tier():
    s3_name = "3. Secure Database Tier"
    create_scenario(
        title=s3_name,
        description="Isolation of sensitive data between web DMZ and secure backend.",
        resource_order=[{"type": "vpc", "label": "Production Environment"}]
    )
    db_vpc_id = create_vpc("Production Environment", "10.20.0.0/16", region="us-east-1", scenario=s3_name)
    if db_vpc_id:
        create_subnet(db_vpc_id, "Web DMZ", "10.20.1.0/24", cdc="CDC-1")
        create_subnet(db_vpc_id, "Web Server", "10.20.1.10/32", cdc="CDC-1")
        create_subnet(db_vpc_id, "Secure DB Tier", "10.20.2.0/24", cdc="CDC-1")
        create_subnet(db_vpc_id, "Database Server", "10.20.2.50/32", cdc="CDC-1")
        run_request("POST", f"/vpcs/{db_vpc_id}/internet-gateways")
        create_route(db_vpc_id, "0.0.0.0/0", "igw-auto", "internet_gateway")
