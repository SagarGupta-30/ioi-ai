import mongoose from "mongoose";

/**
 * Connect to MongoDB using the MONGODB_URI environment variable.
 * Fails clearly if the URI is missing or the connection cannot be established.
 */
export async function connectDatabase(): Promise<void> {
  const uri = process.env.MONGODB_URI;

  if (!uri) {
    console.error(
      "[ioi-ai-backend] MONGODB_URI is not set. " +
        "Please create a .env file (see .env.example).",
    );
    process.exit(1);
  }

  try {
    await mongoose.connect(uri);
    console.log(
      `[ioi-ai-backend] MongoDB connected — database: ${mongoose.connection.db?.databaseName ?? "unknown"}`,
    );
  } catch (error) {
    console.error("[ioi-ai-backend] MongoDB connection failed:", error);
    process.exit(1);
  }
}

/** Returns the current Mongoose connection readyState as a human-readable string. */
export function getDatabaseStatus(): string {
  // readyState: 0 = disconnected, 1 = connected, 2 = connecting, 3 = disconnecting
  const state = mongoose.connection.readyState;
  switch (state) {
    case 0:
      return "disconnected";
    case 1:
      return "connected";
    case 2:
      return "connecting";
    case 3:
      return "disconnecting";
    default:
      return "unknown";
  }
}
