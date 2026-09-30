"""
Production Observability and Metrics Collection for IOI AI RAG Service.

Collects, aggregates, and persists query performance, classification distributions,
retrieval health, and latency breakdowns without external/paid dependencies.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import threading
from typing import Any, Optional
import uuid

# Base path for persistent metrics log
DEFAULT_METRICS_DIR = Path(__file__).resolve().parents[2] / "data" / "metrics"
DEFAULT_METRICS_FILE = DEFAULT_METRICS_DIR / "query_metrics.jsonl"
MAX_IN_MEMORY_RECORDS = 1000


@dataclass
class QueryMetricRecord:
    """Individual record of a processed RAG query."""

    id: str
    timestamp: str
    query: str
    query_type: str
    retrieval_status: str
    success: bool
    sources_count: int
    timings: dict[str, float]
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MetricsCollector:
    """
    Thread-safe in-memory and persistent metrics collection engine.
    """

    def __init__(
        self,
        log_file: Optional[Path] = None,
        max_records: int = MAX_IN_MEMORY_RECORDS,
    ):
        self._lock = threading.Lock()
        self._log_file = log_file or DEFAULT_METRICS_FILE
        self._max_records = max_records
        self._records: list[QueryMetricRecord] = []
        self._ensure_log_dir()
        self._load_persisted_records()

    def _ensure_log_dir(self) -> None:
        try:
            self._log_file.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"[metrics] Warning: could not create metrics directory: {e}")

    def _load_persisted_records(self) -> None:
        """Load latest entries from JSONL log on startup."""
        if not self._log_file.exists():
            return

        loaded: list[QueryMetricRecord] = []
        try:
            with open(self._log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        loaded.append(
                            QueryMetricRecord(
                                id=data.get("id", str(uuid.uuid4())),
                                timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
                                query=data.get("query", ""),
                                query_type=data.get("query_type", "unknown"),
                                retrieval_status=data.get("retrieval_status", "unknown"),
                                success=data.get("success", True),
                                sources_count=int(data.get("sources_count", 0)),
                                timings=data.get("timings", {}),
                                error=data.get("error"),
                            )
                        )
                    except Exception:
                        continue
            # Keep only the last max_records
            with self._lock:
                self._records = loaded[-self._max_records :]
        except Exception as e:
            print(f"[metrics] Notice: could not load existing metrics file: {e}")

    def record_query(
        self,
        query: str,
        query_type: str,
        retrieval_status: str,
        success: bool = True,
        sources_count: int = 0,
        timings: Optional[dict[str, float]] = None,
        error: Optional[str] = None,
    ) -> QueryMetricRecord:
        """Record a completed or failed query."""
        record = QueryMetricRecord(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            query=query[:200],  # Truncate overly long queries
            query_type=query_type,
            retrieval_status=retrieval_status,
            success=success,
            sources_count=sources_count,
            timings={k: round(v, 2) for k, v in (timings or {}).items()},
            error=error,
        )

        with self._lock:
            self._records.append(record)
            if len(self._records) > self._max_records:
                self._records.pop(0)

        # Append asynchronously or immediately to JSONL log
        try:
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record.to_dict()) + "\n")
        except Exception as e:
            print(f"[metrics] Warning: could not append to metrics log: {e}")

        return record

    def get_metrics(
        self,
        limit: int = 50,
        query_type: Optional[str] = None,
        retrieval_status: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Return the most recent query records matching optional filters."""
        with self._lock:
            records = list(self._records)

        # Reverse so most recent come first
        records.reverse()

        filtered: list[dict[str, Any]] = []
        for r in records:
            if query_type and r.query_type != query_type:
                continue
            if retrieval_status and r.retrieval_status != retrieval_status:
                continue
            filtered.append(r.to_dict())
            if len(filtered) >= limit:
                break

        return filtered

    def get_summary(self) -> dict[str, Any]:
        """Compute aggregated observability statistics across recorded queries."""
        with self._lock:
            records = list(self._records)

        total_queries = len(records)
        if total_queries == 0:
            return {
                "total_queries": 0,
                "successful_queries": 0,
                "failed_queries": 0,
                "success_rate_pct": 100.0,
                "query_type_distribution": {},
                "retrieval_status_distribution": {},
                "latency_stats": {
                    "avg_total_ms": 0.0,
                    "min_total_ms": 0.0,
                    "max_total_ms": 0.0,
                    "p50_total_ms": 0.0,
                    "p95_total_ms": 0.0,
                    "avg_classification_ms": 0.0,
                    "avg_embedding_ms": 0.0,
                    "avg_retrieval_ms": 0.0,
                    "avg_generation_ms": 0.0,
                    "avg_aggregation_ms": 0.0,
                },
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

        successful_queries = sum(1 for r in records if r.success)
        failed_queries = total_queries - successful_queries
        success_rate_pct = round((successful_queries / total_queries) * 100.0, 2)

        # Distributions
        query_type_dist: dict[str, int] = {}
        status_dist: dict[str, int] = {}

        total_latencies: list[float] = []
        classification_latencies: list[float] = []
        embedding_latencies: list[float] = []
        retrieval_latencies: list[float] = []
        generation_latencies: list[float] = []
        aggregation_latencies: list[float] = []

        for r in records:
            query_type_dist[r.query_type] = query_type_dist.get(r.query_type, 0) + 1
            status_dist[r.retrieval_status] = status_dist.get(r.retrieval_status, 0) + 1

            t = r.timings or {}
            if "total_ms" in t:
                total_latencies.append(t["total_ms"])
            if "classification_ms" in t:
                classification_latencies.append(t["classification_ms"])
            if "embedding_ms" in t:
                embedding_latencies.append(t["embedding_ms"])
            if "retrieval_ms" in t:
                retrieval_latencies.append(t["retrieval_ms"])
            if "generation_ms" in t:
                generation_latencies.append(t["generation_ms"])
            if "aggregation_ms" in t:
                aggregation_latencies.append(t["aggregation_ms"])

        # Compute percentile and average latencies
        def calc_avg(vals: list[float]) -> float:
            return round(sum(vals) / len(vals), 2) if vals else 0.0

        total_latencies.sort()
        min_total = round(total_latencies[0], 2) if total_latencies else 0.0
        max_total = round(total_latencies[-1], 2) if total_latencies else 0.0
        avg_total = calc_avg(total_latencies)

        if total_latencies:
            p50_idx = int(len(total_latencies) * 0.50)
            p95_idx = min(int(len(total_latencies) * 0.95), len(total_latencies) - 1)
            p50_total = round(total_latencies[p50_idx], 2)
            p95_total = round(total_latencies[p95_idx], 2)
        else:
            p50_total = 0.0
            p95_total = 0.0

        return {
            "total_queries": total_queries,
            "successful_queries": successful_queries,
            "failed_queries": failed_queries,
            "success_rate_pct": success_rate_pct,
            "query_type_distribution": query_type_dist,
            "retrieval_status_distribution": status_dist,
            "latency_stats": {
                "avg_total_ms": avg_total,
                "min_total_ms": min_total,
                "max_total_ms": max_total,
                "p50_total_ms": p50_total,
                "p95_total_ms": p95_total,
                "avg_classification_ms": calc_avg(classification_latencies),
                "avg_embedding_ms": calc_avg(embedding_latencies),
                "avg_retrieval_ms": calc_avg(retrieval_latencies),
                "avg_generation_ms": calc_avg(generation_latencies),
                "avg_aggregation_ms": calc_avg(aggregation_latencies),
            },
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    def clear(self) -> None:
        """Clear in-memory records (useful for test isolation)."""
        with self._lock:
            self._records.clear()


# Global singleton instance
_METRICS_COLLECTOR: Optional[MetricsCollector] = None
_INIT_LOCK = threading.Lock()


def get_metrics_collector() -> MetricsCollector:
    """Return the global singleton MetricsCollector."""
    global _METRICS_COLLECTOR
    if _METRICS_COLLECTOR is None:
        with _INIT_LOCK:
            if _METRICS_COLLECTOR is None:
                _METRICS_COLLECTOR = MetricsCollector()
    return _METRICS_COLLECTOR
