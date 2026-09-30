import { Router, Request, Response } from "express";
import {
  queryRAGService,
  getRAGMetrics,
  getRAGMetricsSummary,
  RAGServiceError,
} from "../services/rag/client";

export const ragRouter = Router();

// ---------------------------------------------------------------------------
// POST /api/rag/query
// Proxies natural language queries to the Python FastAPI RAG service
// ---------------------------------------------------------------------------
ragRouter.post("/rag/query", async (req: Request, res: Response) => {
  try {
    const { query, top_k, campus, batch, gender, school } = req.body || {};

    // 1. Validate query
    if (!query || typeof query !== "string" || !query.trim()) {
      res.status(400).json({
        success: false,
        error: "Query must be a non-empty string.",
      });
      return;
    }

    if (query.trim().length > 1000) {
      res.status(400).json({
        success: false,
        error: "Query exceeds the maximum allowed length of 1000 characters.",
      });
      return;
    }

    // 2. Validate top_k if supplied
    let validatedTopK: number | undefined;
    if (top_k !== undefined && top_k !== null) {
      const parsedTopK = Number(top_k);
      if (!Number.isInteger(parsedTopK) || parsedTopK < 1 || parsedTopK > 50) {
        res.status(400).json({
          success: false,
          error: "top_k must be an integer between 1 and 50.",
        });
        return;
      }
      validatedTopK = parsedTopK;
    }

    // 3. Forward request to Python FastAPI RAG service
    const result = await queryRAGService({
      query: query.trim(),
      top_k: validatedTopK,
      campus: typeof campus === "string" ? campus : undefined,
      batch: typeof batch === "string" || typeof batch === "number" ? String(batch) : undefined,
      gender: typeof gender === "string" ? gender : undefined,
      school: typeof school === "string" ? school : undefined,
    });

    res.status(200).json({
      success: true,
      query: result.query,
      query_type: result.query_type,
      retrieval_status: result.retrieval_status,
      answer: result.answer,
      sources: result.sources,
      aggregation: result.aggregation,
      timings: result.timings,
    });
  } catch (error: unknown) {
    if (error instanceof RAGServiceError) {
      res.status(error.statusCode).json({
        success: false,
        error: error.message,
      });
      return;
    }

    console.error("[rag] Unexpected error:", error);
    res.status(500).json({
      success: false,
      error: "An internal server error occurred while processing the RAG query.",
    });
  }
});

// ---------------------------------------------------------------------------
// GET /api/rag/metrics and GET /api/metrics
// Proxies metrics logs to the Python FastAPI RAG service
// ---------------------------------------------------------------------------
const handleMetricsGet = async (req: Request, res: Response) => {
  try {
    const limit = req.query.limit ? Number(req.query.limit) : 50;
    const queryType = typeof req.query.query_type === "string" ? req.query.query_type : undefined;
    const status = typeof req.query.status === "string" ? req.query.status : undefined;

    const data = await getRAGMetrics(limit, queryType, status);
    res.status(200).json(data);
  } catch (error: unknown) {
    if (error instanceof RAGServiceError) {
      res.status(error.statusCode).json({
        success: false,
        error: error.message,
      });
      return;
    }
    console.error("[rag] Unexpected error fetching metrics:", error);
    res.status(500).json({
      success: false,
      error: "An internal server error occurred while fetching RAG metrics.",
    });
  }
};

ragRouter.get("/rag/metrics", handleMetricsGet);
ragRouter.get("/metrics", handleMetricsGet);

// ---------------------------------------------------------------------------
// GET /api/rag/metrics/summary and GET /api/metrics/summary
// Proxies aggregated metrics summary to the Python FastAPI RAG service
// ---------------------------------------------------------------------------
const handleMetricsSummaryGet = async (req: Request, res: Response) => {
  try {
    const data = await getRAGMetricsSummary();
    res.status(200).json(data);
  } catch (error: unknown) {
    if (error instanceof RAGServiceError) {
      res.status(error.statusCode).json({
        success: false,
        error: error.message,
      });
      return;
    }
    console.error("[rag] Unexpected error fetching metrics summary:", error);
    res.status(500).json({
      success: false,
      error: "An internal server error occurred while fetching RAG metrics summary.",
    });
  }
};

ragRouter.get("/rag/metrics/summary", handleMetricsSummaryGet);
ragRouter.get("/metrics/summary", handleMetricsSummaryGet);

