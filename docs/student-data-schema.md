# Student Data Schema

Proposed internal data schema for IOI AI, based on fields actually discovered in the PW IOI public API.

## Source-to-Internal Field Mapping

### Center Schema

| Source Field | Source Type | Internal Field | Internal Type | Notes |
|-------------|-------------|----------------|---------------|-------|
| `id` | UUID string | `centerId` | string | Primary key from API |
| `name` | string | `centerName` | string | e.g., "IOI Bengaluru" |
| `location` | string | `campus` | string | City name, e.g., "Bengaluru" |
| `code` | integer | `centerCode` | number | Numeric campus code |

### Batch Schema

| Source Field | Source Type | Internal Field | Internal Type | Notes |
|-------------|-------------|----------------|---------------|-------|
| `id` | UUID string | `batchId` | string | Primary key from API |
| `name` | string | `batchName` | string | Graduation year, e.g., "24" |

### Student Schema

| Source Field | Source Type | Internal Field | Internal Type | Notes |
|-------------|-------------|----------------|---------------|-------|
| `id` | UUID string | `studentId` | string | Primary key from API |
| `name` | string | `name` | string | Full name |
| `address` | string \| null | `address` | string \| null | Always null in current data |
| `gender` | string | `gender` | `"MALE"` \| `"FEMALE"` | Enum |
| *(derived)* | — | `campus` | string | Derived from center context |
| *(derived)* | — | `batch` | string | Derived from batch context |
| *(derived)* | — | `school` | string | Always `"SOT"` for now |

## Normalized Internal Schema

### `Center`

```typescript
interface Center {
  centerId: string;      // UUID from API
  centerName: string;    // "IOI Bengaluru"
  campus: string;        // "Bengaluru"
  centerCode: number;    // 1
  school: string;        // "SOT"
}
```

### `Batch`

```typescript
interface Batch {
  batchId: string;       // UUID from API
  batchName: string;     // "24"
  centerId: string;      // FK to Center
}
```

### `Student`

```typescript
interface Student {
  studentId: string;     // UUID from API
  name: string;          // "Aarushi Mandloi"
  gender: "MALE" | "FEMALE";
  address: string | null;
  // Denormalized context fields
  campus: string;        // "Bengaluru" (from Center)
  batch: string;         // "24" (from Batch)
  school: string;        // "SOT"
}
```

## Important Notes

1. **No invented fields.** This schema contains only fields that exist in the public API or are directly derivable from the request context (campus, batch, school).

2. **`address` caveat.** The field exists in the API response schema but has been observed as `null` across all tested campus/batch combinations. The frontend JS contains parsing logic to split it into city/state, suggesting it may be populated in the future.

3. **No LinkedIn/GitHub.** The frontend hardcodes LinkedIn URLs to `https://www.linkedin.com/` — there are no per-student social links in the API data.

4. **Gender values.** Observed values are `"MALE"` and `"FEMALE"` (uppercase strings).

5. **Hierarchical structure.** Students are not globally queryable — they must be fetched per center+batch combination. The schema should preserve this relationship.

## Future Schema Extensions

If additional data sources are integrated later, the schema could be extended with:

```typescript
// NOT from current API — for future use only
interface StudentExtended extends Student {
  program?: string;        // e.g., "B.Tech CSE"
  skills?: string[];
  projects?: string[];
  githubUrl?: string;
  linkedinUrl?: string;
  bio?: string;
  isSynthetic: boolean;   // Flag for synthetic/demo data
}
```

These fields would be populated from:
- Supplemental public sources (if discovered)
- Synthetic/demo data (clearly labeled)
