#!/usr/bin/env python3
"""
Simple test to verify static site scenario rendering.
"""

import json
import os
import re
import sys


def test_static_site():
    """Test that static site has proper scenario structure"""
    html_path = 'docs/index.html'
    
    if not os.path.exists(html_path):
        print(f'❌ File not found: {html_path}')
        return False
    
    try:
        with open(html_path, 'r') as f:
            content = f.read()
    except Exception as e:
        print(f'❌ Error reading file: {e}')
        return False

    # Check both data structures exist
    has_static_scenarios = 'window.STATIC_SCENARIOS = [' in content
    has_vpc_data = 'window.STATIC_VPC_DATA = {' in content
    
    if not has_static_scenarios:
        print('❌ STATIC_SCENARIOS not found')
        return False
    print('✅ STATIC_SCENARIOS found')
    
    if not has_vpc_data:
        print('❌ STATIC_VPC_DATA not found')
        return False
    print('✅ STATIC_VPC_DATA found')
    
    # Parse STATIC_SCENARIOS (simple string array)
    start = content.find('window.STATIC_SCENARIOS = [')
    end = content.find('];', start)
    if start == -1 or end == -1:
        print('❌ Could not find STATIC_SCENARIOS boundaries')
        return False
    
    scenarios_str = content[start + len('window.STATIC_SCENARIOS = '):end + 1]
    
    try:
        scenario_names = json.loads(scenarios_str)
        print(f'✅ Parsed {len(scenario_names)} scenario names from STATIC_SCENARIOS')
    except json.JSONDecodeError as e:
        print(f'❌ Error parsing STATIC_SCENARIOS: {e}')
        return False
    
    # Parse STATIC_VPC_DATA to get scenarios with resources
    # Extract just the scenarios array from STATIC_VPC_DATA
    scenarios_match = re.search(r'"scenarios":\s*\[', content)
    if not scenarios_match:
        print('❌ Could not find scenarios in STATIC_VPC_DATA')
        return False
    
    # Find the matching closing bracket for the scenarios array
    start_pos = scenarios_match.end() - 1  # Position of opening [
    bracket_count = 0
    end_pos = start_pos
    
    for i, char in enumerate(content[start_pos:], start=start_pos):
        if char == '[':
            bracket_count += 1
        elif char == ']':
            bracket_count -= 1
            if bracket_count == 0:
                end_pos = i + 1
                break
    
    scenarios_json = content[start_pos:end_pos]
    
    try:
        scenarios = json.loads(scenarios_json)
        print(f'✅ Parsed {len(scenarios)} scenarios from STATIC_VPC_DATA')
        
        # Check if scenarios have resources
        with_resources = [s for s in scenarios if s.get('resources')]
        print(f'✅ Scenarios with resources: {len(with_resources)}')
        
        # Check a few specific scenarios
        test_scenarios = ['1. Single VPC', '2. Multi-tier VPC', '12. Kubernetes Hybrid Network']
        found_count = 0
        
        for test_scenario in test_scenarios:
            matching = [s for s in scenarios if s.get('title') == test_scenario]
            if matching:
                scenario = matching[0]
                resources = scenario.get('resources', [])
                print(f'✅ {test_scenario}: Found with {len(resources)} resources')
                found_count += 1
            else:
                print(f'⚠️ {test_scenario}: Not found (checking partial match...)')
                # Try partial match
                partial = [s for s in scenarios if test_scenario.split('. ')[-1] in s.get('title', '')]
                if partial:
                    scenario = partial[0]
                    resources = scenario.get('resources', [])
                    print(f'   ✅ Partial match: "{scenario.get("title")}" with {len(resources)} resources')
                    found_count += 1
        
        return len(with_resources) > 0 and found_count > 0
        
    except json.JSONDecodeError as e:
        print(f'❌ Error parsing scenarios as JSON: {e}')
        if hasattr(e, 'lineno'):
            lines = scenarios_json.split('\n')
            if e.lineno <= len(lines):
                print(f'   Problem near line {e.lineno}: {lines[e.lineno - 1][:100]}')
        return False
    except Exception as e:
        print(f'❌ Unexpected error: {e}')
        return False


if __name__ == '__main__':
    success = test_static_site()
    print()
    if success:
        print('✅ Test PASSED: Static site scenario rendering working correctly')
    else:
        print('❌ Test FAILED: Static site scenario rendering broken')
    
    # Exit with appropriate code for CI/CD
    sys.exit(0 if success else 1)