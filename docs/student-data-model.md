# Student Data Model

## Why Normalization Is Needed

The IOI AI project consumes data from two fundamentally different sources:

1. **Real public data** from the PW IOI public API — sparse, containing only `id`, `name`, `gender`, and a currently-null `address` field.
2. **Synthetic demo data** — richer profiles with skills, projects, and interests, generated to demonstrate RAG capabilities.

A single normalized schema lets the application treat both record types uniformly while preserving clear provenance about where each record came from and which fields are trustworthy.

## Source Fields from PW IOI Public API

The PW IOI public API (`https://api.pwioi.club`) returns these fields per student:

| API Field | Type | Status |
|-----------|------|--------|
| `id` | UUID string | Always present |
| `name` | string | Always present |
| `gender` | `"MALE"` \| `"FEMALE"` | Always present |
| `address` | string \| null | Present in schema, always `null` in observed data |

Additionally, **campus** and **batch** are derived from the API request path:
```
GET /api/students/public/SOT/{centerId}/{batchId}
```
The center's `location` field provides the campus name, and the batch's `name` field provides the batch year.

## Normalized Student Fields

| Field | Type | From Public API? | Notes |
|-------|------|------------------|-------|
| `id` | string | ✅ | UUID from API, or generated for synthetic |
| `name` | string | ✅ | Full name |
| `campus` | string | ✅ (derived) | From center context (e.g., "Bengaluru") |
| `batch` | string | ✅ (derived) | From batch context (e.g., "24") |
| `gender` | `"MALE"` \| `"FEMALE"` | ✅ | Directly from API |
| `address` | string \| null | ⚠️ Schema only | Always null in current data |
| `school` | string | ✅ (derived) | Always "SOT" currently |
| `skills` | string[] | ❌ | Synthetic/demo only |
| `projects` | StudentProject[] | ❌ | Synthetic/demo only |
| `interests` | string[] | ❌ | Synthetic/demo only |
| `publicLinks` | PublicLinks | ❌ | Synthetic/demo only |
| `source` | SourceMetadata | — | Always present, added by our system |

## Which Fields Are Available from the Real API

Only these fields come from the PW IOI public API:

- `id` — always present
- `name` — always present
- `gender` — always present
- `address` — exists in the response but is always `null`
- `campus` — derived from the center's `location` field
- `batch` — derived from the batch's `name` field
- `school` — derived from the URL path (`SOT`)

**Everything else** (`skills`, `projects`, `interests`, `publicLinks`) is **only populated for synthetic/demo records**.

## Which Fields Are Only for Synthetic/Demo Data

| Field | Why synthetic-only |
|-------|--------------------|
| `skills` | Not returned by the public API |
| `projects` | Not returned by the public API |
| `interests` | Not returned by the public API |
| `publicLinks` | LinkedIn URLs are hardcoded in the frontend, not per-student |

## Meaning of Null and Empty Fields

| Value | Meaning |
|-------|---------|
| `null` (string field) | The source does not provide this information |
| `[]` (array field) | The source does not provide this information (empty collection) |
| `{ linkedin: null, github: null, portfolio: null }` | No known public links |

**Critical rule:** A `null` or empty value means "unknown/not available from this source" — it does **not** mean the student lacks that attribute. We never fabricate values for real students.

## Data Provenance (Source Metadata)

Every record carries a `source` object:

```typescript
interface SourceMetadata {
  type: "pwioi_public_api" | "synthetic";
  status: "public" | "demo";
  origin: string;      // API URL or generator label
  ingestedAt: string;  // ISO-8601 timestamp
}
```

### Examples

**Real public record:**
```json
{
  "type": "pwioi_public_api",
  "status": "public",
  "origin": "https://api.pwioi.club/api/students/public/SOT/{centerId}/{batchId}",
  "ingestedAt": "2026-09-28T15:40:00.000Z"
}
```

**Synthetic demo record:**
```json
{
  "type": "synthetic",
  "status": "demo",
  "origin": "synthetic-generator",
  "ingestedAt": "2026-09-28T15:45:00.000Z"
}
```

This ensures any consumer can determine at a glance whether a record is real or fabricated.

## Structured Data vs. Future RAG Document Representation

| Aspect | Student (structured) | StudentDocument (RAG) |
|--------|---------------------|-----------------------|
| **Purpose** | Store and query student records | Feed text into embedding + retrieval pipeline |
| **Format** | Typed object with discrete fields | Flattened plain-text string + metadata dict |
| **Schema** | `Student` interface/dataclass | `StudentDocument` dataclass |
| **Usage** | API responses, filtering, display | Vector indexing, semantic search |

The `StudentDocument` is a **derived representation** — it is generated from a `Student` record by flattening its fields into a text paragraph. This separation keeps the structured data clean and the RAG pipeline flexible.

```
Student (structured)  →  StudentDocument (text)  →  Embedding (future)  →  Vector Store (future)
```

The RAG service's `StudentDocument.from_student()` handles the conversion. Embedding and vector storage are **not implemented yet**.

## Implementation Locations

| Artifact | Path |
|----------|------|
| TypeScript types | `backend/src/models/student.ts` |
| Python dataclasses | `rag-service/app/models.py` |
| Public example | `data/raw/example-public-student.json` |
| Synthetic example | `data/synthetic/example-student.json` |
