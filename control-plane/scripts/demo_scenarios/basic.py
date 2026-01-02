from .scenarios import (
    s01_single_vpc,
    s02_multi_tier_vpc,
    s03_secure_db_tier,
    s04_public_lb,
    s05_nat_router,
    s06_microservices_mesh,
    s07_managed_vpn,
    s08_mesh_overlay,
    s09_vpc_peering,
    s10_private_service
)

def run_basic_scenarios():
    print("\n=== Running Basic Scenarios (1-10) ===")
    s01_single_vpc.run_s01_single_vpc()
    s02_multi_tier_vpc.run_s02_multi_tier_vpc()
    s03_secure_db_tier.run_s03_secure_db_tier()
    s04_public_lb.run_s04_public_lb()
    s05_nat_router.run_s05_nat_router()
    s06_microservices_mesh.run_s06_microservices_mesh()
    s07_managed_vpn.run_s07_managed_vpn()
    s08_mesh_overlay.run_s08_mesh_overlay()
    s09_vpc_peering.run_s09_vpc_peering()
    s10_private_service.run_s10_private_service()
