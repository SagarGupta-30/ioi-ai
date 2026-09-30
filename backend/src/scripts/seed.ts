/**
 * Development seed script.
 *
 * Inserts the two example student records from data/raw and data/synthetic
 * into MongoDB. Uses upsert to avoid duplicates on re-run.
 *
 * Usage:
 *   npx tsx src/scripts/seed.ts
 */

import "dotenv/config";
import path from "path";
import fs from "fs";
import mongoose from "mongoose";
import { connectDatabase } from "../config/database";
import { StudentModel, toMongooseDoc } from "../models/student.model";
import type { Student } from "../models/student";

const DATA_ROOT = path.resolve(__dirname, "../../../data");

async function seed() {
  await connectDatabase();

  const files = [
    path.join(DATA_ROOT, "raw", "example-public-student.json"),
    path.join(DATA_ROOT, "synthetic", "example-student.json"),
  ];

  let inserted = 0;
  let skipped = 0;

  for (const filePath of files) {
    const raw = fs.readFileSync(filePath, "utf-8");
    const student: Student = JSON.parse(raw);
    const doc = toMongooseDoc(student);

    const result = await StudentModel.updateOne(
      { studentId: doc.studentId },
      { $setOnInsert: doc },
      { upsert: true },
    );

    if (result.upsertedCount > 0) {
      console.log(`[seed] Inserted: ${student.name} (${student.source.type})`);
      inserted++;
    } else {
      console.log(`[seed] Already exists: ${student.name} — skipped`);
      skipped++;
    }
  }

  console.log(`\n[seed] Done. Inserted: ${inserted}, Skipped: ${skipped}`);

  // Verify
  const total = await StudentModel.countDocuments();
  console.log(`[seed] Total students in database: ${total}`);

  await mongoose.disconnect();
}

seed().catch((err) => {
  console.error("[seed] Failed:", err);
  process.exit(1);
});
