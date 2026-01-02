#!/usr/bin/env python3
"""
Create Demo Scenarios for Cloud Networking Control Plane Simulator

Usage:
  Runs automatically on 'make up' or manual execution.
"""

from demo_scenarios.common import wipe_demo_resources
from demo_scenarios.basic import run_basic_scenarios
from demo_scenarios.intermediate import run_intermediate_scenarios
from demo_scenarios.advanced import run_advanced_scenarios

def main():
    print("=== Generating Cloud Networking Control Plane Demo Scenarios ===")
    
    # Clean up any partial or duplicate resources from previous runs
    wipe_demo_resources()
    
    # Run modularized scenarios
    run_basic_scenarios()
    run_intermediate_scenarios()
    run_advanced_scenarios()

    print("\n=== All Scenarios Provisioned Successfully ===")

if __name__ == "__main__":
    main()
