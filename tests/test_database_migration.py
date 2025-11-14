"""Unit tests for database migration service."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from app.services.database_migration import (
    DatabaseMigrationService, 
    SchemaVersion, 
    MigrationStatus,
    get_database_migration_service
)
from app.services.vector_database import VectorDatabaseService
from app.core.exceptions import VectorDatabaseError, ValidationError


@pytest.fixture
def mock_vector_db():
    """Create mock vector database service."""
    mock_db = Mock(spec=VectorDatabaseService)
    mock_db._ensure_connected = AsyncMock()
    mock_db.validate_schema = AsyncMock()
    mock_db.reset_collection = AsyncMock()
    mock_db._collection = Mock()
    return mock_db


@pytest.fixture
def migration_service(mock_vector_db):
    """Create migration service with mock vector database."""
    return DatabaseMigrationService(mock_vector_db)


@pytest.fixture
def sample_metadata():
    """Create sample metadata for testing."""
    return [
        {
            "document_id": "doc1",
            "chunk_index": 0,
            "start_index": 0,
            "end_index": 100,
            "content_length": 100,
            "embedding_model": "test-model",
            "created_at": "2023-01-01T00:00:00",
            "section_title": "Introduction",
            "page_number": 1,
            "language": "en",
            "token_count": 25
        },
        {
            "document_id": "doc2",
            "chunk_index": 1,
            "start_index": 100,
            "end_index": 200,
            "content_length": 100,
            "embedding_model": "test-model",
            "created_at": "2023-01-01T00:01:00",
            "section_title": "Chapter 1",
            "page_number": 2,
            "language": "en",
            "token_count": 30
        }
    ]


class TestDatabaseMigrationService:
    """Test cases for DatabaseMigrationService."""
    
    @pytest.mark.asyncio
    async def test_validate_schema_success(self, migration_service, mock_vector_db, sample_metadata):
        """Test successful schema validation."""
        # Mock vector database responses
        mock_vector_db.validate_schema.return_value = {
            "collection_exists": True,
            "schema_valid": True
        }
        
        mock_vector_db._collection.get.return_value = {
            "metadatas": sample_metadata
        }
        
        result = await migration_service.validate_schema()
        
        assert result["is_valid"] is True
        assert result["schema_version"] == SchemaVersion.V1_0_0
        assert result["target_version"] == SchemaVersion.V1_0_0
        assert len(result["errors"]) == 0
        assert "validation_timestamp" in result
    
    @pytest.mark.asyncio
    async def test_validate_schema_collection_not_exists(self, migration_service, mock_vector_db):
        """Test schema validation when collection doesn't exist."""
        mock_vector_db.validate_schema.return_value = {
            "collection_exists": False
        }
        
        result = await migration_service.validate_schema()
        
        assert result["is_valid"] is False
        assert result["schema_version"] is None
        assert "Collection does not exist" in result["errors"]
    
    @pytest.mark.asyncio
    async def test_validate_schema_no_data(self, migration_service, mock_vector_db):
        """Test schema validation with no data."""
        mock_vector_db.validate_schema.return_value = {
            "collection_exists": True,
            "schema_valid": True
        }
        
        mock_vector_db._collection.get.return_value = {
            "metadatas": []
        }
        
        result = await migration_service.validate_schema()
        
        assert result["is_valid"] is True
        assert "No data available for schema validation" in result["warnings"]
    
    @pytest.mark.asyncio
    async def test_validate_schema_missing_required_fields(self, migration_service, mock_vector_db):
        """Test schema validation with missing required fields."""
        incomplete_metadata = [
            {
                "document_id": "doc1",
                "chunk_index": 0,
                # Missing required fields: start_index, end_index, etc.
            }
        ]
        
        mock_vector_db.validate_schema.return_value = {
            "collection_exists": True,
            "schema_valid": True
        }
        
        mock_vector_db._collection.get.return_value = {
            "metadatas": incomplete_metadata
        }
        
        result = await migration_service.validate_schema()
        
        assert result["is_valid"] is False
        assert len(result["errors"]) > 0
        assert any("missing from all records" in error for error in result["errors"])
    
    @pytest.mark.asyncio
    async def test_validate_schema_type_errors(self, migration_service, mock_vector_db):
        """Test schema validation with type errors."""
        invalid_metadata = [
            {
                "document_id": "doc1",
                "chunk_index": "not_an_integer",  # Should be int
                "start_index": 0,
                "end_index": 100,
                "content_length": 100,
                "embedding_model": "test-model",
                "created_at": "2023-01-01T00:00:00"
            }
        ]
        
        mock_vector_db.validate_schema.return_value = {
            "collection_exists": True,
            "schema_valid": True
        }
        
        mock_vector_db._collection.get.return_value = {
            "metadatas": invalid_metadata
        }
        
        result = await migration_service.validate_schema()
        
        assert "chunk_index" in result["field_analysis"]
        assert result["field_analysis"]["chunk_index"]["type_errors"] > 0
        assert any("type errors" in warning for warning in result["warnings"])
    
    @pytest.mark.asyncio
    async def test_migrate_schema_same_version(self, migration_service, mock_vector_db, sample_metadata):
        """Test migration when already at target version."""
        mock_vector_db.validate_schema.return_value = {
            "collection_exists": True,
            "schema_valid": True
        }
        
        mock_vector_db._collection.get.return_value = {
            "metadatas": sample_metadata
        }
        
        result = await migration_service.migrate_schema(SchemaVersion.V1_0_0, dry_run=False)
        
        assert result["status"] == MigrationStatus.COMPLETED
        assert result["from_version"] == SchemaVersion.V1_0_0
        assert result["to_version"] == SchemaVersion.V1_0_0
        assert "already at target version" in result["warnings"][0]
    
    @pytest.mark.asyncio
    async def test_migrate_schema_dry_run(self, migration_service, mock_vector_db):
        """Test migration in dry run mode."""
        mock_vector_db.validate_schema.return_value = {
            "collection_exists": True,
            "schema_valid": True
        }
        
        mock_vector_db._collection.get.return_value = {
            "metadatas": []
        }
        
        result = await migration_service.migrate_schema(SchemaVersion.V1_0_0, dry_run=True)
        
        assert result["dry_run"] is True
        assert result["status"] == MigrationStatus.COMPLETED
        assert "Dry run - no changes were made" in result["warnings"]
    
    @pytest.mark.asyncio
    async def test_migrate_schema_new_installation(self, migration_service, mock_vector_db):
        """Test migration for new installation (no existing schema)."""
        mock_vector_db.validate_schema.return_value = {
            "collection_exists": True,
            "schema_valid": True
        }
        
        mock_vector_db._collection.get.return_value = {
            "metadatas": []
        }
        
        # Mock _detect_schema_version to return None (new installation)
        with patch.object(migration_service, '_detect_schema_version', return_value=None):
            result = await migration_service.migrate_schema(SchemaVersion.V1_0_0, dry_run=True)
        
        assert result["from_version"] is None
        assert result["to_version"] == SchemaVersion.V1_0_0
        assert any(step["step"] == "initialize_schema" for step in result["steps"])
    
    @pytest.mark.asyncio
    async def test_backup_collection_success(self, migration_service, mock_vector_db):
        """Test successful collection backup."""
        sample_data = {
            "ids": ["id1", "id2"],
            "documents": ["doc1", "doc2"],
            "embeddings": [[0.1, 0.2], [0.3, 0.4]],
            "metadatas": [{"doc_id": "1"}, {"doc_id": "2"}]
        }
        
        mock_vector_db._collection.get.return_value = sample_data
        
        with patch.object(migration_service, '_detect_schema_version', return_value=SchemaVersion.V1_0_0):
            backup_info = await migration_service.backup_collection("test_backup")
        
        assert backup_info["backup_name"] == "test_backup"
        assert backup_info["total_chunks"] == 2
        assert backup_info["schema_version"] == SchemaVersion.V1_0_0
        assert backup_info["data"] == sample_data
    
    @pytest.mark.asyncio
    async def test_backup_collection_auto_name(self, migration_service, mock_vector_db):
        """Test backup with auto-generated name."""
        mock_vector_db._collection.get.return_value = {"ids": []}
        
        with patch.object(migration_service, '_detect_schema_version', return_value=None):
            backup_info = await migration_service.backup_collection()
        
        assert backup_info["backup_name"].startswith("backup_")
        assert "created_at" in backup_info
    
    @pytest.mark.asyncio
    async def test_restore_collection_success(self, migration_service, mock_vector_db):
        """Test successful collection restoration."""
        backup_data = {
            "backup_name": "test_backup",
            "collection_name": "test_collection",
            "total_chunks": 2,
            "created_at": "2023-01-01T00:00:00",
            "schema_version": SchemaVersion.V1_0_0,
            "data": {
                "ids": ["id1", "id2"],
                "documents": ["doc1", "doc2"],
                "embeddings": [[0.1, 0.2], [0.3, 0.4]],
                "metadatas": [{"doc_id": "1"}, {"doc_id": "2"}]
            }
        }
        
        result = await migration_service.restore_collection(backup_data)
        
        assert result["success"] is True
        assert result["backup_name"] == "test_backup"
        assert result["restored_chunks"] == 2
        assert result["schema_version"] == SchemaVersion.V1_0_0
        
        # Verify reset and add were called
        mock_vector_db.reset_collection.assert_called_once()
        mock_vector_db._collection.add.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_restore_collection_invalid_backup(self, migration_service, mock_vector_db):
        """Test restoration with invalid backup data."""
        invalid_backup = {
            "backup_name": "test",
            # Missing required fields
        }
        
        with pytest.raises(ValidationError, match="Invalid backup data format"):
            await migration_service.restore_collection(invalid_backup)
    
    def test_detect_schema_version_v1_0_0(self, migration_service, sample_metadata):
        """Test schema version detection for v1.0.0."""
        sample_data = {"metadatas": sample_metadata}
        
        version = migration_service._detect_schema_version(sample_data)
        
        assert version == SchemaVersion.V1_0_0
    
    def test_detect_schema_version_no_data(self, migration_service):
        """Test schema version detection with no data."""
        sample_data = {"metadatas": []}
        
        version = migration_service._detect_schema_version(sample_data)
        
        assert version is None
    
    def test_detect_schema_version_incompatible(self, migration_service):
        """Test schema version detection with incompatible data."""
        incompatible_metadata = [
            {
                "old_field": "value",
                # Missing all required fields
            }
        ]
        sample_data = {"metadatas": incompatible_metadata}
        
        version = migration_service._detect_schema_version(sample_data)
        
        assert version is None
    
    def test_check_version_compatibility_compatible(self, migration_service, sample_metadata):
        """Test version compatibility check with compatible data."""
        requirements = migration_service.SCHEMA_REQUIREMENTS[SchemaVersion.V1_0_0]
        
        is_compatible = migration_service._check_version_compatibility(sample_metadata, requirements)
        
        assert is_compatible is True
    
    def test_check_version_compatibility_incompatible(self, migration_service):
        """Test version compatibility check with incompatible data."""
        incompatible_metadata = [{"some_field": "value"}]
        requirements = migration_service.SCHEMA_REQUIREMENTS[SchemaVersion.V1_0_0]
        
        is_compatible = migration_service._check_version_compatibility(incompatible_metadata, requirements)
        
        assert is_compatible is False
    
    def test_validate_backup_data_valid(self, migration_service):
        """Test backup data validation with valid data."""
        valid_backup = {
            "backup_name": "test",
            "collection_name": "test_collection",
            "created_at": "2023-01-01T00:00:00",
            "data": {
                "ids": ["id1", "id2"],
                "documents": ["doc1", "doc2"],
                "embeddings": [[0.1], [0.2]],
                "metadatas": [{"key": "val1"}, {"key": "val2"}]
            }
        }
        
        is_valid = migration_service._validate_backup_data(valid_backup)
        
        assert is_valid is True
    
    def test_validate_backup_data_missing_keys(self, migration_service):
        """Test backup data validation with missing required keys."""
        invalid_backup = {
            "backup_name": "test",
            # Missing required keys
        }
        
        is_valid = migration_service._validate_backup_data(invalid_backup)
        
        assert is_valid is False
    
    def test_validate_backup_data_mismatched_lengths(self, migration_service):
        """Test backup data validation with mismatched array lengths."""
        invalid_backup = {
            "backup_name": "test",
            "collection_name": "test_collection",
            "created_at": "2023-01-01T00:00:00",
            "data": {
                "ids": ["id1", "id2"],
                "documents": ["doc1"],  # Mismatched length
                "embeddings": [[0.1], [0.2]]
            }
        }
        
        is_valid = migration_service._validate_backup_data(invalid_backup)
        
        assert is_valid is False
    
    @pytest.mark.asyncio
    async def test_plan_migration_new_installation(self, migration_service):
        """Test migration planning for new installation."""
        steps = await migration_service._plan_migration(None, SchemaVersion.V1_0_0)
        
        assert len(steps) == 1
        assert steps[0]["step"] == "initialize_schema"
        assert steps[0]["type"] == "schema_creation"
    
    @pytest.mark.asyncio
    async def test_plan_migration_version_upgrade(self, migration_service):
        """Test migration planning for version upgrade."""
        # This would be used when we have multiple schema versions
        steps = await migration_service._plan_migration(SchemaVersion.V1_0_0, SchemaVersion.V1_0_0)
        
        # For same version, no steps needed (handled in migrate_schema)
        assert isinstance(steps, list)
    
    @pytest.mark.asyncio
    async def test_execute_migration_backup_step(self, migration_service, mock_vector_db):
        """Test execution of backup migration step."""
        migration_steps = [
            {
                "step": "backup_current_data",
                "type": "backup",
                "description": "Create backup"
            }
        ]
        
        migration_result = {
            "to_version": SchemaVersion.V1_0_0
        }
        
        mock_vector_db._collection.get.return_value = {"ids": []}
        
        with patch.object(migration_service, '_detect_schema_version', return_value=SchemaVersion.V1_0_0):
            await migration_service._execute_migration(migration_steps, migration_result)
        
        assert migration_steps[0]["status"] == "completed"
        assert "backup_info" in migration_steps[0]
    
    @pytest.mark.asyncio
    async def test_execute_migration_validation_failure(self, migration_service, mock_vector_db):
        """Test migration execution with validation failure."""
        migration_steps = [
            {
                "step": "validate_migrated_data",
                "type": "validation",
                "description": "Validate data"
            }
        ]
        
        migration_result = {
            "to_version": SchemaVersion.V1_0_0
        }
        
        # Mock validation to fail
        with patch.object(migration_service, 'validate_schema', return_value={"is_valid": False}):
            with pytest.raises(VectorDatabaseError, match="Post-migration validation failed"):
                await migration_service._execute_migration(migration_steps, migration_result)


def test_get_database_migration_service():
    """Test factory function for database migration service."""
    service = get_database_migration_service()
    
    assert isinstance(service, DatabaseMigrationService)
    assert service.vector_db is not None


def test_get_database_migration_service_with_vector_db():
    """Test factory function with provided vector database service."""
    mock_vector_db = Mock(spec=VectorDatabaseService)
    service = get_database_migration_service(mock_vector_db)
    
    assert isinstance(service, DatabaseMigrationService)
    assert service.vector_db is mock_vector_db


class TestSchemaVersionEnum:
    """Test schema version enumeration."""
    
    def test_schema_version_values(self):
        """Test schema version enum values."""
        assert SchemaVersion.V1_0_0 == "1.0.0"
        assert SchemaVersion.V1_1_0 == "1.1.0"
    
    def test_current_schema_version(self):
        """Test current schema version is set correctly."""
        assert DatabaseMigrationService.CURRENT_SCHEMA_VERSION == SchemaVersion.V1_0_0


class TestMigrationStatusEnum:
    """Test migration status enumeration."""
    
    def test_migration_status_values(self):
        """Test migration status enum values."""
        assert MigrationStatus.PENDING == "pending"
        assert MigrationStatus.RUNNING == "running"
        assert MigrationStatus.COMPLETED == "completed"
        assert MigrationStatus.FAILED == "failed"