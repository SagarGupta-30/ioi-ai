import "dotenv/config";
import express from "express";
import cors from "cors";
import { connectDatabase } from "./config/database";
import { healthRouter } from "./routes/health";
import { studentsRouter } from "./routes/students";
import { ragRouter } from "./routes/rag";

const app = express();
const PORT = process.env.PORT || 5001;

// Middleware
const allowedOrigins = process.env.CORS_ORIGIN
  ? process.env.CORS_ORIGIN.split(",").map((s) => s.trim())
  : "*";
app.use(cors({ origin: allowedOrigins, credentials: true }));
app.use(express.json({ limit: "1mb" }));

// Routes
app.use("/api", healthRouter);
app.use("/api", studentsRouter);
app.use("/api", ragRouter);

// Global Error Handling Middleware (catches body-parser SyntaxErrors and unhandled errors)
app.use((err: any, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
  if (err instanceof SyntaxError && "status" in err && (err as any).status === 400 && "body" in err) {
    res.status(400).json({
      success: false,
      error: "Malformed JSON request body.",
    });
    return;
  }
  console.error("[ioi-ai-backend] Unhandled server error:", err);
  res.status(500).json({
    success: false,
    error: "An unexpected server error occurred.",
  });
});


// Startup: connect to MongoDB, then start Express
async function start() {
  await connectDatabase();

  app.listen(PORT, () => {
    console.log(`[ioi-ai-backend] Server running on http://localhost:${PORT}`);
  });
}

start();
