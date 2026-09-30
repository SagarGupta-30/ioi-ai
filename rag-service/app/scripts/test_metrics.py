"""
Automated Test Suite for Step 8L: Production Observability & Metrics Collection.

Tests:
1. MetricsCollector unit tests (record, filter, summary math, clear)
2. Query Router pipeline metrics instrumentation
3. FastAPI /api/metrics endpoint (filtering, limits, status codes)
4. FastAPI /api/metrics/summary endpoint (statistical integrity)
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.metrics import MetricsCollector, QueryMetricRecord, get_metrics_collector
from app.query_router import route_and_execute_query
from app.main import app
from starlette.testclient import TestClient


class TestMetricsCollection(unittest.TestCase):
    def setUp(self):
        self.collector = MetricsCollector(log_file=Path("/tmp/test_ioi_metrics.jsonl"))
        self.collector.clear()

    def test_01_record_and_retrieve_metrics(self):
        """Verify basic metric recording and filtering."""
        r1 = self.collector.record_query(
            query="students from Pune",
            query_type="structured",
            retrieval_status="sufficient",
            success=True,
            sources_count=3,
            timings={"classification_ms": 1.2, "retrieval_ms": 15.4, "total_ms": 25.1},
        )
        r2 = self.collector.record_query(
            query="how many male students are there",
            query_type="aggregation",
            retrieval_status="not_applicable",
            success=True,
            sources_count=0,
            timings={"classification_ms": 0.8, "aggregation_ms": 40.2, "total_ms": 41.0},
        )
        r3 = self.collector.record_query(
            query="weather today",
            query_type="out_of_domain",
            retrieval_status="insufficient_results",
            success=True,
            sources_count=0,
            timings={"classification_ms": 0.4, "total_ms": 0.5},
        )

        all_records = self.collector.get_metrics(limit=10)
        self.assertEqual(len(all_records), 3)

        # Reverse ordering check (latest query first)
        self.assertEqual(all_records[0]["query"], "weather today")
        self.assertEqual(all_records[1]["query"], "how many male students are there")
        self.assertEqual(all_records[2]["query"], "students from Pune")

        # Query type filtering
        agg_records = self.collector.get_metrics(query_type="aggregation")
        self.assertEqual(len(agg_records), 1)
        self.assertEqual(agg_records[0]["query_type"], "aggregation")

        # Retrieval status filtering
        suff_records = self.collector.get_metrics(retrieval_status="sufficient")
        self.assertEqual(len(suff_records), 1)
        self.assertEqual(suff_records[0]["retrieval_status"], "sufficient")

    def test_02_summary_statistics_calculations(self):
        """Verify accuracy of summary metrics, distributions, and latency percentiles."""
        self.collector.record_query(
            query="q1",
            query_type="structured",
            retrieval_status="sufficient",
            success=True,
            sources_count=2,
            timings={"classification_ms": 1.0, "retrieval_ms": 10.0, "total_ms": 100.0},
        )
        self.collector.record_query(
            query="q2",
            query_type="semantic",
            retrieval_status="sufficient",
            success=True,
            sources_count=5,
            timings={"classification_ms": 2.0, "retrieval_ms": 20.0, "total_ms": 200.0},
        )
        self.collector.record_query(
            query="q3",
            query_type="aggregation",
            retrieval_status="not_applicable",
            success=True,
            sources_count=0,
            timings={"classification_ms": 1.0, "aggregation_ms": 30.0, "total_ms": 300.0},
        )
        self.collector.record_query(
            query="q4",
            query_type="unsupported",
            retrieval_status="not_applicable",
            success=False,
            sources_count=0,
            timings={"classification_ms": 1.0, "total_ms": 20.0},
            error="Private attribute refused",
        )

        summary = self.collector.get_summary()

        self.assertEqual(summary["total_queries"], 4)
        self.assertEqual(summary["successful_queries"], 3)
        self.assertEqual(summary["failed_queries"], 1)
        self.assertEqual(summary["success_rate_pct"], 75.0)

        # Check distribution counts
        q_dist = summary["query_type_distribution"]
        self.assertEqual(q_dist["structured"], 1)
        self.assertEqual(q_dist["semantic"], 1)
        self.assertEqual(q_dist["aggregation"], 1)
        self.assertEqual(q_dist["unsupported"], 1)

        r_dist = summary["retrieval_status_distribution"]
        self.assertEqual(r_dist["sufficient"], 2)
        self.assertEqual(r_dist["not_applicable"], 2)

        # Check latency statistics
        l_stats = summary["latency_stats"]
        self.assertEqual(l_stats["min_total_ms"], 20.0)
        self.assertEqual(l_stats["max_total_ms"], 300.0)
        self.assertEqual(l_stats["avg_total_ms"], 155.0)  # (100+200+300+20)/4 = 155.0
        self.assertTrue(l_stats["p50_total_ms"] <= l_stats["p95_total_ms"])

    def test_03_query_pipeline_automatic_recording(self):
        """Verify that route_and_execute_query automatically records into the global collector."""
        global_collector = get_metrics_collector()
        count_before = len(global_collector.get_metrics(limit=500))

        # Run a fast deterministic aggregation query
        res = route_and_execute_query("how many students are in Bengaluru")
        self.assertTrue(res["success"])

        count_after = len(global_collector.get_metrics(limit=500))
        self.assertGreater(count_after, count_before)

        latest = global_collector.get_metrics(limit=1)[0]
        self.assertEqual(latest["query"], "how many students are in Bengaluru")
        self.assertEqual(latest["query_type"], "aggregation")
        self.assertEqual(latest["retrieval_status"], "not_applicable")
        self.assertTrue(latest["success"])
        self.assertIn("total_ms", latest["timings"])

    def test_04_fastapi_endpoints(self):
        """Verify HTTP behavior for /api/metrics and /api/metrics/summary."""
        client = TestClient(app)

        # Test /api/metrics
        resp = client.get("/api/metrics?limit=10")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertIsInstance(data["metrics"], list)

        # Test /api/metrics/summary
        resp_sum = client.get("/api/metrics/summary")
        self.assertEqual(resp_sum.status_code, 200)
        data_sum = resp_sum.json()
        self.assertTrue(data_sum["success"])
        self.assertIn("total_queries", data_sum["summary"])
        self.assertIn("latency_stats", data_sum["summary"])
        self.assertIn("query_type_distribution", data_sum["summary"])

        # Test invalid limit parameter validation
        resp_invalid = client.get("/api/metrics?limit=500")
        self.assertEqual(resp_invalid.status_code, 400)


def run_tests():
    print("=" * 60)
    print("IOI AI — STEP 8L METRICS & OBSERVABILITY TEST SUITE")
    print("=" * 60)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestMetricsCollection)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        sys.exit(1)
    print("\n✓ All Metrics & Observability Tests Passed Successfully!")


if __name__ == "__main__":
    run_tests()
