/**
 * RAG Service Client
 *
 * Communicates with the local FastAPI RAG service.
 * Handles timeouts, network errors, and status codes.
 */

export interface RAGQueryOptions {
  query: string;
  top_k?: number;
  campus?: string;
  batch?: string;
  gender?: string;
  school?: string;
}

export interface RAGSource {
  student_id: string;
  name: string;
  campus: string;
  batch: string;
  gender: string;
  similarity_score: number;
  source_type: string;
}

export interface RAGResponse {
  success: boolean;
  query: string;
  query_type?: string;
  retrieval_status?: string;
  answer: string;
  sources: RAGSource[];
  aggregation?: {
    count: number;
    filters?: Record<string, any>;
  };
  timings?: Record<string, number>;
}

export class RAGServiceError extends Error {
  statusCode: number;

  constructor(message: string, statusCode: number = 500) {
    super(message);
    this.name = "RAGServiceError";
    this.statusCode = statusCode;
  }
}

/**
 * Send a query to the Python FastAPI RAG service.
 */
export async function queryRAGService(
  options: RAGQueryOptions,
  timeoutMs: number = 60000,
): Promise<RAGResponse> {
  const ragBaseUrl = (process.env.RAG_SERVICE_URL || "http://localhost:8000").replace(/\/+$/, "");
  const targetUrl = `${ragBaseUrl}/api/rag/query`;

  let response: Response;
  try {
    response = await fetch(targetUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(options),
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch (err: unknown) {
    if (err instanceof Error) {
      if (err.name === "TimeoutError") {
        throw new RAGServiceError("RAG service request timed out.", 504);
      }
      if (err.message.includes("ECONNREFUSED") || err.name === "TypeError") {
        throw new RAGServiceError(
          "RAG service is currently unavailable. Ensure the FastAPI service is running on port 8000.",
          503,
        );
      }
    }
    throw new RAGServiceError("Failed to connect to RAG service.", 503);
  }

  const responseText = await response.text();
  let responseData: any;
  try {
    responseData = JSON.parse(responseText);
  } catch {
    throw new RAGServiceError("Invalid JSON received from RAG service.", 502);
  }

  if (!response.ok) {
    const errorMsg = responseData?.error || responseData?.detail || `RAG service returned HTTP ${response.status}`;
    throw new RAGServiceError(errorMsg, response.status >= 500 ? 502 : response.status);
  }

  return responseData as RAGResponse;
}

export interface QueryMetricRecord {
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

export interface MetricsSummary {
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

/**
 * Fetch recent query metrics records from RAG service.
 */
export async function getRAGMetrics(
  limit: number = 50,
  queryType?: string,
  status?: string,
  timeoutMs: number = 10000,
): Promise<{ success: boolean; count: number; metrics: QueryMetricRecord[] }> {
  const ragBaseUrl = (process.env.RAG_SERVICE_URL || "http://localhost:8000").replace(/\/+$/, "");
  const params = new URLSearchParams();
  if (limit) params.set("limit", String(limit));
  if (queryType) params.set("query_type", queryType);
  if (status) params.set("status", status);

  const targetUrl = `${ragBaseUrl}/api/metrics?${params.toString()}`;

  let response: Response;
  try {
    response = await fetch(targetUrl, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch (err: unknown) {
    if (err instanceof Error) {
      if (err.name === "TimeoutError") {
        throw new RAGServiceError("RAG metrics request timed out.", 504);
      }
      if (err.message.includes("ECONNREFUSED") || err.name === "TypeError") {
        throw new RAGServiceError(
          "RAG service is currently unavailable. Ensure the FastAPI service is running on port 8000.",
          503,
        );
      }
    }
    throw new RAGServiceError("Failed to connect to RAG service metrics endpoint.", 503);
  }

  const responseText = await response.text();
  let responseData: any;
  try {
    responseData = JSON.parse(responseText);
  } catch {
    throw new RAGServiceError("Invalid JSON received from RAG metrics endpoint.", 502);
  }

  if (!response.ok) {
    const errorMsg = responseData?.error || responseData?.detail || `RAG metrics returned HTTP ${response.status}`;
    throw new RAGServiceError(errorMsg, response.status >= 500 ? 502 : response.status);
  }

  return responseData;
}

/**
 * Fetch aggregated metrics summary from RAG service.
 */
export async function getRAGMetricsSummary(
  timeoutMs: number = 10000,
): Promise<{ success: boolean; summary: MetricsSummary }> {
  const ragBaseUrl = (process.env.RAG_SERVICE_URL || "http://localhost:8000").replace(/\/+$/, "");
  const targetUrl = `${ragBaseUrl}/api/metrics/summary`;

  let response: Response;
  try {
    response = await fetch(targetUrl, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch (err: unknown) {
    if (err instanceof Error) {
      if (err.name === "TimeoutError") {
        throw new RAGServiceError("RAG metrics summary request timed out.", 504);
      }
      if (err.message.includes("ECONNREFUSED") || err.name === "TypeError") {
        throw new RAGServiceError(
          "RAG service is currently unavailable. Ensure the FastAPI service is running on port 8000.",
          503,
        );
      }
    }
    throw new RAGServiceError("Failed to connect to RAG service metrics summary endpoint.", 503);
  }

  const responseText = await response.text();
  let responseData: any;
  try {
    responseData = JSON.parse(responseText);
  } catch {
    throw new RAGServiceError("Invalid JSON received from RAG metrics summary endpoint.", 502);
  }

  if (!response.ok) {
    const errorMsg = responseData?.error || responseData?.detail || `RAG metrics summary returned HTTP ${response.status}`;
    throw new RAGServiceError(errorMsg, response.status >= 500 ? 502 : response.status);
  }

  return responseData;
}

