# app/src/utils/metrics.py

import atexit
import json
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Optional

METRICS_PATH = Path(".cache/metrics/metrics.json")
FLUSH_EVERY = 50  # auto-flush after this many writes


class MetricsCoordinator:
    _instance: Optional["MetricsCoordinator"] = None
    _init_lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._lock = threading.Lock()
        self._counters: dict[str, dict] = defaultdict(lambda: defaultdict(float))
        self._gauges: dict[str, dict] = defaultdict(lambda: defaultdict(float))
        self._histograms: dict[str, dict] = defaultdict(lambda: defaultdict(list))
        self._write_count = 0
        self._initialized = True
        atexit.register(self.flush)

    # ── Core Methods ──────────────────────────────────────────────────────────

    def _label_key(self, labels: Optional[dict]) -> str:
        if not labels:
            return "__no_labels__"
        return json.dumps(labels, sort_keys=True)

    def increment(self, metric_name: str, labels: Optional[dict] = None, value: float = 1):
        key = self._label_key(labels)
        with self._lock:
            self._counters[metric_name][key] += value
            self._write_count += 1
            if self._write_count >= FLUSH_EVERY:
                self._flush_locked()

    def gauge(self, metric_name: str, labels: Optional[dict] = None, value: float = 0):
        key = self._label_key(labels)
        with self._lock:
            self._gauges[metric_name][key] = value
            self._write_count += 1
            if self._write_count >= FLUSH_EVERY:
                self._flush_locked()

    def histogram(self, metric_name: str, labels: Optional[dict] = None, value: float = 0):
        key = self._label_key(labels)
        with self._lock:
            self._histograms[metric_name][key].append(value)
            self._write_count += 1
            if self._write_count >= FLUSH_EVERY:
                self._flush_locked()

    def get_value(self, metric_name: str, labels: Optional[dict] = None) -> Any:
        key = self._label_key(labels)
        with self._lock:
            if metric_name in self._counters:
                return self._counters[metric_name].get(key, 0)
            if metric_name in self._gauges:
                return self._gauges[metric_name].get(key, 0)
            if metric_name in self._histograms:
                vals = self._histograms[metric_name].get(key, [])
                return {"count": len(vals), "sum": sum(vals), "values": vals}
        return None

    # ── Flush ─────────────────────────────────────────────────────────────────

    def _flush_locked(self):
        """Must be called under self._lock."""
        METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
        output: dict = {}

        for name, label_map in self._counters.items():
            for label_key, val in label_map.items():
                labels = None if label_key == "__no_labels__" else json.loads(label_key)
                entry_key = f"{name}|{label_key}"
                output[entry_key] = {"type": "counter", "value": val}
                if labels:
                    output[entry_key]["labels"] = labels

        for name, label_map in self._gauges.items():
            for label_key, val in label_map.items():
                labels = None if label_key == "__no_labels__" else json.loads(label_key)
                entry_key = f"{name}|{label_key}"
                output[entry_key] = {"type": "gauge", "value": val}
                if labels:
                    output[entry_key]["labels"] = labels

        for name, label_map in self._histograms.items():
            for label_key, vals in label_map.items():
                labels = None if label_key == "__no_labels__" else json.loads(label_key)
                entry_key = f"{name}|{label_key}"
                output[entry_key] = {
                    "type": "histogram",
                    "count": len(vals),
                    "sum": round(sum(vals), 6),
                    "mean": round(sum(vals) / len(vals), 6) if vals else 0,
                    "values": vals,
                }
                if labels:
                    output[entry_key]["labels"] = labels

        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": output,
        }
        METRICS_PATH.write_text(json.dumps(payload, indent=2))
        self._write_count = 0

    def flush(self):
        with self._lock:
            self._flush_locked()

    # ── Prometheus Exposition Format (bonus) ──────────────────────────────────

    def to_prometheus(self) -> str:
        lines = []
        with self._lock:
            for name, label_map in self._counters.items():
                lines.append(f"# TYPE {name} counter")
                for label_key, val in label_map.items():
                    labels = "" if label_key == "__no_labels__" else \
                        "{" + ",".join(f'{k}="{v}"' for k, v in json.loads(label_key).items()) + "}"
                    lines.append(f"{name}{labels} {val}")

            for name, label_map in self._gauges.items():
                lines.append(f"# TYPE {name} gauge")
                for label_key, val in label_map.items():
                    labels = "" if label_key == "__no_labels__" else \
                        "{" + ",".join(f'{k}="{v}"' for k, v in json.loads(label_key).items()) + "}"
                    lines.append(f"{name}{labels} {val}")

            for name, label_map in self._histograms.items():
                lines.append(f"# TYPE {name} histogram")
                for label_key, vals in label_map.items():
                    labels = "" if label_key == "__no_labels__" else \
                        "{" + ",".join(f'{k}="{v}"' for k, v in json.loads(label_key).items()) + "}"
                    lines.append(f"{name}_count{labels} {len(vals)}")
                    lines.append(f"{name}_sum{labels} {sum(vals)}")
        return "\n".join(lines)

    # ── Reset (for tests) ─────────────────────────────────────────────────────

    def reset(self):
        with self._lock:
            self._counters = defaultdict(lambda: defaultdict(float))
            self._gauges = defaultdict(lambda: defaultdict(float))
            self._histograms = defaultdict(lambda: defaultdict(list))
            self._write_count = 0


# ── Singleton accessor ────────────────────────────────────────────────────────

def get_metrics() -> MetricsCoordinator:
    return MetricsCoordinator()


# ── Decorator ─────────────────────────────────────────────────────────────────

def track_tool(tool_name: str):
    """Decorator to auto-track tool_calls_total, tool_errors_total, tool_duration_seconds."""
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            m = get_metrics()
            m.increment("tool_calls_total", {"tool_name": tool_name})
            start = time.perf_counter()
            try:
                result = fn(*args, **kwargs)
                return result
            except Exception as e:
                m.increment("tool_errors_total", {"tool_name": tool_name})
                raise
            finally:
                m.histogram("tool_duration_seconds", {"tool_name": tool_name},
                            time.perf_counter() - start)
        return wrapper
    return decorator


def track_llm(fn: Callable) -> Callable:
    """Decorator to auto-track LLM call metrics."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        m = get_metrics()
        m.increment("llm_calls_total")
        start = time.perf_counter()
        try:
            result = fn(*args, **kwargs)
            return result
        except Exception as e:
            m.increment("llm_errors_total")
            raise
        finally:
            m.histogram("llm_duration_seconds", value=time.perf_counter() - start)
    return wrapper