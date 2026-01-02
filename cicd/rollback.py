#!/usr/bin/env python3
"""
Rollback System

Provides automated and manual rollback capabilities:
- Configuration versioning
- One-click rollback to previous state
- Rollback verification
- Audit logging
"""

import os
import json
import hashlib
import shutil
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ConfigVersion:
    """Represents a configuration version."""
    version_id: str
    timestamp: datetime
    description: str
    config_hash: str
    deployed_nodes: List[str]
    created_by: str

@dataclass
class RollbackResult:
    """Result of a rollback operation."""
    success: bool
    from_version: str
    to_version: str
    nodes_rolled_back: List[str]
    nodes_failed: List[str]
    message: str

class ConfigVersionManager:
    """
    Manages configuration versions for rollback.
    
    Features:
    - Version history storage
    - Config diff viewing
    - Rollback to any previous version
    - Audit trail
    """
    
    def __init__(self, storage_path: str = "/app/data/versions"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.versions: List[ConfigVersion] = []
        self._load_versions()
        
    def _load_versions(self):
        """Load version history from storage."""
        index_file = self.storage_path / "index.json"
        if index_file.exists():
            with open(index_file, 'r') as f:
                data = json.load(f)
                self.versions = [
                    ConfigVersion(
                        version_id=v["version_id"],
                        timestamp=datetime.fromisoformat(v["timestamp"]),
                        description=v["description"],
                        config_hash=v["config_hash"],
                        deployed_nodes=v["deployed_nodes"],
                        created_by=v["created_by"]
                    )
                    for v in data.get("versions", [])
                ]
                
    def _save_versions(self):
        """Save version history to storage."""
        index_file = self.storage_path / "index.json"
        with open(index_file, 'w') as f:
            json.dump({
                "versions": [
                    {
                        "version_id": v.version_id,
                        "timestamp": v.timestamp.isoformat(),
                        "description": v.description,
                        "config_hash": v.config_hash,
                        "deployed_nodes": v.deployed_nodes,
                        "created_by": v.created_by
                    }
                    for v in self.versions
                ]
            }, f, indent=2)
            
    def save_version(self, 
                    config: Dict[str, Any],
                    description: str,
                    deployed_nodes: List[str],
                    created_by: str = "controller") -> ConfigVersion:
        """
        Save a new configuration version.
        """
        config_json = json.dumps(config, sort_keys=True)
        config_hash = hashlib.sha256(config_json.encode()).hexdigest()[:12]
        
        version_id = f"v{len(self.versions) + 1}_{config_hash}"
        timestamp = datetime.utcnow()
        
        # Save config file
        config_file = self.storage_path / f"{version_id}.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
            
        version = ConfigVersion(
            version_id=version_id,
            timestamp=timestamp,
            description=description,
            config_hash=config_hash,
            deployed_nodes=deployed_nodes,
            created_by=created_by
        )
        
        self.versions.append(version)
        self._save_versions()
        
        print(f"Saved config version: {version_id}")
        return version
        
    def get_version(self, version_id: str) -> Optional[ConfigVersion]:
        """Get a specific version."""
        for v in self.versions:
            if v.version_id == version_id:
                return v
        return None
        
    def get_version_config(self, version_id: str) -> Optional[Dict[str, Any]]:
        """Get the configuration for a specific version."""
        config_file = self.storage_path / f"{version_id}.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                return json.load(f)
        return None
        
    def list_versions(self, limit: int = 10) -> List[ConfigVersion]:
        """List recent versions."""
        return sorted(self.versions, key=lambda v: v.timestamp, reverse=True)[:limit]
        
    def get_current_version(self) -> Optional[ConfigVersion]:
        """Get the current (latest) version."""
        if self.versions:
            return sorted(self.versions, key=lambda v: v.timestamp)[-1]
        return None


class RollbackManager:
    """
    Manages rollback operations.
    """
    
    def __init__(self, version_manager: ConfigVersionManager):
        self.version_manager = version_manager
        self.audit_log: List[Dict[str, Any]] = []
        
    def rollback_to_version(self, version_id: str) -> RollbackResult:
        """
        Rollback to a specific version.
        """
        current = self.version_manager.get_current_version()
        target = self.version_manager.get_version(version_id)
        
        if not target:
            return RollbackResult(
                success=False,
                from_version=current.version_id if current else "",
                to_version=version_id,
                nodes_rolled_back=[],
                nodes_failed=[],
                message=f"Version {version_id} not found"
            )
            
        target_config = self.version_manager.get_version_config(version_id)
        if not target_config:
            return RollbackResult(
                success=False,
                from_version=current.version_id if current else "",
                to_version=version_id,
                nodes_rolled_back=[],
                nodes_failed=[],
                message=f"Configuration for {version_id} not found"
            )
            
        print(f"Rolling back from {current.version_id if current else 'unknown'} to {version_id}")
        
        # Deploy the old config to all nodes
        nodes_success = []
        nodes_failed = []
        
        for node in target.deployed_nodes:
            if self._deploy_to_node(node, target_config):
                nodes_success.append(node)
            else:
                nodes_failed.append(node)
                
        # Log the rollback
        self._log_rollback(current, target, nodes_success, nodes_failed)
        
        success = len(nodes_failed) == 0
        
        return RollbackResult(
            success=success,
            from_version=current.version_id if current else "",
            to_version=version_id,
            nodes_rolled_back=nodes_success,
            nodes_failed=nodes_failed,
            message="Rollback complete" if success else f"Partial rollback: {len(nodes_failed)} nodes failed"
        )
        
    def rollback_to_previous(self) -> RollbackResult:
        """Rollback to the previous version."""
        versions = self.version_manager.list_versions(2)
        
        if len(versions) < 2:
            return RollbackResult(
                success=False,
                from_version="",
                to_version="",
                nodes_rolled_back=[],
                nodes_failed=[],
                message="No previous version to rollback to"
            )
            
        previous_version = versions[1]  # Second most recent
        return self.rollback_to_version(previous_version.version_id)
        
    def _deploy_to_node(self, node: str, config: Dict[str, Any]) -> bool:
        """Deploy configuration to a node."""
        print(f"  Deploying rollback config to {node}...")
        
        # In production: push config via API/gNMI/SSH
        try:
            # Simulated deployment
            return True
        except Exception as e:
            print(f"  Error: {e}")
            return False
            
    def _log_rollback(self, 
                     from_version: ConfigVersion,
                     to_version: ConfigVersion,
                     nodes_success: List[str],
                     nodes_failed: List[str]):
        """Log rollback for audit trail."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": "rollback",
            "from_version": from_version.version_id if from_version else None,
            "to_version": to_version.version_id,
            "nodes_success": nodes_success,
            "nodes_failed": nodes_failed
        }
        
        self.audit_log.append(log_entry)
        print(f"  Rollback logged: {from_version.version_id if from_version else 'unknown'} -> {to_version.version_id}")
        
    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Get the rollback audit log."""
        return self.audit_log


def main():
    """Demo rollback system."""
    # Initialize
    version_manager = ConfigVersionManager("/tmp/versions")
    rollback_manager = RollbackManager(version_manager)
    
    # Simulate some deployments
    config_v1 = {"bgp": {"timers": {"keepalive": 60, "hold": 180}}}
    config_v2 = {"bgp": {"timers": {"keepalive": 30, "hold": 90}}}
    config_v3 = {"bgp": {"timers": {"keepalive": 10, "hold": 30}}}  # Aggressive - might cause issues
    
    version_manager.save_version(config_v1, "Initial config", ["leaf-1", "leaf-2", "leaf-3"], "admin")
    version_manager.save_version(config_v2, "Reduced BGP timers", ["leaf-1", "leaf-2", "leaf-3"], "admin")
    version_manager.save_version(config_v3, "Aggressive timers", ["leaf-1", "leaf-2", "leaf-3"], "admin")
    
    print("\nCurrent versions:")
    for v in version_manager.list_versions():
        print(f"  {v.version_id}: {v.description} ({v.timestamp})")
        
    # Rollback to previous
    print("\nRolling back to previous version...")
    result = rollback_manager.rollback_to_previous()
    
    print(f"\nRollback result:")
    print(f"  Success: {result.success}")
    print(f"  From: {result.from_version}")
    print(f"  To: {result.to_version}")
    print(f"  Message: {result.message}")


if __name__ == "__main__":
    main()
