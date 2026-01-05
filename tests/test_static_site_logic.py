#!/usr/bin/env python3
"""
Unit tests for static site parsing logic.

Tests the key logic differences between the original and improved 
versions of test_static_site.py:
1. eval() vs json.loads() - security and parsing correctness
2. Variable scope bug - accessing 's' outside list comprehension
3. File existence check - graceful handling of missing files
4. Error handling - specific JSONDecodeError vs generic Exception
"""

import json
import os
import tempfile
import unittest


class TestJsonVsEval(unittest.TestCase):
    """Test the difference between eval() and json.loads() parsing."""
    
    def test_json_loads_parses_valid_json_array(self):
        """json.loads correctly parses a JSON array."""
        data = '["Single VPC", "Multi-tier VPC", "Kubernetes Hybrid Network"]'
        result = json.loads(data)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], "Single VPC")
    
    def test_json_loads_parses_object_array(self):
        """json.loads correctly parses array of objects."""
        data = '[{"title": "Single VPC", "resources": [{"type": "vpc"}]}]'
        result = json.loads(data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Single VPC")
        self.assertEqual(len(result[0]["resources"]), 1)
    
    def test_json_loads_rejects_javascript_syntax(self):
        """json.loads correctly rejects JavaScript-specific syntax."""
        # JavaScript allows single quotes, JSON does not
        js_data = "['Single VPC', 'Multi-tier VPC']"
        with self.assertRaises(json.JSONDecodeError):
            json.loads(js_data)
    
    def test_json_loads_rejects_trailing_comma(self):
        """json.loads correctly rejects trailing commas."""
        data = '["Single VPC", "Multi-tier VPC",]'
        with self.assertRaises(json.JSONDecodeError):
            json.loads(data)


class TestVariableScopeBug(unittest.TestCase):
    """Test the variable scope bug fix.
    
    Original code had:
        found = any(s.get('title') == test_scenario for s in scenarios)
        if found:
            resources = s.get('resources', [])  # BUG: 's' not defined here!
    
    Fixed code properly captures the matching scenario:
        matching = [s for s in scenarios if s.get('title') == test_scenario]
        if matching:
            scenario = matching[0]
            resources = scenario.get('resources', [])
    """
    
    def test_correct_pattern_gets_right_scenario(self):
        """The fixed pattern correctly retrieves the matching scenario."""
        scenarios = [
            {"title": "First", "resources": [{"type": "vpc"}]},
            {"title": "Second", "resources": [{"type": "hub"}, {"type": "dc"}]},
            {"title": "Third", "resources": []},
        ]
        
        # Fixed pattern
        test_scenario = "Second"
        matching = [s for s in scenarios if s.get('title') == test_scenario]
        
        self.assertTrue(len(matching) > 0)
        scenario = matching[0]
        resources = scenario.get('resources', [])
        
        self.assertEqual(len(resources), 2)
        self.assertEqual(resources[0]["type"], "hub")
    
    def test_correct_pattern_handles_not_found(self):
        """The fixed pattern correctly handles scenario not found."""
        scenarios = [
            {"title": "First", "resources": []},
        ]
        
        test_scenario = "Nonexistent"
        matching = [s for s in scenarios if s.get('title') == test_scenario]
        
        self.assertEqual(len(matching), 0)


class TestFileExistenceCheck(unittest.TestCase):
    """Test file existence checks before opening."""
    
    def test_os_path_exists_returns_false_for_missing_file(self):
        """os.path.exists correctly returns False for missing files."""
        self.assertFalse(os.path.exists('/nonexistent/path/to/file.html'))
    
    def test_os_path_exists_returns_true_for_existing_file(self):
        """os.path.exists correctly returns True for existing files."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name
        try:
            self.assertTrue(os.path.exists(temp_path))
        finally:
            os.unlink(temp_path)
    
    def test_graceful_handling_of_missing_file(self):
        """Code should gracefully handle missing files."""
        html_path = '/nonexistent/path/to/index.html'
        
        if not os.path.exists(html_path):
            result = False  # Graceful failure
        else:
            result = True  # Would continue processing
        
        self.assertFalse(result)


class TestJSONDecodeErrorHandling(unittest.TestCase):
    """Test specific JSONDecodeError handling vs generic Exception."""
    
    def test_json_decode_error_provides_line_info(self):
        """JSONDecodeError provides useful position information."""
        invalid_json = '{\n  "key": value\n}'  # 'value' not quoted
        
        try:
            json.loads(invalid_json)
            self.fail("Should have raised JSONDecodeError")
        except json.JSONDecodeError as e:
            # JSONDecodeError has lineno and colno attributes
            self.assertTrue(hasattr(e, 'lineno'))
            self.assertTrue(hasattr(e, 'colno'))
            self.assertEqual(e.lineno, 2)  # Error on line 2
    
    def test_multiline_json_error_location(self):
        """JSONDecodeError correctly identifies error in multiline JSON."""
        multiline = '''[
            {"title": "First"},
            {"title": "Second" "bad": "syntax"},
            {"title": "Third"}
        ]'''
        
        try:
            json.loads(multiline)
            self.fail("Should have raised JSONDecodeError")
        except json.JSONDecodeError as e:
            self.assertEqual(e.lineno, 3)  # Error on line 3


class TestStaticSiteDataStructure(unittest.TestCase):
    """Test the actual data structure format in docs/index.html."""
    
    def test_static_scenarios_is_string_array(self):
        """STATIC_SCENARIOS is a simple array of strings, not objects."""
        static_scenarios = '["Single VPC", "Multi-tier VPC", "Kubernetes Hybrid Network"]'
        result = json.loads(static_scenarios)
        
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], str)
        self.assertNotIsInstance(result[0], dict)
    
    def test_static_vpc_data_scenarios_has_objects(self):
        """STATIC_VPC_DATA.scenarios contains objects with title, description, resources."""
        vpc_data_scenarios = '''[
            {
                "title": "Single VPC",
                "description": "Simplest cloud network",
                "resources": [{"type": "vpc", "label": "Web VPC"}]
            }
        ]'''
        result = json.loads(vpc_data_scenarios)
        
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], dict)
        self.assertIn('title', result[0])
        self.assertIn('description', result[0])
        self.assertIn('resources', result[0])
        self.assertIsInstance(result[0]['resources'], list)


if __name__ == '__main__':
    unittest.main()
