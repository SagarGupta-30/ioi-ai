# PW IOI Student Data Source

## Source

- **Website URL:** https://www.pwioi.club/students/sot
- **API Base URL:** https://api.pwioi.club
- **School:** School of Technology (SOT)

## Data Loading Mechanism

The PW IOI student directory is a **Next.js application** that loads student data entirely through **client-side JavaScript API calls**. No student data is embedded in the initial HTML.

### How it works:

1. The initial HTML page loads with a navigation bar, header text ("School of Technology"), and a **loading spinner** — but zero student data.
2. The page JavaScript (`page-*.js` chunk) executes and makes three sequential API calls:
   - **Step 1:** Fetch available campus centers (e.g., Bengaluru, Pune, Noida, Lucknow)
   - **Step 2:** After the user selects a campus, fetch available batches for that campus
   - **Step 3:** After the user selects a batch, fetch students for that campus + batch combination
3. Student cards are rendered client-side with avatar images assigned based on gender (male/female avatar pools hosted on ImageKit).
4. LinkedIn links on the cards are **hardcoded** to `https://www.linkedin.com/` (not per-student LinkedIn profiles).

### Key technical details:
- **Framework:** Next.js (App Router, server-rendered shell + client-side data fetching)
- **API base:** `https://api.pwioi.club`
- **No authentication** required for these public endpoints
- **No pagination** at the API level — all students for a campus+batch are returned in a single response
- **Client-side pagination** — the frontend paginates at 12 students per page using local array slicing

## API / Data Endpoint

### Endpoint 1: Get Centers (Campuses)

```
GET https://api.pwioi.club/api/schools/SOT/centers
```

**Response:**
```json
{
  "success": true,
  "count": 4,
  "data": [
    {
      "id": "3f9ce180-a44c-41bb-8643-801d7b7a2d02",
      "name": "IOI Pune",
      "location": "Pune",
      "code": 4
    },
    {
      "id": "4a174eab-ccd1-42db-9a49-bfedf599fe07",
      "name": "IOI Bengaluru",
      "location": "Bengaluru",
      "code": 1
    },
    {
      "id": "615e7747-32f7-4533-8866-0c06dac1e3ee",
      "name": "IOI Lucknow",
      "location": "Lucknow",
      "code": 7
    },
    {
      "id": "ae0c04d1-0143-4ecc-9d14-06001ea62bfa",
      "name": "IOI Noida",
      "location": "Noida",
      "code": 3
    }
  ]
}
```

### Endpoint 2: Get Batches for a Center

```
GET https://api.pwioi.club/api/batches/public/SOT/{centerId}
```

**Parameters:**
| Parameter | Location | Required | Description |
|-----------|----------|----------|-------------|
| `centerId` | URL path | Yes | UUID of the campus center |

**Example:** `GET /api/batches/public/SOT/4a174eab-ccd1-42db-9a49-bfedf599fe07`

**Response:**
```json
{
  "success": true,
  "count": 4,
  "data": [
    { "id": "398a4237-dba3-4fde-960a-0691a314d4b6", "name": "26" },
    { "id": "7c6b7304-16fe-436b-90cb-196acb7ae8bb", "name": "25" },
    { "id": "dedd26c7-30c0-4283-a7bf-9da58eafaf1e", "name": "24" },
    { "id": "65c5d14b-31ee-4b0b-a75e-627742150cd3", "name": "23" }
  ]
}
```

**Batches per campus (observed):**

| Campus | Batches |
|--------|---------|
| Bengaluru | 26, 25, 24, 23 |
| Pune | 26, 25 |
| Noida | 26, 25 |
| Lucknow | 26, 25 |

### Endpoint 3: Get Students for a Center + Batch

```
GET https://api.pwioi.club/api/students/public/SOT/{centerId}/{batchId}
```

**Parameters:**
| Parameter | Location | Required | Description |
|-----------|----------|----------|-------------|
| `centerId` | URL path | Yes | UUID of the campus center |
| `batchId` | URL path | Yes | UUID of the batch |

**Example:** `GET /api/students/public/SOT/4a174eab-ccd1-42db-9a49-bfedf599fe07/dedd26c7-30c0-4283-a7bf-9da58eafaf1e`

**Response:**
```json
{
  "success": true,
  "count": 142,
  "data": [
    {
      "id": "119e4b7e-7052-4acd-844b-c1ac49a67824",
      "name": "Aarushi Mandloi",
      "address": null,
      "gender": "FEMALE"
    },
    {
      "id": "b8f85d5d-e8cf-4e92-9da0-704c16d48b9a",
      "name": "Abhi Rai",
      "address": null,
      "gender": "MALE"
    }
  ]
}
```

## Publicly Available Fields

### Center Fields

| Field | Available | Type | Notes |
|-------|-----------|------|-------|
| `id` | ✅ | UUID string | Unique center identifier |
| `name` | ✅ | string | Full center name (e.g., "IOI Bengaluru") |
| `location` | ✅ | string | City name (e.g., "Bengaluru") |
| `code` | ✅ | integer | Numeric code for the center |

### Batch Fields

| Field | Available | Type | Notes |
|-------|-----------|------|-------|
| `id` | ✅ | UUID string | Unique batch identifier |
| `name` | ✅ | string | Batch/graduation year (e.g., "24", "25") |

### Student Fields

| Field | Available | Type | Notes |
|-------|-----------|------|-------|
| `id` | ✅ | UUID string | Unique student identifier |
| `name` | ✅ | string | Full name |
| `address` | ⚠️ | string \| null | Present in schema but **always null** in observed data |
| `gender` | ✅ | string | "MALE" or "FEMALE" |

### Fields NOT present in the public API

| Field | Status |
|-------|--------|
| email | ❌ Not available |
| phone | ❌ Not available |
| program/major | ❌ Not available |
| skills | ❌ Not available |
| projects | ❌ Not available |
| GitHub URL | ❌ Not available |
| LinkedIn URL | ❌ Not available (hardcoded to `https://www.linkedin.com/` in frontend) |
| profile photo | ❌ Not available (frontend assigns generic avatars by gender) |
| enrollment ID | ❌ Not available |
| CGPA / grades | ❌ Not available |

## Pagination / Filtering

### API-level Pagination
**None.** The API returns all students for a given center+batch in a single response. No `page`, `limit`, `offset`, or cursor parameters are accepted.

### Client-side Pagination
The frontend implements client-side pagination:
- Page size: **12 students per page**
- Uses array slicing: `students.slice((page-1)*12, page*12)`
- Renders pagination buttons with prev/next and page numbers

### Filtering
Filtering is done through the **hierarchical URL path** structure:
1. **School** → hardcoded as `SOT` (School of Technology)
2. **Campus/Center** → selected via UUID
3. **Batch** → selected via UUID

There is no text search, name filter, or gender filter at the API level.

## Example Response

A small sanitized example from the Bengaluru campus, batch 24:

```json
{
  "success": true,
  "count": 142,
  "data": [
    {
      "id": "119e4b7e-7052-4acd-844b-c1ac49a67824",
      "name": "Aarushi Mandloi",
      "address": null,
      "gender": "FEMALE"
    },
    {
      "id": "b8f85d5d-e8cf-4e92-9da0-704c16d48b9a",
      "name": "Abhi Rai",
      "address": null,
      "gender": "MALE"
    },
    {
      "id": "193afc04-b5ef-4e90-967a-d69177675e05",
      "name": "Abhishek Choudhary",
      "address": null,
      "gender": "MALE"
    }
  ]
}
```

## Data Usage Considerations

1. **Public data only.** All data documented here is obtained from publicly accessible API endpoints that require no authentication. The same data is visible to any visitor of the PW IOI website.

2. **Demo project.** IOI AI is a demonstration project. Student data will be used only to populate a knowledge base for educational/demo purposes.

3. **No sensitive data.** The public API does not expose emails, phone numbers, grades, enrollment IDs, or any sensitive personal information. Only names and gender are returned.

4. **Address field.** The `address` field exists in the schema but is consistently `null` across all observed responses (tested across multiple campuses and batches). If it were populated, it would contain comma-separated city/state information (based on the frontend parsing logic).

5. **Supplemental data.** Since the public API provides limited fields (name, gender only), the project may use synthetic/demo data to simulate richer profiles for demonstration purposes. Any synthetic data will be clearly labeled as non-real.

6. **No bulk scraping.** The project will make minimal, respectful API calls for data collection. The entire student list for a campus+batch is returned in a single response, so large numbers of requests are not necessary.
