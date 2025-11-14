"""Database schema validation and migration support for ChromaDB."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

from app.services.vector_database import VectorDatabaseService
from app.core.exceptions import VectorDatabaseError, ValidationError
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class MigrationStatus(str, Enum):
    """Migration status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SchemaVersion(str, Enum):
    """Schema version enumeration."""
    V1_0_0 = "1.0.0"
    V1_1_0 = "1.1.0"
    # Add new versions as needed


class DatabaseMigrationService:
    """Service for database schema validation and migration."""
    
    CURRENT_SCHEMA_VERSION = SchemaVersion.V1_0_0
    
    # Required metadata fields for each schema version
    SCHEMA_REQUIREMENTS = {
        SchemaVersion.V1_0_0: {
            "required_fields": [
                "document_id",
                "chunk_index", 
                "start_index",
                "end_index",
                "content_length",
                "embedding_model",
                "created_at"
            ],
            "optional_fields": [
                "section_title",
                "page_number",
                "language",
                "token_count"
            ],
            "field_types": {
                "document_id": str,
                "chunk_index": int,
                "start_index": int,
                "end_index": int,
                "content_length": int,
                "embedding_model": str,
                "created_at": str,
                "section_title": str,
                "page_number": int,
                "language": str,
                "token_count": int
            }
        }
    }
    
    def __init__(self, vector_db_service: VectorDatabaseService = None):
        """Initialize migration service.
        
        Args:
            vector_db_service: Vector database service instance
        """
        self.vector_db = vector_db_service or VectorDatabaseService()
        self.settings = get_settings()
    
    async def validate_schema(self, target_version: SchemaVersion = None) -> Dict[str, Any]:
        """Validate database schema against target version.
        
        Args:
            target_version: Target schema version to validate against
            
        Returns:
            Validation results dictionary
        """
        target_version = target_version or self.CURRENT_SCHEMA_VERSION
        
        try:
            # Ensure connection
            await self.vector_db._ensure_connected()
            
            # Get basic collection info
            basic_validation = await self.vector_db.validate_schema()
            collection_exists = basic_validation.get("collection_exists", True)  # Assume exists if connected
            
            if not collection_exists:
                return {
                    "collection_exists": False,
                    "schema_version": None,
                    "is_valid": False,
                    "target_version": target_version,
                    "errors": ["Collection does not exist"],
                    "warnings": [],
                    "validation_timestamp": datetime.now().isoformat()
                }
            
            # Get sample data for detailed validation
            sample_data = self.vector_db._collection.get(limit=10)
            
            validation_result = {
                "collection_exists": collection_exists,
                "schema_version": self._detect_schema_version(sample_data),
                "target_version": target_version,
                "is_valid": True,
                "errors": [],
                "warnings": [],
                "field_analysis": {},
                "validation_timestamp": datetime.now().isoformat()
            }
            
            # Validate against target schema requirements
            if sample_data.get("metadatas"):
                validation_result.update(
                    self._validate_metadata_schema(sample_data["metadatas"], target_version)
                )
            else:
                validation_result["warnings"].append("No data available for schema validation")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            return {
                "collection_exists": False,
                "schema_version": None,
                "is_valid": False,
                "target_version": target_version,
                "errors": [f"Validation failed: {str(e)}"],
                "warnings": [],
                "validation_timestamp": datetime.now().isoformat()
            }
    
    async def migrate_schema(
        self, 
        target_version: SchemaVersion,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """Migrate database schema to target version.
        
        Args:
            target_version: Target schema version
            dry_run: If True, only simulate migration without making changes
            
        Returns:
            Migration results dictionary
        """
        try:
            # Validate current schema
            current_validation = await self.validate_schema()
            current_version = current_validation.get("schema_version")
            
            migration_result = {
                "migration_id": f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "from_version": current_version,
                "to_version": target_version,
                "dry_run": dry_run,
                "status": MigrationStatus.PENDING,
                "steps": [],
                "errors": [],
                "warnings": [],
                "started_at": datetime.now().isoformat(),
                "completed_at": None
            }
            
            # Check if migration is needed
            if current_version == target_version:
                migration_result["status"] = MigrationStatus.COMPLETED
                migration_result["warnings"].append("Schema is already at target version")
                migration_result["completed_at"] = datetime.now().isoformat()
                return migration_result
            
            # Plan migration steps
            migration_steps = await self._plan_migration(current_version, target_version)
            migration_result["steps"] = migration_steps
            
            if not dry_run:
                # Execute migration
                migration_result["status"] = MigrationStatus.RUNNING
                await self._execute_migration(migration_steps, migration_result)
                migration_result["status"] = MigrationStatus.COMPLETED
            else:
                migration_result["warnings"].append("Dry run - no changes were made")
            
            migration_result["completed_at"] = datetime.now().isoformat()
            return migration_result
            
        except Exception as e:
            logger.error(f"Schema migration failed: {e}")
            migration_result["status"] = MigrationStatus.FAILED
            migration_result["errors"].append(f"Migration failed: {str(e)}")
            migration_result["completed_at"] = datetime.now().isoformat()
            return migration_result
    
    async def backup_collection(self, backup_name: str = None) -> Dict[str, Any]:
        """Create a backup of the current collection.
        
        Args:
            backup_name: Optional backup name
            
        Returns:
            Backup information dictionary
        """
        try:
            backup_name = backup_name or f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Get all data from collection
            all_data = self.vector_db._collection.get()
            
            backup_info = {
                "backup_name": backup_name,
                "collection_name": self.settings.CHROMA_COLLECTION_NAME,
                "total_chunks": len(all_data.get("ids", [])),
                "created_at": datetime.now().isoformat(),
                "schema_version": self._detect_schema_version(all_data),
                "data": all_data
            }
            
            logger.info(f"Created backup '{backup_name}' with {backup_info['total_chunks']} chunks")
            return backup_info
            
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            raise VectorDatabaseError(f"Backup failed: {str(e)}")
    
    async def restore_collection(self, backup_data: Dict[str, Any]) -> Dict[str, Any]:
        """Restore collection from backup data.
        
        Args:
            backup_data: Backup data dictionary
            
        Returns:
            Restoration results dictionary
        """
        try:
            # Validate backup data
            if not self._validate_backup_data(backup_data):
                raise ValidationError("Invalid backup data format")
            
            # Reset collection
            await self.vector_db.reset_collection()
            
            # Restore data
            data = backup_data["data"]
            if data.get("ids") and data.get("documents") and data.get("embeddings"):
                self.vector_db._collection.add(
                    ids=data["ids"],
                    documents=data["documents"],
                    embeddings=data["embeddings"],
                    metadatas=data.get("metadatas", [])
                )
            
            restore_result = {
                "backup_name": backup_data.get("backup_name", "unknown"),
                "restored_chunks": len(data.get("ids", [])),
                "restored_at": datetime.now().isoformat(),
                "schema_version": backup_data.get("schema_version"),
                "success": True
            }
            
            logger.info(f"Restored {restore_result['restored_chunks']} chunks from backup")
            return restore_result
            
        except Exception as e:
            logger.error(f"Collection restoration failed: {e}")
            raise VectorDatabaseError(f"Restoration failed: {str(e)}")
    
    # Private methods
    
    def _detect_schema_version(self, sample_data: Dict[str, Any]) -> Optional[SchemaVersion]:
        """Detect schema version from sample data.
        
        Args:
            sample_data: Sample data from collection
            
        Returns:
            Detected schema version or None
        """
        if not sample_data.get("metadatas"):
            return None
        
        # Check against known schema versions
        for version, requirements in self.SCHEMA_REQUIREMENTS.items():
            if self._check_version_compatibility(sample_data["metadatas"], requirements):
                return version
        
        return None
    
    def _check_version_compatibility(
        self, 
        metadatas: List[Dict[str, Any]], 
        requirements: Dict[str, Any]
    ) -> bool:
        """Check if metadata is compatible with schema requirements.
        
        Args:
            metadatas: List of metadata dictionaries
            requirements: Schema requirements
            
        Returns:
            True if compatible
        """
        if not metadatas:
            return False
        
        required_fields = requirements["required_fields"]
        sample_metadata = metadatas[0]
        
        # Check if all required fields are present
        return all(field in sample_metadata for field in required_fields)
    
    def _validate_metadata_schema(
        self, 
        metadatas: List[Dict[str, Any]], 
        target_version: SchemaVersion
    ) -> Dict[str, Any]:
        """Validate metadata against target schema version.
        
        Args:
            metadatas: List of metadata dictionaries
            target_version: Target schema version
            
        Returns:
            Validation results
        """
        requirements = self.SCHEMA_REQUIREMENTS.get(target_version, {})
        required_fields = requirements.get("required_fields", [])
        optional_fields = requirements.get("optional_fields", [])
        field_types = requirements.get("field_types", {})
        
        errors = []
        warnings = []
        field_analysis = {}
        
        # Analyze field presence and types
        for field in required_fields + optional_fields:
            field_stats = {
                "present_count": 0,
                "total_count": len(metadatas),
                "type_errors": 0,
                "expected_type": field_types.get(field, "any").__name__ if field in field_types else "any"
            }
            
            for metadata in metadatas:
                if field in metadata:
                    field_stats["present_count"] += 1
                    
                    # Check type if specified
                    if field in field_types:
                        expected_type = field_types[field]
                        if not isinstance(metadata[field], expected_type):
                            field_stats["type_errors"] += 1
            
            field_analysis[field] = field_stats
            
            # Check required fields
            if field in required_fields and field_stats["present_count"] == 0:
                errors.append(f"Required field '{field}' is missing from all records")
            elif field in required_fields and field_stats["present_count"] < len(metadatas):
                warnings.append(f"Required field '{field}' is missing from some records")
            
            # Check type errors
            if field_stats["type_errors"] > 0:
                warnings.append(f"Field '{field}' has type errors in {field_stats['type_errors']} records")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "field_analysis": field_analysis
        }
    
    async def _plan_migration(
        self, 
        from_version: Optional[SchemaVersion], 
        to_version: SchemaVersion
    ) -> List[Dict[str, Any]]:
        """Plan migration steps from source to target version.
        
        Args:
            from_version: Source schema version
            to_version: Target schema version
            
        Returns:
            List of migration steps
        """
        steps = []
        
        if from_version is None:
            # New installation
            steps.append({
                "step": "initialize_schema",
                "description": f"Initialize schema to version {to_version}",
                "type": "schema_creation"
            })
        elif from_version != to_version:
            # Version upgrade/downgrade
            steps.append({
                "step": "backup_current_data",
                "description": "Create backup of current data",
                "type": "backup"
            })
            
            steps.append({
                "step": "update_metadata_schema",
                "description": f"Update metadata schema from {from_version} to {to_version}",
                "type": "schema_update"
            })
            
            steps.append({
                "step": "validate_migrated_data",
                "description": "Validate data after migration",
                "type": "validation"
            })
        
        return steps
    
    async def _execute_migration(
        self, 
        migration_steps: List[Dict[str, Any]], 
        migration_result: Dict[str, Any]
    ) -> None:
        """Execute migration steps.
        
        Args:
            migration_steps: List of migration steps to execute
            migration_result: Migration result dictionary to update
        """
        for step in migration_steps:
            try:
                step_type = step["type"]
                
                if step_type == "backup":
                    backup_info = await self.backup_collection()
                    step["backup_info"] = backup_info
                    
                elif step_type == "schema_creation":
                    # Schema is created automatically when collection is accessed
                    pass
                    
                elif step_type == "schema_update":
                    # For ChromaDB, schema updates typically involve data transformation
                    await self._update_metadata_schema(migration_result["to_version"])
                    
                elif step_type == "validation":
                    validation_result = await self.validate_schema(migration_result["to_version"])
                    if not validation_result["is_valid"]:
                        raise VectorDatabaseError("Post-migration validation failed")
                
                step["status"] = "completed"
                step["completed_at"] = datetime.now().isoformat()
                
            except Exception as e:
                step["status"] = "failed"
                step["error"] = str(e)
                step["completed_at"] = datetime.now().isoformat()
                raise
    
    async def _update_metadata_schema(self, target_version: SchemaVersion) -> None:
        """Update metadata schema to target version.
        
        Args:
            target_version: Target schema version
        """
        # For ChromaDB, this would involve updating existing metadata
        # This is a placeholder for actual schema transformation logic
        logger.info(f"Updating metadata schema to version {target_version}")
        
        # Example: Add missing required fields with default values
        requirements = self.SCHEMA_REQUIREMENTS.get(target_version, {})
        required_fields = requirements.get("required_fields", [])
        
        # In a real implementation, you would:
        # 1. Get all existing data
        # 2. Transform metadata to match new schema
        # 3. Re-insert transformed data
        
        pass
    
    def _validate_backup_data(self, backup_data: Dict[str, Any]) -> bool:
        """Validate backup data format.
        
        Args:
            backup_data: Backup data to validate
            
        Returns:
            True if valid backup data
        """
        required_keys = ["backup_name", "collection_name", "created_at", "data"]
        
        if not all(key in backup_data for key in required_keys):
            return False
        
        data = backup_data["data"]
        if not isinstance(data, dict):
            return False
        
        # Check data structure
        if "ids" in data and "documents" in data:
            ids_count = len(data["ids"])
            docs_count = len(data["documents"])
            
            if ids_count != docs_count:
                return False
            
            if "embeddings" in data and data["embeddings"] is not None and len(data["embeddings"]) != ids_count:
                return False
            
            if "metadatas" in data and data["metadatas"] is not None and len(data["metadatas"]) != ids_count:
                return False
        
        return True


# Factory function
def get_database_migration_service(
    vector_db_service: VectorDatabaseService = None
) -> DatabaseMigrationService:
    """Get database migration service instance.
    
    Args:
        vector_db_service: Optional vector database service instance
        
    Returns:
        DatabaseMigrationService instance
    """
    return DatabaseMigrationService(vector_db_service)