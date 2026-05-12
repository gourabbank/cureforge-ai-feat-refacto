# app/tests/test_hypothesis_bank.py

import sys
from unittest.mock import MagicMock, patch

mock_settings = MagicMock()
mock_settings.litellm_api_key = "test"
mock_settings.jina_api_key = "test"
mock_settings.model_name = "test"
mock_settings.redis_password = "test"

patch("app.src.utils.settings.get_settings", return_value=mock_settings).start()
patch("app.src.utils.logger.get_settings", return_value=mock_settings).start()

import pytest
import threading
from pathlib import Path
from app.src.core.tools.hypothesis_bank import storage


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "embeddings.db")
    monkeypatch.setattr(storage, "FAISS_PATH", tmp_path / "faiss.index")
    monkeypatch.setattr(storage, "FAISS_ID_MAP_PATH", tmp_path / "faiss_id_map.json")
    yield


def test_add_and_retrieve():
    hyp_id = storage.add_hypothesis(
        text="Inhibiting VEGFR2 may reduce tumor angiogenesis in glioblastoma.",
        disease="glioblastoma",
        phase_origin="hypothesize",
        keywords=["VEGFR2", "angiogenesis"],
        efficacy_score=0.7,
        safety_score=0.8,
    )
    assert hyp_id is not None
    result = storage.get_hypothesis(hyp_id)
    assert result["disease"] == "glioblastoma"
    assert result["efficacy_score"] == 0.7
    assert "VEGFR2" in result["keywords"]


def test_semantic_search_returns_relevant():
    storage.add_hypothesis(
        text="mTOR pathway inhibition shows promise in pancreatic cancer models.",
        disease="pancreatic_cancer",
        keywords=["mTOR"],
    )
    storage.add_hypothesis(
        text="Aspirin reduces cardiovascular inflammation markers.",
        disease="cardiovascular",
        keywords=["aspirin"],
    )
    results = storage.search_hypotheses("mTOR signaling cancer", top_k=1)
    assert len(results) == 1
    assert "mTOR" in results[0]["text"] or results[0]["disease"] == "pancreatic_cancer"


def test_disease_filter():
    storage.add_hypothesis(text="Hypothesis A", disease="cancer")
    storage.add_hypothesis(text="Hypothesis B", disease="diabetes")
    results = storage.search_hypotheses("treatment", disease_filter="cancer")
    assert all(r["disease"] == "cancer" for r in results)


def test_empty_database():
    results = storage.search_hypotheses("anything")
    assert results == []
    listing = storage.list_hypotheses()
    assert listing == []


def test_update_scores():
    hyp_id = storage.add_hypothesis(text="Test hypothesis", disease="test_disease")
    success = storage.update_scores(hyp_id, efficacy_score=0.9, safety_score=0.95,
                                    update_reason="Trial results confirmed")
    assert success is True
    result = storage.get_hypothesis(hyp_id)
    assert result["efficacy_score"] == 0.9
    assert "Trial results confirmed" in result["notes"]


def test_concurrent_writes():
    errors = []

    def write(i):
        try:
            storage.add_hypothesis(
                text=f"Concurrent hypothesis {i}",
                disease="test",
            )
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=write, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == [], f"Concurrent write errors: {errors}"
    assert len(storage.list_hypotheses()) == 10


def test_export_markdown():
    storage.add_hypothesis(
        text="Export test hypothesis", disease="lupus",
        keywords=["IL-6"], efficacy_score=0.6, safety_score=0.7,
    )
    md = storage.export_to_markdown(disease="lupus")
    assert "# Hypothesis Bank" in md
    assert "lupus" in md
    assert "IL-6" in md