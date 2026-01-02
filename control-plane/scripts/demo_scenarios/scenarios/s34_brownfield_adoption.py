"""
Scenario 34: Brownfield Endpoint Adoption

This scenario validates late-stage control plane behavior and VPC View UI semantics
by adopting pre-existing workloads into a newly declared VPC without redeploying,
restarting, or reattaching containers.

Preconditions:
- Endpoints exist on the fabric as containers.
- Endpoint IP addresses fall within the declared VPC CIDR.
- The control plane is running and actively reconciling state.

Behavior Under Test:
- Discovery of existing endpoints prior to VPC creation.
- Logical ownership reassignment of endpoints to the new VPC.
- VPC View accurately reflects endpoints' new membership and subnet placement.
- Enforcement of isolation using native VRF when available, with fallback to iptables-based isolation when not supported.
- Withdrawal and re-advertisement of EVPN Type-2 routes under a new VNI.
- Optional Type-5 route injection when an Internet Gateway is attached.

Success Criteria:
- No containers are restarted or moved at the Docker layer.
- Endpoints appear in the VPC View within the correct VPC boundary and subnet.
- Control plane convergence is idempotent and non-disruptive.
- EVPN control plane reflects the new VPC ownership.
- Logical boundaries in the VPC View match declared intent.

Failure Semantics:
- If no eligible brownfield endpoints are detected, the scenario fails immediately.
- Failure indicates an invalid test environment, not a simulator bug.
- Any endpoint missing or incorrectly placed in the VPC View constitutes failure.

This scenario models real-world brownfield adoption workflows used by cloud providers,
ensuring both control plane correctness and UI fidelity in representing logical VPC ownership.
"""

from ..common import *

def run_s34_brownfield_adoption():
    s34_name = "34. Brownfield Endpoint Adoption"
    create_scenario(
        title=s34_name,
        description="Adopt existing workloads into a new VPC without redeployment, ensuring accurate VPC View mapping.",
        resource_order=[{"type": "vpc", "label": "Brownfield VPC"}]
    )

    # Check that brownfield endpoints exist within the intended CIDR
    assert_brownfield_endpoints_exist("10.1.0.0/16", s34_name)

    # Create the new VPC for adoption
    bf_vpc_id = create_vpc("Brownfield VPC", "10.1.0.0/16", scenario=s34_name)
    if bf_vpc_id:
        # Add subnets mapping to the two servers
        create_subnet(bf_vpc_id, "Adopted Subnet A", "10.1.1.0/24", cdc="CDC-1")  # server-1: 10.1.1.10
        create_subnet(bf_vpc_id, "Adopted Subnet B", "10.1.2.0/24", cdc="CDC-1")  # server-2: 10.1.2.10

        # Attach a default route via Internet Gateway
        create_route(bf_vpc_id, "0.0.0.0/0", "igw-auto", "internet_gateway")
