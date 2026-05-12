# app/tests/test_metrics.py

import json
import threading
import sys
from unittest.mock import MagicMock, patch
from pathlib import Path

mock_settings = MagicMock()
mock_settings.litellm_api_key = "test"
mock_settings.jina_api_key = "test"
mock_settings.model_name = "test"
mock_settings.redis_password = "test"
patch("app.src.utils.settings.get_settings", return_value=mock_settings).start()
patch("app.src.utils.logger.get_settings", return_value=mock_settings).start()

import pytest
from app.src.utils.metrics import MetricsCoordinator, get_metrics, track_tool


@pytest.fixture(autouse=True)
def fresh_metrics():
    get_metrics().reset()
    yield
    get_metrics().reset()


class TestIncrement:
    def test_basic_increment(self):
        m = get_metrics()
        m.increment("test_counter")
        assert m.get_value("test_counter") == 1

    def test_increment_by_value(self):
        m = get_metrics()
        m.increment("test_counter", value=5)
        assert m.get_value("test_counter") == 5

    def test_increment_accumulates(self):
        m = get_metrics()
        m.increment("test_counter")
        m.increment("test_counter")
        assert m.get_value("test_counter") == 2

    def test_increment_with_labels(self):
        m = get_metrics()
        m.increment("phase_transitions_total", {"phase_from": "research", "phase_to": "hypothesize"})
        assert m.get_value("phase_transitions_total", {"phase_from": "research", "phase_to": "hypothesize"}) == 1

    def test_different_labels_are_independent(self):
        m = get_metrics()
        m.increment("tool_calls_total", {"tool_name": "search"})
        m.increment("tool_calls_total", {"tool_name": "write"})
        assert m.get_value("tool_calls_total", {"tool_name": "search"}) == 1
        assert m.get_value("tool_calls_total", {"tool_name": "write"}) == 1


class TestGauge:
    def test_gauge_set(self):
        m = get_metrics()
        m.gauge("active_agents", value=3)
        assert m.get_value("active_agents") == 3

    def test_gauge_overwrite(self):
        m = get_metrics()
        m.gauge("active_agents", value=3)
        m.gauge("active_agents", value=5)
        assert m.get_value("active_agents") == 5

    def test_gauge_with_labels(self):
        m = get_metrics()
        m.gauge("llm_tokens_used", {"model": "gpt-4"}, value=1000)
        assert m.get_value("llm_tokens_used", {"model": "gpt-4"}) == 1000


class TestHistogram:
    def test_histogram_records_values(self):
        m = get_metrics()
        m.histogram("tool_duration_seconds", {"tool_name": "search"}, value=0.5)
        m.histogram("tool_duration_seconds", {"tool_name": "search"}, value=1.0)
        result = m.get_value("tool_duration_seconds", {"tool_name": "search"})
        assert result["count"] == 2
        assert result["sum"] == 1.5

    def test_histogram_empty(self):
        m = get_metrics()
        result = m.get_value("nonexistent_histogram")
        assert result is None


class TestFlush:
    def test_flush_creates_file(self, tmp_path, monkeypatch):
        import app.src.utils.metrics as metrics_module
        monkeypatch.setattr(metrics_module, "METRICS_PATH", tmp_path / "metrics.json")
        m = get_metrics()
        m.increment("agent_created_total")
        m.flush()
        assert (tmp_path / "metrics.json").exists()

    def test_flush_valid_json(self, tmp_path, monkeypatch):
        import app.src.utils.metrics as metrics_module
        monkeypatch.setattr(metrics_module, "METRICS_PATH", tmp_path / "metrics.json")
        m = get_metrics()
        m.increment("agent_created_total", value=3)
        m.gauge("active_agents", value=2)
        m.histogram("agent_runtime_seconds", value=10.5)
        m.flush()
        data = json.loads((tmp_path / "metrics.json").read_text())
        assert "timestamp" in data
        assert "metrics" in data

    def test_flush_contains_metrics(self, tmp_path, monkeypatch):
        import app.src.utils.metrics as metrics_module
        monkeypatch.setattr(metrics_module, "METRICS_PATH", tmp_path / "metrics.json")
        m = get_metrics()
        m.increment("agent_created_total", value=5)
        m.flush()
        data = json.loads((tmp_path / "metrics.json").read_text())
        keys = list(data["metrics"].keys())
        assert any("agent_created_total" in k for k in keys)


class TestThreadSafety:
    def test_concurrent_increments(self):
        m = get_metrics()
        errors = []

        def worker():
            try:
                for _ in range(100):
                    m.increment("concurrent_counter")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert errors == []
        assert m.get_value("concurrent_counter") == 1000

    def test_concurrent_mixed_ops(self):
        m = get_metrics()
        errors = []

        def writer():
            try:
                m.increment("mixed_counter")
                m.gauge("mixed_gauge", value=1)
                m.histogram("mixed_hist", value=0.1)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer) for _ in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert errors == []


class TestDecorator:
    def test_track_tool_increments_calls(self):
        m = get_metrics()

        @track_tool("my_tool")
        def my_fn():
            return "ok"

        my_fn()
        assert m.get_value("tool_calls_total", {"tool_name": "my_tool"}) == 1

    def test_track_tool_records_duration(self):
        m = get_metrics()

        @track_tool("timed_tool")
        def my_fn():
            return "ok"

        my_fn()
        result = m.get_value("tool_duration_seconds", {"tool_name": "timed_tool"})
        assert result["count"] == 1

    def test_track_tool_records_errors(self):
        m = get_metrics()

        @track_tool("broken_tool")
        def broken():
            raise ValueError("oops")

        with pytest.raises(ValueError):
            broken()

        assert m.get_value("tool_errors_total", {"tool_name": "broken_tool"}) == 1

    def test_track_tool_preserves_return_value(self):
        @track_tool("return_tool")
        def fn():
            return 42

        assert fn() == 42


class TestSingleton:
    def test_same_instance(self):
        a = get_metrics()
        b = get_metrics()
        assert a is b

    def test_state_shared_across_references(self):
        a = get_metrics()
        b = get_metrics()
        a.increment("shared_metric")
        assert b.get_value("shared_metric") == 1


class TestPrometheusFormat:
    def test_prometheus_output_contains_metric(self):
        m = get_metrics()
        m.increment("agent_created_total", value=3)
        output = m.to_prometheus()
        assert "agent_created_total" in output
        assert "3" in output