# Profiles API

A REST API that aggregates data from Genderize, Agify, and Nationalize APIs, stores profiles in PostgreSQL, and exposes endpoints to manage them.

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL (Neon)
- **Deployment**: Vercel

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/profiles` | Create a profile by name |
| GET | `/api/profiles` | List all profiles (filterable) |
| GET | `/api/profiles/{id}` | Get a single profile |
| DELETE | `/api/profiles/{id}` | Delete a profile |

### Filters for GET /api/profiles

- `gender` — e.g. `?gender=male`
- `country_id` — e.g. `?country_id=NG`
- `age_group` — e.g. `?age_group=adult`

Filters are case-insensitive and combinable.

## Local Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variable
export DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require

# Run the server
uvicorn main:app --reload
```

## Deployment (Vercel + Neon)

1. Push repo to GitHub
2. Go to [vercel.com](https://vercel.com) → New Project → Import your repo
3. Add `DATABASE_URL` as an environment variable (from your Neon project dashboard)
4. Deploy — Vercel picks up `vercel.json` automatically

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string from Neon |