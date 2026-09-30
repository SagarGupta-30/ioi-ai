import { Router, Request, Response } from "express";
import { getDatabaseStatus } from "../config/database";

export const healthRouter = Router();

healthRouter.get("/health", (_req: Request, res: Response) => {
  const dbStatus = getDatabaseStatus();

  res.json({
    status: dbStatus === "connected" ? "ok" : "degraded",
    service: "ioi-ai-backend",
    database: dbStatus,
  });
});
