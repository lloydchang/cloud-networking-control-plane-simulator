#!/usr/bin/env python3
"""
Diagnostic Logger for Cloud Networking Control Plane Simulator

This module provides comprehensive diagnostic logging to help identify and troubleshoot
common issues in the control plane simulator.
"""

import logging
import traceback
import sys
import os
from datetime import datetime
from typing import Optional, Dict, Any
import json

# Configure diagnostic logging
handlers = [logging.StreamHandler(sys.stdout)]

# Only add file handler if not in test environment
if not os.getenv("VERCEL"):
    # Ensure directory exists
    log_dir = '/app/data'
    os.makedirs(log_dir, exist_ok=True)
    handlers.append(logging.FileHandler(f'{log_dir}/diagnostic.log'))

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers
)

logger = logging.getLogger("diagnostic")

class DiagnosticLogger:
    """Centralized diagnostic logging for the control plane."""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.errors = []
        self.warnings = []
        
    def log_system_info(self):
        """Log system information for debugging."""
        try:
            import platform
            import psutil
            
            logger.info("=" * 60)
            logger.info("SYSTEM DIAGNOSTICS")
            logger.info("=" * 60)
            logger.info(f"Platform: {platform.platform()}")
            logger.info(f"Python Version: {sys.version}")
            logger.info(f"Working Directory: {os.getcwd()}")
            logger.info(f"Python Path: {sys.path[:3]}...")
            logger.info(f"Environment Variables: {[k for k in os.environ.keys() if 'CONTROL' in k or 'DB' in k or 'API' in k]}")
            
            # Check available memory
            memory = psutil.virtual_memory()
            logger.info(f"Memory - Total: {memory.total / 1024**3:.2f}GB, Available: {memory.available / 1024**3:.2f}GB")
            
            # Check disk space
            disk = psutil.disk_usage('/')
            logger.info(f"Disk - Total: {disk.total / 1024**3:.2f}GB, Free: {disk.free / 1024**3:.2f}GB")
            
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Failed to log system info: {e}")
    
    def log_database_status(self, db_path: str = "/app/data/network.db"):
        """Log database connectivity and schema status."""
        try:
            import sqlite3
            
            logger.info("DATABASE DIAGNOSTICS")
            logger.info("-" * 30)
            logger.info(f"Database Path: {db_path}")
            logger.info(f"Database Exists: {os.path.exists(db_path)}")
            
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Check tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                logger.info(f"Tables: {[t[0] for t in tables]}")
                
                # Check table counts
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table[0]};")
                    count = cursor.fetchone()[0]
                    logger.info(f"Table {table[0]}: {count} records")
                
                conn.close()
            else:
                logger.warning("Database file does not exist yet")
                
        except Exception as e:
            logger.error(f"Database diagnostic failed: {e}")
            logger.error(traceback.format_exc())
    
    def log_docker_status(self):
        """Log Docker connectivity and container status."""
        try:
            import docker
            
            logger.info("DOCKER DIAGNOSTICS")
            logger.info("-" * 20)
            
            client = docker.from_env()
            logger.info("Docker client connected successfully")
            
            # List containers
            containers = client.containers.list(all=True)
            logger.info(f"Total containers: {len(containers)}")
            
            for container in containers:
                status = f"{container.name} ({container.status})"
                logger.info(f"  - {status}")
                
                # Check if it's a control plane related container
                if any(keyword in container.name.lower() for keyword in ['control-plane', 'leaf', 'spine']):
                    try:
                        logs = container.logs(tail=5).decode('utf-8')
                        if logs.strip():
                            logger.info(f"    Last 5 lines of logs for {container.name}:")
                            for line in logs.strip().split('\n'):
                                logger.info(f"      {line}")
                    except Exception as e:
                        logger.warning(f"Could not get logs for {container.name}: {e}")
                        
        except Exception as e:
            logger.error(f"Docker diagnostic failed: {e}")
            logger.error(traceback.format_exc())
    
    def log_api_status(self):
        """Log API service status."""
        try:
            import requests
            
            logger.info("API DIAGNOSTICS")
            logger.info("-" * 15)
            
            # Test REST API
            try:
                response = requests.get("http://localhost:8000/health", timeout=5)
                logger.info(f"REST API Health: {response.status_code} - {response.text}")
            except Exception as e:
                logger.error(f"REST API Health Check Failed: {e}")
            
            # Test gRPC API
            try:
                import grpc
                channel = grpc.insecure_channel('localhost:50051')
                grpc.channel_ready_future(channel).result(timeout=5)
                logger.info("gRPC API: Connected successfully")
                channel.close()
            except Exception as e:
                logger.error(f"gRPC API Connection Failed: {e}")
                
        except ImportError:
            logger.warning("requests or grpc not available for API testing")
        except Exception as e:
            logger.error(f"API diagnostic failed: {e}")
    
    def log_error(self, error_msg: str, context: Optional[Dict[str, Any]] = None):
        """Log an error with context."""
        self.errors.append({
            'timestamp': datetime.now().isoformat(),
            'error': error_msg,
            'context': context or {}
        })
        logger.error(f"ERROR: {error_msg}")
        if context:
            logger.error(f"Context: {json.dumps(context, indent=2)}")
    
    def log_warning(self, warning_msg: str, context: Optional[Dict[str, Any]] = None):
        """Log a warning with context."""
        self.warnings.append({
            'timestamp': datetime.now().isoformat(),
            'warning': warning_msg,
            'context': context or {}
        })
        logger.warning(f"WARNING: {warning_msg}")
        if context:
            logger.warning(f"Context: {json.dumps(context, indent=2)}")
    
    def log_success(self, success_msg: str):
        """Log a success message."""
        logger.info(f"SUCCESS: {success_msg}")
    
    def generate_report(self):
        """Generate a diagnostic report."""
        report = {
            'start_time': self.start_time.isoformat(),
            'end_time': datetime.now().isoformat(),
            'errors': self.errors,
            'warnings': self.warnings,
            'total_errors': len(self.errors),
            'total_warnings': len(self.warnings)
        }
        
        # Save report to file
        report_path = "/app/data/diagnostic_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info("=" * 60)
        logger.info("DIAGNOSTIC REPORT SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total Errors: {len(self.errors)}")
        logger.info(f"Total Warnings: {len(self.warnings)}")
        logger.info(f"Report saved to: {report_path}")
        logger.info("=" * 60)
        
        return report

# Global diagnostic logger instance
diagnostic_logger = DiagnosticLogger()

def run_full_diagnostic():
    """Run a complete diagnostic check."""
    logger.info("Starting full diagnostic check...")
    
    diagnostic_logger.log_system_info()
    diagnostic_logger.log_database_status()
    diagnostic_logger.log_docker_status()
    diagnostic_logger.log_api_status()
    
    return diagnostic_logger.generate_report()

if __name__ == "__main__":
    run_full_diagnostic()