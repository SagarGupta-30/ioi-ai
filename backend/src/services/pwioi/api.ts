/**
 * PW IOI Public API Client
 *
 * Fetches centers, batches, and students from the PW IOI public REST API.
 * Pure data-fetching layer — no database logic here.
 */

const API_BASE = "https://api.pwioi.club";

// ---------------------------------------------------------------------------
// Response types (matching the public API shape)
// ---------------------------------------------------------------------------

export interface PwioiCenter {
  id: string;
  name: string;
  location: string;
  code: number;
}

export interface PwioiBatch {
  id: string;
  name: string;
}

export interface PwioiRawStudent {
  id: string;
  name: string;
  address: string | null;
  gender: "MALE" | "FEMALE";
}

interface ApiResponse<T> {
  success: boolean;
  count: number;
  data: T[];
}

// ---------------------------------------------------------------------------
// Fetch helpers
// ---------------------------------------------------------------------------

async function fetchJson<T>(url: string): Promise<ApiResponse<T>> {
  const res = await fetch(url);

  if (!res.ok) {
    throw new Error(`HTTP ${res.status} ${res.statusText} — ${url}`);
  }

  const json = (await res.json()) as ApiResponse<T>;

  if (!json.success) {
    throw new Error(`API returned success=false — ${url}`);
  }

  return json;
}

// ---------------------------------------------------------------------------
// Public API functions
// ---------------------------------------------------------------------------

/** Fetch all School of Technology centers (campuses). */
export async function fetchCenters(): Promise<PwioiCenter[]> {
  const res = await fetchJson<PwioiCenter>(`${API_BASE}/api/schools/SOT/centers`);
  return res.data;
}

/** Fetch all batches for a given center. */
export async function fetchBatches(centerId: string): Promise<PwioiBatch[]> {
  const res = await fetchJson<PwioiBatch>(
    `${API_BASE}/api/batches/public/SOT/${centerId}`,
  );
  return res.data;
}

/** Fetch all students for a given center + batch. */
export async function fetchStudents(
  centerId: string,
  batchId: string,
): Promise<PwioiRawStudent[]> {
  const res = await fetchJson<PwioiRawStudent>(
    `${API_BASE}/api/students/public/SOT/${centerId}/${batchId}`,
  );
  return res.data;
}

/** Build the full API endpoint URL for a student fetch (used for source.origin). */
export function studentEndpointUrl(centerId: string, batchId: string): string {
  return `${API_BASE}/api/students/public/SOT/${centerId}/${batchId}`;
}
