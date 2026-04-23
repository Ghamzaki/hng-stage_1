# Insighta Labs — Demographic Intelligence API

A FastAPI + PostgreSQL REST API that stores demographic profiles and supports advanced filtering, sorting, pagination, and natural language querying.

## Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL (Neon free tier)
- **Deployment**: Vercel
- **HTTP client**: httpx (async)
- **UUID**: uuid6 (v7)

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/profiles` | Create a new profile via external APIs |
| GET | `/api/profiles` | List profiles with filters, sorting, pagination |
| GET | `/api/profiles/search` | Natural language profile search |
| GET | `/api/profiles/{id}` | Get a single profile by ID |
| DELETE | `/api/profiles/{id}` | Delete a profile |

---

## GET /api/profiles — Filters & Sorting

All query parameters are optional and combinable.

**Filters**

| Parameter | Type | Example |
|---|---|---|
| `gender` | string | `male` / `female` |
| `age_group` | string | `child` / `teenager` / `adult` / `senior` |
| `country_id` | string | `NG`, `KE`, `GH` |
| `min_age` | int | `25` |
| `max_age` | int | `40` |
| `min_gender_probability` | float | `0.9` |
| `min_country_probability` | float | `0.7` |

**Sorting**

| Parameter | Options | Default |
|---|---|---|
| `sort_by` | `age`, `created_at`, `gender_probability` | `created_at` |
| `order` | `asc`, `desc` | `asc` |

**Pagination**

| Parameter | Default | Max |
|---|---|---|
| `page` | `1` | — |
| `limit` | `10` | `50` |

**Example**
```
GET /api/profiles?gender=male&country_id=NG&min_age=25&sort_by=age&order=desc&page=1&limit=10
```

---

## GET /api/profiles/search — Natural Language Query

```
GET /api/profiles/search?q=young males from nigeria
```

### How Parsing Works

The parser uses **rule-based keyword matching and regex patterns** — no AI or LLMs involved. It scans the query string for known keywords and patterns, maps them to structured filters, then runs the same query engine as the standard GET endpoint.

### Supported Keywords & Mappings

**Gender**

| Query words | Maps to |
|---|---|
| `male`, `males`, `man`, `men` | `gender=male` |
| `female`, `females`, `woman`, `women`, `lady`, `ladies` | `gender=female` |

**Age descriptors**

| Query phrase | Maps to |
|---|---|
| `young` | `min_age=16`, `max_age=24` |
| `above X`, `over X`, `older than X` | `min_age=X` |
| `below X`, `under X`, `younger than X` | `max_age=X` |
| `between X and Y` | `min_age=X`, `max_age=Y` |

> Note: `young` is a parsing alias only — it is not a stored age group. It maps to ages 16–24.

**Age groups**

| Query words | Maps to |
|---|---|
| `child`, `children`, `kids` | `age_group=child` |
| `teenager`, `teen`, `teens`, `adolescent` | `age_group=teenager` |
| `adult`, `adults` | `age_group=adult` |
| `senior`, `seniors`, `elderly`, `old` | `age_group=senior` |

**Country**

Triggered by `from [country]` or `in [country]`. Supports:
- Full country names: `nigeria`, `south africa`, `côte d'ivoire`
- Common aliases: `uk` → GB, `usa` → US, `america` → US, `ivory coast` → CI
- Bare 2-letter ISO codes anywhere in query: `NG males`

### Example Mappings

| Query | Parsed filters |
|---|---|
| `young males from nigeria` | `gender=male`, `min_age=16`, `max_age=24`, `country_id=NG` |
| `females above 30` | `gender=female`, `min_age=30` |
| `people from angola` | `country_id=AO` |
| `adult males from kenya` | `gender=male`, `age_group=adult`, `country_id=KE` |
| `male and female teenagers above 17` | `age_group=teenager`, `min_age=17` |
| `senior women in south africa` | `gender=female`, `age_group=senior`, `country_id=ZA` |
| `between 20 and 40` | `min_age=20`, `max_age=40` |

### Uninterpretable Queries

If the parser cannot extract any filter from the query, it returns:
```json
{ "status": "error", "message": "Unable to interpret query" }
```

---

## Parser Limitations

1. **Ambiguous gender**: When both `male` and `female` keywords appear in the same query (e.g. "male and female teenagers"), the parser picks the first match (`male`). It does not support querying both genders simultaneously.

2. **`young` is not a stored age group**: It is a parsing alias for ages 16–24. Querying `age_group=young` directly on `/api/profiles` will return no results.

3. **No negation support**: Queries like "not from nigeria" or "excluding adults" are not parsed.

4. **No compound country logic**: "from nigeria or kenya" returns results for whichever country is matched first.

5. **Country name ambiguity**: `guinea` maps to Guinea (GN). `equatorial guinea` and `guinea-bissau` require the full name to be correctly identified.

6. **No probability filters**: The NL parser does not support `min_gender_probability` or `min_country_probability` — those are only available on the standard GET endpoint.

7. **No name-based search**: Searching by a person's name is not supported via the NL endpoint.

8. **Spelling errors**: Misspelled country names or keywords will not be matched.

---

## Setup & Local Development

```bash
# 1. Clone the repo
git clone https://github.com/Ghamzaki/hng-stage_1
cd hng-stage_1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create .env file
echo 'DATABASE_URL=postgresql://user:password@host/db?sslmode=require' > .env

# 4. Copy seed file to project root
cp /path/to/seed_profiles.json .

# 5. Run the server (seed runs automatically on startup)
uvicorn main:app --reload
```

## Deployment (Vercel + Neon)

1. Push repo to GitHub
2. Import project on [vercel.com](https://vercel.com)
3. Add environment variable: `DATABASE_URL` = your Neon connection string
4. Deploy — the seed runs automatically on first startup

## Error Responses

All errors follow this structure:
```json
{ "status": "error", "message": "<description>" }
```

| Code | Meaning |
|---|---|
| 400 | Missing or invalid parameter |
| 404 | Profile not found |
| 422 | Invalid parameter type |
| 502 | External API failure |
| 500 | Internal server error |