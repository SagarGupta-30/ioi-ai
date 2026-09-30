/**
 * IOI AI — Normalized Student Data Model
 *
 * A single schema that represents both real PW IOI public records
 * and synthetic/demo records. Fields not available from the source
 * remain null/empty — never fabricated.
 */

// ---------------------------------------------------------------------------
// Source Metadata
// ---------------------------------------------------------------------------

/** Distinguishes where a record came from and how trustworthy it is. */
export interface SourceMetadata {
  /** Origin of the record. */
  type: "pwioi_public_api" | "synthetic";

  /** Visibility / trust level. */
  status: "public" | "demo";

  /**
   * URL or identifier for the originating data source.
   * For public records: the API endpoint used.
   * For synthetic records: "synthetic-generator" or similar label.
   */
  origin: string;

  /** ISO-8601 timestamp of when this record was ingested/created. */
  ingestedAt: string;
}

// ---------------------------------------------------------------------------
// Sub-structures
// ---------------------------------------------------------------------------

/** A student project for demo/synthetic profiles. */
export interface StudentProject {
  title: string;
  description: string | null;
  url: string | null;
}

/** Public links a student may have. */
export interface PublicLinks {
  linkedin: string | null;
  github: string | null;
  portfolio: string | null;
}

// ---------------------------------------------------------------------------
// Core Student Model
// ---------------------------------------------------------------------------

export interface Student {
  /** UUID from PW IOI API, or a generated UUID for synthetic records. */
  id: string;

  /** Full name. Available from the public API. */
  name: string;

  /**
   * Campus location (e.g., "Bengaluru", "Pune").
   * Derived from the center context, not a direct student field.
   */
  campus: string;

  /**
   * Batch / graduation year (e.g., "24", "25").
   * Derived from the batch context, not a direct student field.
   */
  batch: string;

  /** "MALE" | "FEMALE". Available from the public API. */
  gender: "MALE" | "FEMALE";

  /**
   * Address string. Present in the API schema but currently always null.
   * If populated, expected format: "City, State".
   */
  address: string | null;

  /**
   * School identifier. Currently always "SOT" (School of Technology).
   * Derived from the API path, not a direct student field.
   */
  school: string;

  // -- Fields below are ONLY populated for synthetic/demo records ----------

  /** Technical or non-technical skills. Empty array if unknown. */
  skills: string[];

  /** Projects the student has worked on. Empty array if unknown. */
  projects: StudentProject[];

  /** Academic or personal interests. Empty array if unknown. */
  interests: string[];

  /** Public web links. All null if unknown. */
  publicLinks: PublicLinks;

  /** Provenance information — always present. */
  source: SourceMetadata;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Fields that are actually returned by the PW IOI public API. */
export type PublicApiStudentFields = Pick<
  Student,
  "id" | "name" | "gender" | "address"
>;

/** Creates a Student from raw PW IOI API data + request context. */
export function fromPublicApi(
  raw: PublicApiStudentFields,
  campus: string,
  batch: string,
  apiEndpoint: string,
): Student {
  return {
    id: raw.id,
    name: raw.name,
    campus,
    batch,
    gender: raw.gender,
    address: raw.address,
    school: "SOT",
    skills: [],
    projects: [],
    interests: [],
    publicLinks: { linkedin: null, github: null, portfolio: null },
    source: {
      type: "pwioi_public_api",
      status: "public",
      origin: apiEndpoint,
      ingestedAt: new Date().toISOString(),
    },
  };
}
