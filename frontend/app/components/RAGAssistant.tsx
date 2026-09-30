"use client";

import React, { useState, useEffect, useCallback } from "react";

interface SourceItem {
  name: string;
  campus: string;
  batch: string;
  gender: string;
  similarity_score: number;
  source_type: string;
}

interface RAGResponse {
  success: boolean;
  query: string;
  query_type?: string;
  retrieval_status?: string;
  answer: string;
  sources: SourceItem[];
  aggregation?: {
    count: number;
    filters?: Record<string, any>;
  };
  timings?: Record<string, number>;
  error?: string;
}

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

interface Props {
  activeTab?: "assistant" | "metrics";
}

const EXAMPLE_QUERIES = [
  "Who are some students from Bengaluru?",
  "Find male students from batch 26",
  "Female students from Pune interested in machine learning",
  "How many students are in Bengaluru?",
];

// Initial default state directly matching the design reference screenshot
const INITIAL_PREVIEW: RAGResponse = {
  success: true,
  query: "What is Sagar Gupta's roll number and campus?",
  query_type: "semantic",
  retrieval_status: "sufficient",
  answer:
    "Sagar Gupta’s roll number isn’t available in the records. His campus is Bengaluru.",
  sources: [
    {
      name: "Sagar Gupta",
      campus: "Bengaluru",
      batch: "23",
      gender: "MALE",
      similarity_score: 0.7204,
      source_type: "pwioi_public_api",
    },
    {
      name: "Aman Gupta",
      campus: "Bengaluru",
      batch: "24",
      gender: "MALE",
      similarity_score: 0.6812,
      source_type: "pwioi_public_api",
    },
    {
      name: "Krishna Gupta",
      campus: "Bengaluru",
      batch: "26",
      gender: "MALE",
      similarity_score: 0.6543,
      source_type: "pwioi_public_api",
    },
  ],
};

export default function RAGAssistant({ activeTab = "assistant" }: Props) {
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<RAGResponse>(INITIAL_PREVIEW);
  const [hasQueried, setHasQueried] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Metrics telemetry state for Observability view
  const [metricsSummary, setMetricsSummary] = useState<MetricsSummary | null>(null);
  const [recentRecords, setRecentRecords] = useState<QueryMetricRecord[]>([]);
  const [isMetricsLoading, setIsMetricsLoading] = useState(false);

  const backendUrl =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:5001";

  // Fetch telemetry metrics
  const fetchMetrics = useCallback(async () => {
    setIsMetricsLoading(true);
    try {
      const [sumRes, recRes] = await Promise.all([
        fetch(`${backendUrl}/api/rag/metrics/summary`),
        fetch(`${backendUrl}/api/rag/metrics?limit=15`),
      ]);
      if (sumRes.ok && recRes.ok) {
        const sumData = await sumRes.json();
        const recData = await recRes.json();
        if (sumData.success && sumData.summary) {
          setMetricsSummary(sumData.summary);
        }
        if (recData.success && Array.isArray(recData.metrics)) {
          setRecentRecords(recData.metrics);
        }
      }
    } catch {
      // Non-fatal background fetch
    } finally {
      setIsMetricsLoading(false);
    }
  }, [backendUrl]);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  const handleSubmit = async (searchQuery: string) => {
    const trimmed = searchQuery.trim();
    if (!trimmed) {
      setError("Please enter a question or search query.");
      return;
    }

    if (isLoading) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${backendUrl}/api/rag/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: trimmed,
          top_k: 5,
        }),
      });

      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(
          data.error ||
            `Server returned status ${response.status}: Failed to generate answer.`
        );
      }

      setResult(data);
      setHasQueried(true);
      fetchMetrics();
    } catch (err: unknown) {
      if (err instanceof Error) {
        if (
          err.message.includes("Failed to fetch") ||
          err.message.includes("NetworkError")
        ) {
          setError(
            "Unable to connect to backend server. Ensure Express is running on port 5001."
          );
        } else {
          setError(err.message);
        }
      } else {
        setError("An unexpected error occurred while processing your query.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleExampleClick = (example: string) => {
    setQuery(example);
    handleSubmit(example);
  };

  const handleCampusClick = (campus: string) => {
    const campusQuery = `Who are some students from ${campus}?`;
    setQuery(campusQuery);
    handleSubmit(campusQuery);
  };

  const handleCopy = () => {
    if (!result?.answer) return;
    navigator.clipboard.writeText(result.answer);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatMs = (ms: number | undefined) => {
    if (ms === undefined || ms === null || isNaN(ms)) return "0 ms";
    if (ms < 1) return `${ms.toFixed(1)} ms`;
    if (ms < 1000) return `${Math.round(ms)} ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  const getQueryBadgeLabel = (type?: string) => {
    switch (type) {
      case "aggregation":
        return "EXACT COUNT";
      case "structured":
        return "STRUCTURED MATCH";
      case "hybrid":
        return "HYBRID MATCH";
      case "unsupported":
        return "PRIVACY SAFEGUARD";
      case "out_of_domain":
        return "OUT OF DOMAIN";
      case "semantic":
      default:
        return "SEMANTIC MATCH";
    }
  };

  const renderFormattedAnswer = (text: string) => {
    if (!text) return null;
    const parts = text.split(/(\*\*[^*]+\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return (
          <strong key={i} className="font-extrabold text-[#7052d6]">
            {part.slice(2, -2)}
          </strong>
        );
      }
      return part;
    });
  };

  return (
    <div className="w-full flex flex-col items-center">
      {/* 1. Overlapping Search / Query Card */}
      <section className="relative -mt-14 sm:-mt-16 z-20 max-w-6xl mx-auto px-4 sm:px-6 w-full animate-fade-in-up">
        <div className="bg-white rounded-[26px] border border-[#e7e4f0] shadow-sm p-6 sm:p-7">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2">
            <div>
              <div className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-[#6e6785]">
                <span className="w-2 h-2 rounded-full bg-[#7052d6]" />
                <span>START A SEARCH</span>
              </div>
              <h2 className="text-xl sm:text-2xl font-bold text-[#28243d] mt-1 tracking-tight">
                What would you like to know?
              </h2>
            </div>
            <div className="self-start sm:self-auto">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-[#f3f0fa] border border-[#e7e4f0] text-[#6e6785]">
                <svg className="w-3.5 h-3.5 text-[#16a34a]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>Grounded in student records</span>
              </span>
            </div>
          </div>

          {/* Search Input Bar */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSubmit(query);
            }}
            className="mt-4"
          >
            <div className="relative flex items-center rounded-2xl border border-[#e7e4f0] bg-white focus-within:border-[#7052d6] focus-within:ring-2 focus-within:ring-[#7052d6]/10 transition-all p-1.5 shadow-2xs">
              <div className="pl-3 pr-2 text-[#888099]">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <input
                type="text"
                id="rag-query-input"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="What is Sagar Gupta's roll number and campus?"
                disabled={isLoading}
                className="w-full bg-transparent py-2.5 px-2 text-sm sm:text-base text-[#28243d] placeholder:text-[#888099] focus:outline-none disabled:opacity-50"
              />
              <button
                type="submit"
                id="rag-submit-button"
                disabled={isLoading || !query.trim()}
                className="px-5 py-2.5 rounded-xl bg-[#7052d6] hover:bg-[#5d42c3] text-white text-xs sm:text-sm font-semibold transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5 shadow-xs flex-shrink-0 cursor-pointer active:scale-98"
              >
                {isLoading ? (
                  <>
                    <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                    <span>Searching...</span>
                  </>
                ) : (
                  <>
                    <span>Search</span>
                    <span className="text-white/80">→</span>
                  </>
                )}
              </button>
            </div>

            {/* Example Queries */}
            <div className="flex flex-wrap items-center gap-2 mt-4 pt-1">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[#888099] mr-1">
                TRY ASKING
              </span>
              {EXAMPLE_QUERIES.map((example, idx) => (
                <button
                  key={idx}
                  type="button"
                  id={`example-query-${idx}`}
                  onClick={() => handleExampleClick(example)}
                  disabled={isLoading}
                  className="inline-flex items-center gap-1 text-xs px-3.5 py-1.5 rounded-full border border-[#e7e4f0] bg-[#f3f0fa] hover:bg-[#eae5f7] hover:border-[#ddd6fe] text-[#4a4365] transition-all cursor-pointer disabled:opacity-50 font-medium active:scale-98"
                >
                  <span>{example}</span>
                  <span className="text-[#888099] text-[10px]">↗</span>
                </button>
              ))}
            </div>
          </form>
        </div>
      </section>

      {/* Query Error Notification */}
      {error && !isLoading && (
        <div className="max-w-6xl mx-auto px-4 sm:px-6 w-full mt-4">
          <div
            id="rag-error-banner"
            className="w-full rounded-2xl border border-red-200 bg-red-50/80 p-4 text-xs sm:text-sm text-red-800 flex items-start gap-3 shadow-xs"
          >
            <svg className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="flex-1">
              <span className="font-bold uppercase tracking-wide text-xs">Query Request Notice</span>
              <p className="mt-0.5 text-zinc-700">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* 2. Main Content Grid: Left Column (Answer or Observability) + Right Column (Knowledge Base & Trust) */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 w-full mt-6 grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column (~72% width) */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          {activeTab === "assistant" ? (
            /* Assistant Mode: AI Grounded Answer Card */
            <div className="bg-white rounded-[26px] border border-[#e7e4f0] p-6 sm:p-7 shadow-xs flex flex-col gap-4 animate-fade-in-up">
              {/* Answer Card Top Header */}
              <div className="flex items-center justify-between pb-3 border-b border-[#f0edf7]">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-[#e4f7ed] text-[#16a34a] flex items-center justify-center flex-shrink-0">
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M12 2L14.2 8.3L20.5 10.5L14.2 12.7L12 19L9.8 12.7L3.5 10.5L9.8 8.3L12 2Z" />
                    </svg>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-[#28243d] leading-tight">
                      AI GROUNDED ANSWER
                    </span>
                    <span className="text-xs text-[#888099] font-normal leading-tight">
                      For your latest search
                    </span>
                  </div>
                </div>

                {/* Status Badge */}
                <span
                  id="rag-query-type-badge"
                  className="inline-flex items-center px-3 py-1 rounded-full text-[10px] font-bold tracking-wider uppercase border border-[#bbf7d0] bg-[#e4f7ed] text-[#16a34a]"
                >
                  {getQueryBadgeLabel(result?.query_type)}
                </span>
              </div>

              {/* Answer Body */}
              <div className="flex flex-col gap-3">
                <p className="text-xs text-[#888099] italic">
                  “{result?.query}”
                </p>

                {/* Headline Answer Text */}
                <div
                  id="rag-answer-text"
                  className="text-xl sm:text-2xl font-bold tracking-tight text-[#28243d] leading-snug whitespace-pre-line"
                >
                  {!hasQueried ? (
                    <>
                      Sagar Gupta’s roll number isn’t available in the records. His campus is{" "}
                      <span className="text-[#7052d6] font-extrabold">Bengaluru.</span>
                    </>
                  ) : (
                    renderFormattedAnswer(result?.answer)
                  )}
                </div>

                {/* "WHAT THE RECORDS TELL US" Evidence Box */}
                <div className="bg-[#f8f7fb] border border-[#e7e4f0] rounded-2xl p-4 sm:p-5 flex flex-col gap-2 mt-2">
                  <div className="flex items-center gap-2 text-[#7052d6]">
                    <svg className="w-4 h-4 text-[#7052d6] flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                    </svg>
                    <span className="text-[11px] font-bold uppercase tracking-wider text-[#7052d6]">
                      WHAT THE RECORDS TELL US
                    </span>
                  </div>

                  <p className="text-xs sm:text-sm text-[#4a4365] leading-relaxed">
                    {!hasQueried
                      ? "The provided student record lists Sagar Gupta under SOT (School of Technology) at the Bengaluru campus. No roll number was found in the available record, so we won't guess one."
                      : result?.query_type === "aggregation"
                      ? `Verified institutional count computed directly via MongoDB Atlas directory index across 1,097 student documents.`
                      : result?.query_type === "unsupported"
                      ? "The public directory preserves privacy and does not record private contact numbers, personal emails, or academic GPAs."
                      : result?.retrieval_status === "insufficient_results"
                      ? "Retrieved context similarity score fell below the verified safety threshold (0.58). The assistant refrains from guessing."
                      : `Answer synthesized strictly from ${result?.sources?.length || 0} retrieved student profiles ranked by FastEmbed (bge-small-en-v1.5) cosine similarity.`}
                  </p>
                </div>
              </div>

              {/* Answer Card Footer */}
              <div className="pt-3 border-t border-[#f0edf7] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-[#888099]">
                <div className="flex items-center gap-1.5">
                  <svg className="w-4 h-4 text-[#16a34a] flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <span className="text-[#4a4365] font-medium text-[11px] sm:text-xs">
                    Grounded in 1,097 verified student documents
                  </span>
                  {result?.timings && (
                    <span className="ml-2 font-mono text-[10px] text-[#888099]">
                      ({(result.timings.total_ms / 1000).toFixed(2)}s)
                    </span>
                  )}
                </div>

                <button
                  type="button"
                  onClick={handleCopy}
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#4a4365] hover:text-[#28243d] transition-colors cursor-pointer self-start sm:self-auto"
                >
                  {copied ? (
                    <>
                      <svg className="w-3.5 h-3.5 text-[#16a34a]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      <span className="text-[#16a34a]">Copied!</span>
                    </>
                  ) : (
                    <>
                      <svg className="w-3.5 h-3.5 text-[#888099]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                      <span>Copy answer</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          ) : (
            /* Observability Mode: System Insights Card matching Figma Reference */
            <div className="bg-white rounded-[26px] border border-[#e7e4f0] p-6 sm:p-7 shadow-xs flex flex-col gap-6 animate-fade-in-up">
              <div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-[#7052d6]">
                  SYSTEM INSIGHTS
                </span>
                <h3 className="text-2xl font-bold text-[#28243d] tracking-tight mt-1">
                  Observability
                </h3>
                <p className="text-xs text-[#888099] mt-0.5">
                  A transparent look at the example retrieval pipeline.
                </p>
              </div>

              {/* 3 Metric Cards matching reference */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {/* 1. Verified documents */}
                <div className="bg-[#f8f7fb] border border-[#e7e4f0] rounded-2xl p-4 flex flex-col justify-between">
                  <div className="w-8 h-8 rounded-lg bg-[#eeeafc] text-[#7052d6] flex items-center justify-center mb-3">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2 1.5 3 3.5 3h9c2 0 3.5-1 3.5-3V7c0-2-1.5-3-3.5-3h-9C5.5 4 4 5 4 7zm0 5h16M4 12c0 2 1.5 3 3.5 3h9c2 0 3.5-1 3.5-3" />
                    </svg>
                  </div>
                  <div>
                    <span className="text-2xl sm:text-3xl font-extrabold text-[#28243d]">
                      1,097
                    </span>
                    <span className="block text-xs text-[#888099] mt-0.5">
                      Verified documents
                    </span>
                  </div>
                </div>

                {/* 2. Retrieved sources */}
                <div className="bg-[#f8f7fb] border border-[#e7e4f0] rounded-2xl p-4 flex flex-col justify-between">
                  <div className="w-8 h-8 rounded-lg bg-[#eeeafc] text-[#7052d6] flex items-center justify-center mb-3">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                    </svg>
                  </div>
                  <div>
                    <span className="text-2xl sm:text-3xl font-extrabold text-[#28243d]">
                      {result?.sources?.length || 5}
                    </span>
                    <span className="block text-xs text-[#888099] mt-0.5">
                      Retrieved sources
                    </span>
                  </div>
                </div>

                {/* 3. Latency */}
                <div className="bg-[#f8f7fb] border border-[#e7e4f0] rounded-2xl p-4 flex flex-col justify-between">
                  <div className="w-8 h-8 rounded-lg bg-[#eeeafc] text-[#7052d6] flex items-center justify-center mb-3">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div>
                    <span className="text-2xl sm:text-3xl font-extrabold text-[#28243d]">
                      {metricsSummary?.latency_stats?.avg_total_ms
                        ? formatMs(metricsSummary.latency_stats.avg_total_ms)
                        : "9.05s"}
                    </span>
                    <span className="block text-xs text-[#888099] mt-0.5">
                      Example latency
                    </span>
                  </div>
                </div>
              </div>

              {/* Dark Purple Pipeline Flowchart Card */}
              <div className="bg-[#1f1a38] text-white rounded-2xl p-5 shadow-xs flex flex-col gap-3">
                <div className="flex items-center gap-2 text-xs font-semibold text-[#b5b0c7]">
                  <svg className="w-4 h-4 text-[#a78bfa]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  <span>Example answer pipeline</span>
                </div>

                <div className="flex flex-wrap items-center gap-2 pt-1 text-xs">
                  <span className="px-3.5 py-1.5 rounded-xl bg-[#2e284f] border border-[#433c6e] text-white font-medium">
                    Student documents
                  </span>
                  <span className="text-[#a78bfa]">→</span>
                  <span className="px-3.5 py-1.5 rounded-xl bg-[#2e284f] border border-[#433c6e] text-white font-medium">
                    FastEmbed + ChromaDB
                  </span>
                  <span className="text-[#a78bfa]">→</span>
                  <span className="px-3.5 py-1.5 rounded-xl bg-[#2e284f] border border-[#433c6e] text-white font-medium">
                    Ollama
                  </span>
                  <span className="text-[#a78bfa]">→</span>
                  <span className="px-3.5 py-1.5 rounded-xl bg-[#2e284f] border border-[#433c6e] text-[#a78bfa] font-medium">
                    Grounded answer
                  </span>
                </div>
              </div>

              <p className="text-[11px] text-[#888099]">
                Metrics and pipeline details are shown from the connected local backend.
              </p>

              {/* Additional Live Telemetry KPIs */}
              {metricsSummary && (
                <div className="border-t border-[#f0edf7] pt-4 flex flex-col gap-4">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-[#6e6785]">
                      Live Telemetry Statistics
                    </h4>
                    <span className="text-[10px] font-mono text-[#888099]">
                      {metricsSummary.total_queries} queries logged
                    </span>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                    <div className="p-3 rounded-xl bg-[#f8f7fb] border border-[#e7e4f0]">
                      <span className="text-[10px] text-[#888099] block">Success Rate</span>
                      <span className="font-bold text-base text-[#16a34a]">
                        {metricsSummary.success_rate_pct}%
                      </span>
                    </div>
                    <div className="p-3 rounded-xl bg-[#f8f7fb] border border-[#e7e4f0]">
                      <span className="text-[10px] text-[#888099] block">Median (P50)</span>
                      <span className="font-bold text-base text-[#28243d]">
                        {formatMs(metricsSummary.latency_stats.p50_total_ms)}
                      </span>
                    </div>
                    <div className="p-3 rounded-xl bg-[#f8f7fb] border border-[#e7e4f0]">
                      <span className="text-[10px] text-[#888099] block">P95 Latency</span>
                      <span className="font-bold text-base text-[#7052d6]">
                        {formatMs(metricsSummary.latency_stats.p95_total_ms)}
                      </span>
                    </div>
                    <div className="p-3 rounded-xl bg-[#f8f7fb] border border-[#e7e4f0]">
                      <span className="text-[10px] text-[#888099] block">Router Speed</span>
                      <span className="font-bold text-base text-[#28243d]">
                        {formatMs(metricsSummary.latency_stats.avg_classification_ms)}
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Column: Knowledge Base & Peach Trust Card (~28% width) */}
        <div className="lg:col-span-4 flex flex-col gap-5 animate-fade-in-up">
          {/* Card 1: Knowledge Base Card */}
          <div className="bg-white rounded-[26px] border border-[#e7e4f0] p-6 shadow-xs flex flex-col">
            <div className="w-9 h-9 rounded-xl bg-[#eeeafc] text-[#7052d6] flex items-center justify-center mb-3">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2 1.5 3 3.5 3h9c2 0 3.5-1 3.5-3V7c0-2-1.5-3-3.5-3h-9C5.5 4 4 5 4 7zm0 5h16M4 12c0 2 1.5 3 3.5 3h9c2 0 3.5-1 3.5-3" />
              </svg>
            </div>

            <span className="text-[11px] font-bold uppercase tracking-wider text-[#888099]">
              KNOWLEDGE BASE
            </span>
            <h3 className="text-lg font-bold text-[#28243d] mt-0.5">
              Student records
            </h3>
            <p className="text-xs text-[#6e6785] leading-relaxed mt-1">
              A searchable view across the PW IOI student community.
            </p>

            <div className="mt-4 pt-1 flex items-baseline justify-between">
              <div>
                <span className="text-3xl sm:text-4xl font-extrabold tracking-tight text-[#28243d]">
                  1,097
                </span>
                <span className="block text-xs text-[#888099] font-medium">
                  verified documents
                </span>
              </div>
              <div className="w-7 h-7 rounded-full bg-[#e4f7ed] border border-[#bbf7d0] flex items-center justify-center text-[#16a34a]">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                </svg>
              </div>
            </div>

            <div className="border-t border-[#f0edf7] my-4" />

            {/* Campus Coverage Chips */}
            <span className="text-[10px] font-bold uppercase tracking-wider text-[#888099] mb-2.5">
              CAMPUS COVERAGE
            </span>
            <div className="flex flex-wrap gap-1.5">
              {["Bengaluru", "Pune", "Noida", "Lucknow"].map((campus) => (
                <button
                  key={campus}
                  type="button"
                  onClick={() => handleCampusClick(campus)}
                  className="px-3 py-1 rounded-full text-xs font-medium border border-[#e7e4f0] bg-[#f8f7fb] hover:bg-[#eeeafc] hover:border-[#ddd6fe] text-[#4a4365] transition-colors cursor-pointer"
                >
                  {campus}
                </button>
              ))}
            </div>
          </div>

          {/* Card 2: Warm Peach Trust Card matching reference */}
          <div className="bg-[#fdf2ec] border border-[#f7dfd3] rounded-[26px] p-6 shadow-xs flex flex-col gap-2">
            <div className="w-8 h-8 rounded-xl bg-white text-[#7c3d2e] flex items-center justify-center shadow-2xs mb-1">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>

            <h3 className="text-base font-bold text-[#7c3d2e]">
              Built for trust.
            </h3>
            <p className="text-xs text-[#8c4132] leading-relaxed">
              Answers are tied to available records. When information is missing, the assistant says so instead of filling in the blanks.
            </p>

            <div className="border-t border-[#f7dfd3] my-2" />

            <div className="flex items-center gap-1.5 text-[11px] font-bold tracking-wider uppercase text-[#8c4132]">
              <svg className="w-3.5 h-3.5 text-[#8c4132]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
              </svg>
              <span>EVIDENCE OVER ASSUMPTIONS</span>
            </div>
          </div>

          {/* Helper Footnote */}
          <div className="px-2 flex items-start gap-2 text-[11px] text-[#888099]">
            <svg className="w-3.5 h-3.5 text-[#888099] flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>
              Preview interface based on the provided example. Connect a retrieval API for live queries.
            </span>
          </div>
        </div>
      </section>

      {/* 3. The Evidence / Retrieved Sources Section (always accessible) */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 w-full mt-12 mb-16 animate-fade-in-up">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2 mb-4">
          <div>
            <span className="text-[11px] font-bold uppercase tracking-widest text-[#888099]">
              THE EVIDENCE
            </span>
            <h3 className="text-xl sm:text-2xl font-bold text-[#28243d] tracking-tight mt-0.5">
              Retrieved sources{" "}
              <span className="text-[#888099] font-normal">
                ({result?.sources?.length || 0} shown)
              </span>
            </h3>
          </div>
          <span className="text-xs text-[#888099] font-medium">
            {!hasQueried ? "From the reference example" : "Ranked by Cosine Similarity"}
          </span>
        </div>

        {/* Source Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {(result?.sources || []).map((source, index) => {
            const similarityPct = Math.round(source.similarity_score * 100);
            const isSynthetic = source.source_type === "synthetic";

            return (
              <div
                key={index}
                className="bg-white rounded-2xl border border-[#e7e4f0] p-5 shadow-xs hover:border-[#7052d6]/40 hover:-translate-y-0.5 hover:shadow-sm transition-all flex flex-col justify-between gap-4"
              >
                <div className="flex flex-col gap-3">
                  <div className="flex items-center justify-between">
                    <div className="w-8 h-8 rounded-lg bg-[#eeeafc] text-[#7052d6] flex items-center justify-center">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-[#888099]">
                      SOURCE 0{index + 1}
                    </span>
                  </div>

                  <div>
                    <h4 className="text-base font-bold text-[#28243d] truncate">
                      {source.name}
                    </h4>
                    <p className="text-xs text-[#6e6785] mt-0.5">
                      School of Technology · {source.campus} campus
                    </p>
                  </div>

                  {/* Badges */}
                  <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-[#4a4365]">
                    <span className="px-2 py-0.5 rounded-md bg-[#f3f0fa] text-[10px] font-medium text-[#4a4365]">
                      Batch {source.batch}
                    </span>
                    <span className="px-2 py-0.5 rounded-md bg-[#f3f0fa] text-[10px] font-medium text-[#4a4365]">
                      {source.gender}
                    </span>
                    <span className="px-2 py-0.5 rounded-md bg-[#e4f7ed] text-[#16a34a] font-mono text-[10px] font-medium">
                      {similarityPct}% match
                    </span>
                  </div>
                </div>

                {/* Card Bottom */}
                <div className="pt-3 border-t border-[#f0edf7] flex items-center justify-between text-xs">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[#888099]">
                    {isSynthetic ? "SYNTHETIC DEMO" : "PW IOI PUBLIC"}
                  </span>
                  <svg className="w-3.5 h-3.5 text-[#888099]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
