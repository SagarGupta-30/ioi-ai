"use client";

import React, { useEffect, useState, useCallback } from "react";

interface MetricsSummary {
  total_queries: number;
  successful_queries: number;
  failed_queries: number;
  success_rate_pct: number;
  query_type_distribution: Record<string, number>;
  retrieval_status_distribution: Record<string, number>;
  latency_stats: {
    avg_total_ms: number;
    min_total_ms: number;
    max_total_ms: number;
    p50_total_ms: number;
    p95_total_ms: number;
    avg_classification_ms: number;
    avg_embedding_ms: number;
    avg_retrieval_ms: number;
    avg_generation_ms: number;
    avg_aggregation_ms: number;
  };
  last_updated: string;
}

interface QueryMetricRecord {
  id: string;
  timestamp: string;
  query: string;
  query_type: string;
  retrieval_status: string;
  success: boolean;
  sources_count: number;
  timings: Record<string, number>;
  error?: string | null;
}

export default function MetricsDashboard() {
  const [summary, setSummary] = useState<MetricsSummary | null>(null);
  const [records, setRecords] = useState<QueryMetricRecord[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<Date | null>(null);

  const backendUrl = (
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:5001"
  ).replace(/\/+$/, "");

  const fetchMetrics = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [sumRes, recRes] = await Promise.all([
        fetch(`${backendUrl}/api/rag/metrics/summary`),
        fetch(`${backendUrl}/api/rag/metrics?limit=30`),
      ]);

      if (!sumRes.ok || !recRes.ok) {
        throw new Error(
          `Metrics API responded with error: ${sumRes.status} / ${recRes.status}`
        );
      }

      const sumData = await sumRes.json();
      const recData = await recRes.json();

      if (sumData.success && sumData.summary) {
        setSummary(sumData.summary);
      }
      if (recData.success && Array.isArray(recData.metrics)) {
        setRecords(recData.metrics);
      }
      setLastRefreshedAt(new Date());
    } catch (err: unknown) {
      console.error("Failed to fetch metrics telemetry:", err);
      setError(
        err instanceof Error
          ? err.message
          : "Failed to connect to backend metrics proxy."
      );
    } finally {
      setIsLoading(false);
    }
  }, [backendUrl]);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      fetchMetrics();
    }, 8000);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchMetrics]);

  const formatMs = (ms: number | undefined) => {
    if (ms === undefined || ms === null || isNaN(ms)) return "0 ms";
    if (ms < 1) return `${ms.toFixed(1)} ms`;
    if (ms < 1000) return `${Math.round(ms)} ms`;
    return `${(ms / 1000).toFixed(2)} s`;
  };

  const formatTimestamp = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    } catch {
      return iso;
    }
  };

  const getQueryTypeBadge = (type: string) => {
    switch (type.toLowerCase()) {
      case "structured":
        return "bg-blue-50 text-blue-800 border-blue-200";
      case "semantic":
        return "bg-purple-50 text-purple-800 border-purple-200";
      case "hybrid":
        return "bg-emerald-50 text-emerald-800 border-emerald-200";
      case "aggregation":
        return "bg-amber-50 text-amber-800 border-amber-200";
      case "unsupported":
        return "bg-zinc-100 text-zinc-700 border-zinc-200";
      case "out_of_domain":
        return "bg-zinc-100 text-zinc-600 border-zinc-200";
      default:
        return "bg-zinc-100 text-zinc-700 border-zinc-200";
    }
  };

  const getRetrievalStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case "sufficient":
        return "bg-emerald-50 text-emerald-800 border-emerald-200";
      case "insufficient_results":
        return "bg-amber-50 text-amber-800 border-amber-200";
      case "no_results":
        return "bg-zinc-100 text-zinc-600 border-zinc-200";
      case "not_applicable":
        return "bg-indigo-50 text-indigo-800 border-indigo-200";
      default:
        return "bg-zinc-100 text-zinc-700 border-zinc-200";
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 w-full pt-6 pb-12 flex flex-col gap-6 animate-in fade-in duration-300">
      {/* Top Header Card */}
      <div className="bg-white rounded-3xl border border-zinc-200/90 p-6 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-[#eaf4ec] text-emerald-800 flex items-center justify-center flex-shrink-0">
            <svg className="w-5 h-5 text-emerald-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-400">
                SYSTEM TELEMETRY
              </span>
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            </div>
            <h2 className="text-xl font-bold text-zinc-900 tracking-tight">
              Observability & Performance Dashboard
            </h2>
            <p className="text-xs text-zinc-500 mt-0.5">
              Live pipeline execution latency, routing telemetry, and retrieval quality metrics
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 self-end sm:self-center">
          <label className="flex items-center gap-2 text-xs text-zinc-600 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded border-zinc-300 text-[#0c1b15] focus:ring-0"
            />
            <span>Auto-refresh (8s)</span>
          </label>

          <button
            onClick={() => fetchMetrics()}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold rounded-xl bg-zinc-100 hover:bg-zinc-200 text-zinc-800 transition-colors disabled:opacity-50 cursor-pointer"
            title="Refresh metrics telemetry"
          >
            <svg
              className={`w-3.5 h-3.5 ${isLoading ? "animate-spin text-zinc-600" : ""}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span>{isLoading ? "Refreshing..." : "Refresh"}</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-red-50 border border-red-200 text-red-800 text-xs">
          <strong>Telemetry Error:</strong> {error}
        </div>
      )}

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {/* Total Queries */}
        <div className="bg-white rounded-3xl border border-zinc-200/90 p-5 shadow-xs flex flex-col justify-between">
          <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-400">
            Total Queries
          </span>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold tracking-tight text-zinc-900">
              {summary ? summary.total_queries : "—"}
            </span>
            <span className="text-xs text-zinc-400">recorded</span>
          </div>
          <div className="mt-2 text-[11px] text-zinc-500">
            {summary ? `${summary.successful_queries} successful` : "Awaiting queries"}
          </div>
        </div>

        {/* Success Rate */}
        <div className="bg-white rounded-3xl border border-zinc-200/90 p-5 shadow-xs flex flex-col justify-between">
          <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-400">
            Success Rate
          </span>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold tracking-tight text-emerald-700">
              {summary ? `${summary.success_rate_pct}%` : "—"}
            </span>
          </div>
          <div className="mt-2 text-[11px] text-zinc-500">
            {summary ? `${summary.failed_queries} execution errors` : "Zero failures"}
          </div>
        </div>

        {/* Average Latency */}
        <div className="bg-white rounded-3xl border border-zinc-200/90 p-5 shadow-xs flex flex-col justify-between">
          <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-400">
            Avg Total Latency
          </span>
          <div className="mt-3 flex items-baseline gap-1">
            <span className="text-3xl font-extrabold tracking-tight text-zinc-900">
              {summary ? formatMs(summary.latency_stats.avg_total_ms) : "—"}
            </span>
          </div>
          <div className="mt-2 text-[11px] text-zinc-500">
            {summary ? `Median (P50): ${formatMs(summary.latency_stats.p50_total_ms)}` : "—"}
          </div>
        </div>

        {/* P95 Latency */}
        <div className="bg-white rounded-3xl border border-zinc-200/90 p-5 shadow-xs flex flex-col justify-between">
          <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-400">
            P95 Latency
          </span>
          <div className="mt-3 flex items-baseline gap-1">
            <span className="text-3xl font-extrabold tracking-tight text-zinc-900">
              {summary ? formatMs(summary.latency_stats.p95_total_ms) : "—"}
            </span>
          </div>
          <div className="mt-2 text-[11px] text-zinc-500">
            {summary ? `Max: ${formatMs(summary.latency_stats.max_total_ms)}` : "—"}
          </div>
        </div>
      </div>

      {/* Two Column Layout: Distributions & Stage Latencies */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Query Type Distribution */}
        <div className="bg-white rounded-3xl border border-zinc-200/90 p-6 shadow-xs flex flex-col">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-zinc-900">
              Query Type Distribution
            </h3>
            <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-400">
              Router Telemetry
            </span>
          </div>
          <p className="text-xs text-zinc-500 mt-0.5 mb-5">
            Proportion of queries handled across routing paths
          </p>

          <div className="flex flex-col gap-3 flex-1 justify-center">
            {[
              { key: "structured", label: "Structured Directory", color: "bg-blue-600" },
              { key: "semantic", label: "Semantic Search", color: "bg-purple-600" },
              { key: "hybrid", label: "Hybrid (Filter + Rank)", color: "bg-emerald-600" },
              { key: "aggregation", label: "Aggregation (DB Count)", color: "bg-amber-600" },
              { key: "unsupported", label: "Unsupported Guardrail", color: "bg-zinc-400" },
              { key: "out_of_domain", label: "Out of Domain", color: "bg-zinc-300" },
            ].map(({ key, label, color }) => {
              const count = summary?.query_type_distribution?.[key] || 0;
              const total = summary?.total_queries || 1;
              const pct = summary?.total_queries ? Math.round((count / total) * 100) : 0;
              return (
                <div key={key} className="flex flex-col gap-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-medium text-zinc-700">
                      {label}
                    </span>
                    <span className="text-zinc-500 font-mono text-[11px]">
                      {count} ({pct}%)
                    </span>
                  </div>
                  <div className="w-full h-1.5 rounded-full bg-zinc-100 overflow-hidden">
                    <div
                      className={`h-full rounded-full ${color} transition-all duration-500`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Pipeline Stage Latency Breakdown */}
        <div className="bg-white rounded-3xl border border-zinc-200/90 p-6 shadow-xs flex flex-col">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-zinc-900">
              Pipeline Stage Latencies
            </h3>
            <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-400">
              Average ms
            </span>
          </div>
          <p className="text-xs text-zinc-500 mt-0.5 mb-5">
            Mean latency breakdown per processing phase
          </p>

          <div className="flex flex-col gap-2.5 flex-1 justify-center">
            {[
              {
                label: "Query Classification",
                val: summary?.latency_stats?.avg_classification_ms,
                desc: "Deterministic rule router",
              },
              {
                label: "Dense Vector Embedding",
                val: summary?.latency_stats?.avg_embedding_ms,
                desc: "FastEmbed ONNX (384-dim)",
              },
              {
                label: "Vector Store Retrieval",
                val: summary?.latency_stats?.avg_retrieval_ms,
                desc: "ChromaDB cosine search",
              },
              {
                label: "MongoDB Count Aggregation",
                val: summary?.latency_stats?.avg_aggregation_ms,
                desc: "Direct Atlas count index",
              },
              {
                label: "LLM Generation",
                val: summary?.latency_stats?.avg_generation_ms,
                desc: "Local Ollama llama3.2:1b",
              },
            ].map(({ label, val, desc }) => (
              <div
                key={label}
                className="flex items-center justify-between p-3 rounded-2xl bg-[#f8faf8] border border-zinc-100"
              >
                <div>
                  <div className="text-xs font-bold text-zinc-800">
                    {label}
                  </div>
                  <div className="text-[11px] text-zinc-400">{desc}</div>
                </div>
                <div className="text-xs font-bold font-mono text-zinc-900">
                  {formatMs(val)}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Retrieval Status Summary Badges */}
      <div className="bg-white rounded-3xl border border-zinc-200/90 p-6 shadow-xs flex flex-col gap-3">
        <h3 className="text-sm font-bold text-zinc-900">
          Retrieval Evidence States
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            {
              status: "sufficient",
              title: "Sufficient Context",
              desc: "Cosine score ≥ 0.58",
              count: summary?.retrieval_status_distribution?.["sufficient"] || 0,
              badgeClass: "bg-emerald-50 text-emerald-800 border-emerald-200",
            },
            {
              status: "insufficient_results",
              title: "Insufficient Evidence",
              desc: "Cosine score < 0.58",
              count: summary?.retrieval_status_distribution?.["insufficient_results"] || 0,
              badgeClass: "bg-amber-50 text-amber-800 border-amber-200",
            },
            {
              status: "no_results",
              title: "No Records Found",
              desc: "0 records matched filter",
              count: summary?.retrieval_status_distribution?.["no_results"] || 0,
              badgeClass: "bg-zinc-100 text-zinc-600 border-zinc-200",
            },
            {
              status: "not_applicable",
              title: "Direct / Guardrail",
              desc: "Bypassed vector search",
              count: summary?.retrieval_status_distribution?.["not_applicable"] || 0,
              badgeClass: "bg-indigo-50 text-indigo-800 border-indigo-200",
            },
          ].map(({ title, desc, count, badgeClass }) => (
            <div
              key={title}
              className={`p-3.5 rounded-2xl border flex flex-col justify-between ${badgeClass}`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold">{title}</span>
                <span className="text-base font-bold">{count}</span>
              </div>
              <span className="text-[11px] opacity-75 mt-1">{desc}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Query Telemetry Table */}
      <div className="bg-white rounded-3xl border border-zinc-200/90 p-6 shadow-xs flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-bold text-zinc-900">
              Recent Query Telemetry Log
            </h3>
            <p className="text-xs text-zinc-500">
              Last {records.length} queries processed by IOI AI
            </p>
          </div>
          {lastRefreshedAt && (
            <span className="text-[11px] text-zinc-400">
              Updated {lastRefreshedAt.toLocaleTimeString()}
            </span>
          )}
        </div>

        {records.length === 0 ? (
          <div className="py-12 text-center text-xs text-zinc-400 border border-dashed border-zinc-200 rounded-2xl">
            No queries logged yet. Execute questions in the Assistant tab to populate live telemetry.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-zinc-200 text-zinc-400 font-medium text-[11px]">
                  <th className="py-2.5 px-3">Time</th>
                  <th className="py-2.5 px-3">Query</th>
                  <th className="py-2.5 px-3">Type</th>
                  <th className="py-2.5 px-3">Retrieval Status</th>
                  <th className="py-2.5 px-3 text-center">Sources</th>
                  <th className="py-2.5 px-3 text-right">Latency</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100 font-sans">
                {records.map((r) => (
                  <tr
                    key={r.id}
                    className="hover:bg-zinc-50 transition-colors"
                  >
                    <td className="py-2.5 px-3 text-zinc-400 whitespace-nowrap font-mono text-[11px]">
                      {formatTimestamp(r.timestamp)}
                    </td>
                    <td className="py-2.5 px-3 text-zinc-900 font-medium max-w-xs truncate" title={r.query}>
                      {r.query}
                    </td>
                    <td className="py-2.5 px-3 whitespace-nowrap">
                      <span
                        className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold border ${getQueryTypeBadge(
                          r.query_type
                        )}`}
                      >
                        {r.query_type}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 whitespace-nowrap">
                      <span
                        className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-medium border ${getRetrievalStatusBadge(
                          r.retrieval_status
                        )}`}
                      >
                        {r.retrieval_status}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-center text-zinc-600 font-mono">
                      {r.sources_count}
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono font-semibold text-zinc-900 whitespace-nowrap">
                      {formatMs(r.timings?.total_ms)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
