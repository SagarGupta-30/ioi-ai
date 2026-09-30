import { Schema, model } from "mongoose";
import type {
  Student,
  SourceMetadata,
  StudentProject,
  PublicLinks,
} from "./student";

// ---------------------------------------------------------------------------
// Mongoose Sub-schemas
// ---------------------------------------------------------------------------

const sourceMetadataSchema = new Schema<SourceMetadata>(
  {
    type: { type: String, required: true, enum: ["pwioi_public_api", "synthetic"] },
    status: { type: String, required: true, enum: ["public", "demo"] },
    origin: { type: String, required: true },
    ingestedAt: { type: String, required: true },
  },
  { _id: false },
);

const studentProjectSchema = new Schema<StudentProject>(
  {
    title: { type: String, required: true },
    description: { type: String, default: null },
    url: { type: String, default: null },
  },
  { _id: false },
);

const publicLinksSchema = new Schema<PublicLinks>(
  {
    linkedin: { type: String, default: null },
    github: { type: String, default: null },
    portfolio: { type: String, default: null },
  },
  { _id: false },
);

// ---------------------------------------------------------------------------
// Student Schema
//
// Our Student.id (the PW IOI UUID or synthetic ID) is stored in a field
// called `studentId` to avoid collision with Mongoose's built-in `id` virtual.
// The toJSON transform maps it back to `id` for API consumers.
// ---------------------------------------------------------------------------

const studentSchema = new Schema(
  {
    studentId: { type: String, required: true, unique: true, index: true },

    name: { type: String, required: true },
    campus: { type: String, required: true },
    batch: { type: String, required: true },
    gender: { type: String, required: true, enum: ["MALE", "FEMALE"] },
    address: { type: String, default: null },
    school: { type: String, required: true, default: "SOT" },

    // Enrichment fields — empty arrays for real records, populated for synthetic
    skills: { type: [String], default: [] },
    projects: { type: [studentProjectSchema], default: [] },
    interests: { type: [String], default: [] },
    publicLinks: { type: publicLinksSchema, default: () => ({}) },

    // Provenance — always required
    source: { type: sourceMetadataSchema, required: true },
  },
  {
    timestamps: true,
    toJSON: {
      transform(_doc: unknown, ret: Record<string, unknown>) {
        // Expose studentId as `id` and clean up Mongoose internals
        ret.id = ret.studentId;
        delete ret.studentId;
        delete ret._id;
        delete ret.__v;
        return ret;
      },
    },
  },
);

// ---------------------------------------------------------------------------
// Model
// ---------------------------------------------------------------------------

export const StudentModel = model("Student", studentSchema);

// ---------------------------------------------------------------------------
// Helper: convert a JSON record (with `id` field) to the Mongoose doc shape
// ---------------------------------------------------------------------------

/** Maps a Student-shaped object to the Mongoose document shape (id → studentId). */
export function toMongooseDoc(student: Student) {
  const { id, ...rest } = student;
  return { studentId: id, ...rest };
}
