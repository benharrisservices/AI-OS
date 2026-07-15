"""Production knowledge ingestion: embeddings, paths, authenticated upload."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from ai_os.api.app import app
from ai_os.api.startup import apply_data_dir_defaults
from ai_os.knowledge.config import KnowledgeSettings
from ai_os.knowledge.embedding import DimensionMismatchError, EmbeddingService


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestEmbeddingProvider:
    def test_ollama_available_locally(self, tmp_path: Path) -> None:
        settings = KnowledgeSettings(
            knowledge_index_dir=tmp_path / "index",
            embedding_provider="ollama",
            embedding_model="nomic-embed-text",
            embedding_dimensions=768,
        )
        service = EmbeddingService(settings)

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/api/version"):
                return httpx.Response(200, json={"version": "0.1"})
            if request.url.path.endswith("/api/embed"):
                return httpx.Response(
                    200, json={"embeddings": [[0.1] * 768, [0.2] * 768]}
                )
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        with patch("ai_os.knowledge.embedding.httpx.Client") as client_cls:
            client_cls.return_value.__enter__.return_value = httpx.Client(
                transport=transport
            )
            # Directly stub Client usage in _ensure_provider and _embed_ollama
            with patch.object(service, "_embed_ollama", return_value=[[0.1] * 768]):
                with patch.object(service, "_ensure_provider") as ensure:
                    ensure.side_effect = lambda: setattr(service, "_provider_resolved", True) or setattr(
                        service, "_use_openai", False
                    ) or setattr(service, "_index_checked", True)
                    vectors = service.embed_texts(["hello"])
        assert len(vectors[0]) == 768
        assert service.active_provider == "ollama"

    def test_ollama_unavailable_openai_fallback(self, tmp_path: Path) -> None:
        settings = KnowledgeSettings(
            knowledge_index_dir=tmp_path / "index",
            embedding_provider="ollama",
            openai_embedding_model="text-embedding-3-small",
            openai_embedding_dimensions=1536,
        )
        service = EmbeddingService(settings)
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            with patch.object(service, "_assert_index_compatible"):
                with patch("ai_os.knowledge.embedding.httpx.Client") as client_cls:
                    mock_client = MagicMock()
                    mock_client.get.side_effect = httpx.ConnectError("refused")
                    mock_resp = MagicMock()
                    mock_resp.raise_for_status = MagicMock()
                    mock_resp.json.return_value = {
                        "data": [{"index": 0, "embedding": [0.5] * 1536}]
                    }
                    mock_client.post.return_value = mock_resp
                    client_cls.return_value.__enter__.return_value = mock_client
                    vectors = service.embed_texts(["hello"])
                    assert service.active_provider == "openai"
                    assert service.active_model == "text-embedding-3-small"
                    assert len(vectors[0]) == 1536

    def test_openai_failure_raises(self, tmp_path: Path) -> None:
        settings = KnowledgeSettings(
            knowledge_index_dir=tmp_path / "index",
            embedding_provider="openai",
            openai_embedding_dimensions=1536,
        )
        service = EmbeddingService(settings)
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OPENAI_API_KEY", None)
            with patch.object(service, "_assert_index_compatible"):
                with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
                    service.embed_texts(["hello"])

    def test_cache_keys_include_provider_model_dims(self, tmp_path: Path) -> None:
        settings = KnowledgeSettings(
            knowledge_index_dir=tmp_path / "index",
            embedding_provider="openai",
            openai_embedding_model="text-embedding-3-small",
            openai_embedding_dimensions=1536,
        )
        service = EmbeddingService(settings)
        with patch.object(service, "_assert_index_compatible"):
            service._ensure_provider()
            key_a = service._cache_key("abc")
            service.settings.openai_embedding_dimensions = 512  # type: ignore[misc]
            # Force re-read of expected dims via property after mutation
            object.__setattr__(service.settings, "openai_embedding_dimensions", 512)
            key_b = service._cache_key("abc")
        assert key_a != key_b

    def test_dimension_mismatch_raises(self, tmp_path: Path) -> None:
        settings = KnowledgeSettings(
            knowledge_index_dir=tmp_path / "index",
            vector_store_path=tmp_path / "vectors",
            embedding_provider="openai",
            embedding_dimensions=768,
            openai_embedding_dimensions=1536,
        )
        settings.ensure_dirs()
        service = EmbeddingService(settings)
        service._provider_resolved = True
        service._use_openai = True
        service._index_checked = False

        fake_manifest = MagicMock(embedding_dimensions=768)
        with patch(
            "ai_os.knowledge.index.vector.VectorIndex"
        ) as vector_cls:
            vector_cls.return_value.count.return_value = 5
            with patch(
                "ai_os.knowledge.index.manifest.ManifestService"
            ) as manifest_cls:
                manifest_cls.return_value.load.return_value = fake_manifest
                with pytest.raises(DimensionMismatchError, match="reindex"):
                    service._assert_index_compatible()


class TestPersistentPaths:
    def test_production_absolute_data_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        data = tmp_path / "data"
        data.mkdir()
        monkeypatch.setenv("AI_OS_DATA_DIR", str(data))
        settings = KnowledgeSettings(
            ai_os_data_dir=data,
            knowledge_raw_dir=Path("./knowledge/raw"),
            knowledge_processed_dir=Path("./knowledge/processed"),
            knowledge_index_dir=Path("./knowledge/index"),
            vector_store_path=Path("./knowledge/index/vectors"),
            knowledge_watch_dir=Path("./knowledge/raw/inbox"),
            knowledge_backup_dir=Path("./knowledge/backups"),
        )
        assert settings.knowledge_raw_dir == data / "knowledge" / "raw"
        assert settings.vector_store_path == data / "knowledge" / "index" / "vectors"
        assert str(settings.knowledge_raw_dir).startswith(str(data))

    def test_local_relative_paths_unchanged(self, monkeypatch: pytest.MonkeyPatch) -> None:
        settings = KnowledgeSettings(
            ai_os_data_dir=None,
            knowledge_raw_dir=Path("./knowledge/raw"),
            vector_store_path=Path("./knowledge/index/vectors"),
        )
        assert settings.knowledge_raw_dir == Path("./knowledge/raw")
        assert not settings.knowledge_raw_dir.is_absolute()

    def test_startup_defaults_include_agent_outputs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        data = tmp_path / "data"
        monkeypatch.setenv("AI_OS_DATA_DIR", str(data))
        for key in (
            "KNOWLEDGE_RAW_DIR",
            "MEMORY_WORKING_DIR",
            "AGENT_TASKS_DIR",
            "AGENT_LOGS_DIR",
        ):
            monkeypatch.delenv(key, raising=False)
        apply_data_dir_defaults()
        assert os.environ["AGENT_TASKS_DIR"] == f"{data}/memory/agent/tasks"
        assert os.environ["AGENT_LOGS_DIR"] == f"{data}/memory/agent/logs"
        assert os.environ["KNOWLEDGE_RAW_DIR"] == f"{data}/knowledge/raw"


class TestUploadAuth:
    def test_unauthenticated_upload_rejected(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AI_OS_API_KEY", "secret-test-key")
        response = client.post(
            "/api/v1/imports/upload",
            data={"preset_id": "personal-documents"},
            files=[("files", ("note.md", b"# hi", "text/markdown"))],
        )
        assert response.status_code == 401

    def test_authenticated_upload_accepted(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("AI_OS_API_KEY", "secret-test-key")
        monkeypatch.setenv("AI_OS_DATA_DIR", str(tmp_path / "data"))
        for key in (
            "KNOWLEDGE_RAW_DIR",
            "KNOWLEDGE_PROCESSED_DIR",
            "KNOWLEDGE_INDEX_DIR",
            "VECTOR_STORE_PATH",
        ):
            monkeypatch.delenv(key, raising=False)

        from ai_os.knowledge.populate import ImportProgress

        fake = ImportProgress()
        fake.total = 1
        fake.processed = 1
        fake.ingested = 1

        with patch(
            "ai_os.api.routers.imports.KnowledgeImporter.import_path",
            return_value=fake,
        ):
            with patch(
                "ai_os.knowledge.maintenance.MaintenanceService.ensure_search_indexes"
            ):
                with patch(
                    "ai_os.knowledge.health.HealthService"
                ) as health_cls:
                    health_cls.return_value.report.return_value = MagicMock(
                        document_count=1, chunk_count=3
                    )
                    with patch(
                        "ai_os.api.routers.imports.validate_import",
                        return_value=MagicMock(
                            ready=True,
                            errors=[],
                            new_files=1,
                            duplicate_files=0,
                        ),
                    ):
                        with patch(
                            "ai_os.knowledge.config.get_settings",
                            return_value=KnowledgeSettings(
                                ai_os_data_dir=tmp_path / "data",
                                knowledge_raw_dir=tmp_path / "data" / "knowledge" / "raw",
                                knowledge_processed_dir=tmp_path / "data" / "knowledge" / "processed",
                                knowledge_index_dir=tmp_path / "data" / "knowledge" / "index",
                                vector_store_path=tmp_path / "data" / "knowledge" / "index" / "vectors",
                            ),
                        ):
                            response = client.post(
                                "/api/v1/imports/upload",
                                headers={"X-API-Key": "secret-test-key"},
                                data={"preset_id": "personal-documents"},
                                files=[("files", ("note.md", b"# hello sedr", "text/markdown"))],
                            )
        assert response.status_code == 200
        body = response.json()
        assert body["saved_files"] == 1
        assert body["ingested"] == 1

    def test_unsupported_type_rejected(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("AI_OS_API_KEY", "secret-test-key")
        monkeypatch.setenv("AI_OS_DATA_DIR", str(tmp_path / "data"))
        response = client.post(
            "/api/v1/imports/upload",
            headers={"X-API-Key": "secret-test-key"},
            data={"preset_id": "personal-documents"},
            files=[("files", ("malware.exe", b"MZ", "application/octet-stream"))],
        )
        assert response.status_code == 400

    def test_oversized_file_rejected(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("AI_OS_API_KEY", "secret-test-key")
        monkeypatch.setenv("AI_OS_DATA_DIR", str(tmp_path / "data"))
        big = b"x" * (21 * 1024 * 1024)
        response = client.post(
            "/api/v1/imports/upload",
            headers={"X-API-Key": "secret-test-key"},
            data={"preset_id": "personal-documents"},
            files=[("files", ("big.md", big, "text/markdown"))],
        )
        assert response.status_code == 400

    def test_path_traversal_rejected(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        from ai_os.api.routers.imports import _safe_filename

        # Client-supplied directory components are stripped; result stays basename-only.
        name = _safe_filename("../../etc/passwd.md")
        assert name.endswith(".md")
        assert ".." not in name
        assert "/" not in name
        assert "\\" not in name

        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            _safe_filename("")
        with pytest.raises(HTTPException):
            _safe_filename("../secret.exe")

    def test_health_remains_public(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AI_OS_API_KEY", "secret-test-key")
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_dashboard_remains_available(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AI_OS_API_KEY", "secret-test-key")
        response = client.get("/api/v1/dashboard")
        assert response.status_code == 200

    def test_upload_calls_existing_importer(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("AI_OS_API_KEY", "k")
        monkeypatch.setenv("AI_OS_DATA_DIR", str(tmp_path / "data"))
        for key in ("KNOWLEDGE_RAW_DIR", "KNOWLEDGE_PROCESSED_DIR", "KNOWLEDGE_INDEX_DIR", "VECTOR_STORE_PATH"):
            monkeypatch.delenv(key, raising=False)

        from ai_os.knowledge.populate import ImportProgress

        fake = ImportProgress()
        fake.ingested = 1
        fake.total = 1
        fake.processed = 1

        with patch(
            "ai_os.api.routers.imports.KnowledgeImporter.import_path",
            return_value=fake,
        ) as import_mock:
            with patch("ai_os.knowledge.maintenance.MaintenanceService.ensure_search_indexes"):
                with patch("ai_os.knowledge.health.HealthService") as health_cls:
                    health_cls.return_value.report.return_value = MagicMock(
                        document_count=2, chunk_count=4
                    )
                    with patch(
                        "ai_os.api.routers.imports.validate_import",
                        return_value=MagicMock(
                            ready=True, errors=[], new_files=1, duplicate_files=0
                        ),
                    ):
                        with patch(
                            "ai_os.knowledge.config.get_settings",
                            return_value=KnowledgeSettings(
                                ai_os_data_dir=tmp_path / "data",
                                knowledge_raw_dir=tmp_path / "data" / "knowledge" / "raw",
                                knowledge_processed_dir=tmp_path / "data" / "knowledge" / "processed",
                                knowledge_index_dir=tmp_path / "data" / "knowledge" / "index",
                                vector_store_path=tmp_path / "data" / "knowledge" / "index" / "vectors",
                            ),
                        ):
                            response = client.post(
                                "/api/v1/imports/upload",
                                headers={"X-API-Key": "k"},
                                data={"preset_id": "markdown-notes", "tags": "test"},
                                files=[("files", ("a.md", b"# a", "text/markdown"))],
                            )
        assert response.status_code == 200
        assert import_mock.called
        args, kwargs = import_mock.call_args
        assert kwargs.get("source_type") == "folder"
        assert "test" in kwargs.get("tags", [])


    def test_duplicate_upload_reported(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("AI_OS_API_KEY", "k")
        monkeypatch.setenv("AI_OS_DATA_DIR", str(tmp_path / "data"))
        for key in ("KNOWLEDGE_RAW_DIR", "KNOWLEDGE_PROCESSED_DIR", "KNOWLEDGE_INDEX_DIR", "VECTOR_STORE_PATH"):
            monkeypatch.delenv(key, raising=False)

        from ai_os.knowledge.populate import ImportProgress

        fake = ImportProgress()
        fake.total = 1
        fake.processed = 1
        fake.skipped = 1

        with patch(
            "ai_os.api.routers.imports.KnowledgeImporter.import_path",
            return_value=fake,
        ):
            with patch("ai_os.knowledge.maintenance.MaintenanceService.ensure_search_indexes"):
                with patch("ai_os.knowledge.health.HealthService") as health_cls:
                    health_cls.return_value.report.return_value = MagicMock(
                        document_count=1, chunk_count=2
                    )
                    with patch(
                        "ai_os.api.routers.imports.validate_import",
                        return_value=MagicMock(
                            ready=True, errors=[], new_files=0, duplicate_files=1
                        ),
                    ):
                        with patch(
                            "ai_os.knowledge.config.get_settings",
                            return_value=KnowledgeSettings(
                                ai_os_data_dir=tmp_path / "data",
                                knowledge_raw_dir=tmp_path / "data" / "knowledge" / "raw",
                                knowledge_processed_dir=tmp_path / "data" / "knowledge" / "processed",
                                knowledge_index_dir=tmp_path / "data" / "knowledge" / "index",
                                vector_store_path=tmp_path / "data" / "knowledge" / "index" / "vectors",
                            ),
                        ):
                            response = client.post(
                                "/api/v1/imports/upload",
                                headers={"X-API-Key": "k"},
                                data={"preset_id": "markdown-notes"},
                                files=[("files", ("a.md", b"# a", "text/markdown"))],
                            )
        assert response.status_code == 200
        assert response.json()["duplicate_files"] == 1
        assert response.json()["skipped"] == 1

    def test_search_remains_available(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AI_OS_API_KEY", "secret-test-key")
        response = client.get("/api/v1/search", params={"q": "test"})
        assert response.status_code == 200
        assert response.json()["query"] == "test"

    def test_presets_include_existing_registry(self) -> None:
        from ai_os.knowledge.onboarding import load_presets

        ids = {p.id for p in load_presets()}
        assert "markdown-notes" in ids
        assert "personal-documents" in ids
        assert "invented-preset" not in ids
