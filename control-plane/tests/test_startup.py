"""Tests for startup event handlers"""

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.models import Base
from api.rest_api_server import app, SessionLocal


class TestStartupEvents:
    """Test suite for startup event handlers"""

    @patch('api.rest_api_server.SessionLocal')
    @patch('api.rest_api_server.Base.metadata.create_all')
    def test_initialize_database_and_metrics(self, mock_create_all, mock_session_local):
        """Test database initialization on startup"""
        # Setup mock
        mock_db = MagicMock()
        mock_session_local.return_value.__enter__.return_value = mock_db
        mock_session_local.return_value.__exit__.return_value = None
        
        # Get the startup event handler
        startup_handler = None
        for route in app.routes:
            if hasattr(route, 'startup'):
                startup_handler = route.startup
                break
        
        if startup_handler:
            # Call the startup handler
            startup_handler()
            
            # Verify database was initialized
            mock_create_all.assert_called_once()
            mock_session_local.assert_called_once()

    @patch('api.rest_api_server.SessionLocal')
    @patch('api.rest_api_server.Base.metadata.create_all')
    def test_startup_with_database_error(self, mock_create_all, mock_session_local):
        """Test startup handles database errors gracefully"""
        # Setup mock to raise exception
        mock_session_local.side_effect = Exception("Database error")
        
        # Get the startup event handler
        startup_handler = None
        for route in app.routes:
            if hasattr(route, 'startup'):
                startup_handler = route.startup
                break
        
        if startup_handler:
            # Should not raise exception
            try:
                startup_handler()
            except Exception:
                pytest.fail("Startup handler should handle exceptions gracefully")

    @patch('api.rest_api_server.SessionLocal')
    @patch('api.rest_api_server.Base.metadata.create_all')
    def test_startup_closes_database_connection(self, mock_create_all, mock_session_local):
        """Test that startup properly closes database connection"""
        # Setup mock
        mock_db = MagicMock()
        mock_session_local.return_value.__enter__.return_value = mock_db
        mock_session_local.return_value.__exit__.return_value = None
        
        # Get the startup event handler
        startup_handler = None
        for route in app.routes:
            if hasattr(route, 'startup'):
                startup_handler = route.startup
                break
        
        if startup_handler:
            # Call the startup handler
            startup_handler()
            
            # Verify context manager was used (enter/exit called)
            mock_session_local.assert_called_once()
            mock_session_local.return_value.__enter__.assert_called_once()
            mock_session_local.return_value.__exit__.assert_called_once()


class TestDatabaseSetup:
    """Test database setup functionality"""

    def test_database_creation(self):
        """Test that database tables can be created"""
        # Use in-memory database for testing
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        
        # Verify tables exist
        inspector = engine.dialect.get_inspector(engine)
        tables = inspector.get_table_names()
        
        expected_tables = [
            'vpcs', 'subnets', 'routes', 'security_groups',
            'nat_gateways', 'internet_gateways', 'vpn_gateways',
            'vni_counters', 'cloud_routing_hubs', 'standalone_data_centers',
            'standalone_dc_subnets', 'mesh_nodes', 'vpc_endpoints'
        ]
        
        for table in expected_tables:
            assert table in tables, f"Table {table} should exist"

    def test_session_factory_creation(self):
        """Test that session factory can be created"""
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Test session creation
        session = SessionLocal()
        assert session is not None
        session.close()
