/**
 * PW IOI Student Data Ingestion Script
 *
 * Fetches all public student data from the PW IOI API, normalizes it
 * into the existing Student schema, and upserts into MongoDB.
 *
 * Usage:
 *   npm run ingest:pwioi
 */

import "dotenv/config";
import mongoose from "mongoose";
import { connectDatabase } from "../config/database";
import { StudentModel, toMongooseDoc } from "../models/student.model";
import { fromPublicApi, type PublicApiStudentFields } from "../models/student";
import {
  fetchCenters,
  fetchBatches,
  fetchStudents,
  studentEndpointUrl,
  type PwioiRawStudent,
} from "../services/pwioi/api";

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

function isValidStudent(raw: PwioiRawStudent): boolean {
  if (!raw.id || typeof raw.id !== "string") return false;
  if (!raw.name || typeof raw.name !== "string") return false;
  if (raw.gender !== "MALE" && raw.gender !== "FEMALE") return false;
  return true;
}

// ---------------------------------------------------------------------------
// Ingestion
// ---------------------------------------------------------------------------

interface IngestStats {
  totalCenters: number;
  totalBatches: number;
  totalFetched: number;
  inserted: number;
  updated: number;
  invalid: number;
  failures: number;
}

async function ingest(): Promise<void> {
  await connectDatabase();

  const stats: IngestStats = {
    totalCenters: 0,
    totalBatches: 0,
    totalFetched: 0,
    inserted: 0,
    updated: 0,
    invalid: 0,
    failures: 0,
  };

  // 1. Fetch all centers
  console.log("[ingest] Fetching centers...");
  const centers = await fetchCenters();
  stats.totalCenters = centers.length;
  console.log(`[ingest] Found ${centers.length} centers\n`);

  // 2. Iterate centers → batches → students
  for (const center of centers) {
    console.log(`[ingest] Center: ${center.location} (${center.name})`);

    let batches;
    try {
      batches = await fetchBatches(center.id);
    } catch (err) {
      console.error(`[ingest]   ✗ Failed to fetch batches for ${center.location}:`, err);
      stats.failures++;
      continue;
    }

    console.log(`[ingest]   Found ${batches.length} batches`);
    stats.totalBatches += batches.length;

    for (const batch of batches) {
      let rawStudents: PwioiRawStudent[];
      try {
        rawStudents = await fetchStudents(center.id, batch.id);
      } catch (err) {
        console.error(
          `[ingest]   ✗ Failed to fetch students for ${center.location} / batch ${batch.name}:`,
          err,
        );
        stats.failures++;
        continue;
      }

      console.log(`[ingest]   Batch ${batch.name}: ${rawStudents.length} students`);
      stats.totalFetched += rawStudents.length;

      const apiEndpoint = studentEndpointUrl(center.id, batch.id);

      for (const raw of rawStudents) {
        // Validate
        if (!isValidStudent(raw)) {
          console.warn(`[ingest]     ⚠ Invalid record skipped: ${JSON.stringify(raw)}`);
          stats.invalid++;
          continue;
        }

        // Normalize using the existing fromPublicApi helper
        const student = fromPublicApi(
          raw as PublicApiStudentFields,
          center.location,
          batch.name,
          apiEndpoint,
        );

        // Convert to Mongoose shape and upsert
        const doc = toMongooseDoc(student);

        const result = await StudentModel.updateOne(
          { studentId: doc.studentId },
          { $set: doc },
          { upsert: true },
        );

        if (result.upsertedCount > 0) {
          stats.inserted++;
        } else if (result.modifiedCount > 0) {
          stats.updated++;
        }
      }
    }

    console.log(); // blank line between centers
  }

  // 3. Summary
  const totalDb = await StudentModel.countDocuments({
    "source.type": "pwioi_public_api",
  });

  console.log("═".repeat(50));
  console.log("[ingest] INGESTION COMPLETE");
  console.log("═".repeat(50));
  console.log(`  Centers processed:    ${stats.totalCenters}`);
  console.log(`  Batches processed:    ${stats.totalBatches}`);
  console.log(`  Students fetched:     ${stats.totalFetched}`);
  console.log(`  Inserted (new):       ${stats.inserted}`);
  console.log(`  Updated (existing):   ${stats.updated}`);
  console.log(`  Invalid/skipped:      ${stats.invalid}`);
  console.log(`  API failures:         ${stats.failures}`);
  console.log(`  Total public in DB:   ${totalDb}`);
  console.log("═".repeat(50));

  await mongoose.disconnect();
}

ingest().catch((err) => {
  console.error("[ingest] Fatal error:", err);
  process.exit(1);
});
