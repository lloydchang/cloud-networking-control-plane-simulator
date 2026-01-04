"""Tests for diagnostic logger functionality"""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock

# Set environment variables BEFORE importing diagnostic_logger
os.environ["DB_DIR"] = "."
os.environ["VERCEL"] = "1"  # Prevent directory creation during tests

from api.diagnostic_logger import DiagnosticLogger


class TestDiagnosticLogger:
    """Test suite for DiagnosticLogger class"""

    def test_diagnostic_logger_initialization(self):
        """Test that DiagnosticLogger initializes correctly"""
        logger = DiagnosticLogger()
        
        assert logger.start_time is not None
        assert logger.errors == []
        assert logger.warnings == []

    def test_diagnostic_logger_methods(self):
        """Test that DiagnosticLogger has expected methods"""
        logger = DiagnosticLogger()
        
        # Test that methods exist
        assert hasattr(logger, 'log_system_info')
        assert hasattr(logger, 'log_database_status')
        assert hasattr(logger, 'log_docker_status')
        assert hasattr(logger, 'log_api_status')
        assert hasattr(logger, 'log_error')
        assert hasattr(logger, 'log_warning')
        assert hasattr(logger, 'log_success')

    @patch('builtins.open', create=True)
    @patch('os.makedirs')
    def test_log_with_context(self, mock_makedirs, mock_open):
        """Test logging with context data"""
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        logger = DiagnosticLogger()
        context = {"vpc_id": "vpc-123", "action": "create"}
        logger.log_error("VPC operation", context)
        
        # Should not raise any exception
        assert True

    @patch('builtins.open', create=True)
    @patch('os.makedirs')
    def test_log_different_levels(self, mock_makedirs, mock_open):
        """Test logging different event types"""
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        logger = DiagnosticLogger()
        
        # Test different event types
        logger.log_error("Error message", {})
        logger.log_warning("Warning message", {})
        logger.log_success("Success message")
        
        # Should not raise any exceptions
        assert True

    def test_module_level_function(self):
        """Test the module-level functionality"""
        # This should work without errors
        logger = DiagnosticLogger()
        assert logger is not None


class TestDiagnosticLoggerIntegration:
    """Integration tests for diagnostic logger"""

    def test_diagnostic_logger_methods(self):
        """Test that all diagnostic logger methods work"""
        logger = DiagnosticLogger()
        
        # Test all available methods
        logger.log_error("Test error", {})
        logger.log_warning("Test warning", {})
        logger.log_success("Test success")
        
        # Should not raise any exceptions
        assert True
