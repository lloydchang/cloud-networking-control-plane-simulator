#!/usr/bin/env python3
"""
Unit tests for generate_site.py scenario extraction functionality.
"""

import unittest
import os
import tempfile
import sys

# Add the control-plane directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import directly from the module file
import importlib.util
spec = importlib.util.spec_from_file_location("generate_site.py")
generate_site = importlib.util.module_from_spec(spec).extract_scenarios_from_vpc_md


class TestScenarioExtraction(unittest.TestCase):
    """Test scenario extraction from VPC.md"""
    
    def setUp(self):
        """Create a temporary VPC.md file for testing"""
        self.temp_dir = tempfile.mkdtemp()
        self.vpc_md_path = os.path.join(self.temp_dir, 'VPC.md')
        
        # Create test VPC.md content with multiple scenarios
        test_content = """# VPC Scenarios

### 1. Single VPC
* **Goal**: Simplest cloud network with one public subnet
* **Architecture**: Basic VPC with internet gateway

#### Resources
* VPC: Web VPC

### 2. Multi-tier VPC  
* **Goal**: Professional VPC with public/private segmentation
* **Architecture**: Multi-tier application architecture

#### Resources
* VPC: App VPC
* VPC: DB VPC

### 3. Complex Scenario
* **Goal**: Complex multi-resource scenario
* **Architecture**: Hub and spoke design

#### Resources
* VPC: Hub VPC
* Hub: Central Hub
* Data Center: On-prem DC
"""
        
        with open(self.vpc_md_path, 'w') as f:
            f.write(test_content)
    
    def tearDown(self):
        """Clean up temporary files"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_extract_scenarios_with_resources(self):
        """Test that scenarios are extracted with proper resource structure"""
        # Temporarily override the VPC.md path
        original_path = sys.modules['scripts.generate_site'].__file__
        sys.modules['scripts.generate_site'].__file__ = self.vpc_md_path
        
        try:
            scenarios = extract_scenarios_from_vpc_md()
            
            # Should extract 3 scenarios
            self.assertEqual(len(scenarios), 3)
            
            # Check that scenarios have proper structure
            for scenario in scenarios:
                self.assertIn('title', scenario)
                self.assertIn('description', scenario)
                self.assertIn('resources', scenario)
                
                # Check that resources are properly typed
                for resource in scenario['resources']:
                    self.assertIn('type', resource)
                    self.assertIn('label', resource)
                    self.assertIn(resource['type'], ['vpc', 'hub', 'standalone_dc'])
        
        finally:
            # Restore original path
            sys.modules['scripts.generate_site'].__file__ = original_path
    
    def test_extract_scenarios_handles_missing_file(self):
        """Test graceful fallback when VPC.md is missing"""
        original_path = sys.modules['scripts.generate_site'].__file__
        sys.modules['scripts.generate_site'].__file__ = '/nonexistent/path/VPC.md'
        
        try:
            scenarios = extract_scenarios_from_vpc_md()
            
            # Should return default scenarios
            self.assertEqual(scenarios, ["demo", "basic", "advanced"])
            
        finally:
            # Restore original path
            sys.modules['scripts.generate_site'].__file__ = original_path
    
    def test_extract_scenarios_handles_invalid_content(self):
        """Test graceful fallback when VPC.md has invalid content"""
        original_path = sys.modules['scripts.generate_site'].__file__
        sys.modules['scripts.generate_site'].__file__ = self.vpc_md_path
        
        # Create invalid VPC.md
        with open(self.vpc_md_path, 'w') as f:
            f.write("Invalid content without scenario headers")
        
        try:
            scenarios = extract_scenarios_from_vpc_md()
            
            # Should return default scenarios
            self.assertEqual(scenarios, ["demo", "basic", "advanced"])
            
        finally:
            # Restore original path
            sys.modules['scripts.generate_site'].__file__ = original_path


if __name__ == '__main__':
    unittest.main()
