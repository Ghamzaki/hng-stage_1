from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from typing import Optional
import uuid6
from datetime import datetime, timezone

from database import get_pool
from models import ProfileRequest, ProfileFull, ProfileSummary
from services.external import fetch_all
from services.classifier import get_age_group, get_top_country
from services.parser import parse_query

router = APIRouter(prefix="/api/profiles")

VALID_SORT_FIELDS = {"age", "created_at", "gender_probability"}
VALID_ORDERS = {"asc", "desc"}


def _format_row(row: dict) -> dict:
    """Normalize a DB row: format created_at as ISO string."""
    d = dict(row)
    if isinstance(d.get("created_at"), datetime):
        d["created_at"] = d["created_at"].strftime("%Y-%m-%dT%H:%M:%SZ")
    return d


async def _query_profiles(
    conn,
    gender: Optional[str] = None,
    age_group: Optional[str] = None,
    country_id: Optional[str] = None,
    min_age: Optional[int] = None,
    max_age: Optional[int] = None,
    min_gender_probability: Optional[float] = None,
    min_country_probability: Optional[float] = None,
    sort_by: Optional[str] = "created_at",
    order: Optional[str] = "asc",
    page: int = 1,
    limit: int = 10,
):
    """Shared query builder used by both GET all and NL search."""
    conditions = ["1=1"]
    params = []
    i = 1

    if gender:
        conditions.append(f"LOWER(gender) = ${i}")
        params.append(gender.lower())
        i += 1
    if age_group:
        conditions.append(f"LOWER(age_group) = ${i}")
        params.append(age_group.lower())
        i += 1
    if country_id:
        conditions.append(f"UPPER(country_id) = ${i}")
        params.append(country_id.upper())
        i += 1
    if min_age is not None:
        conditions.append(f"age >= ${i}")
        params.append(min_age)
        i += 1
    if max_age is not None:
        conditions.append(f"age <= ${i}")
        params.append(max_age)
        i += 1
    if min_gender_probability is not None:
        conditions.append(f"gender_probability >= ${i}")
        params.append(min_gender_probability)
        i += 1
    if min_country_probability is not None:
        conditions.append(f"country_probability >= ${i}")
        params.append(min_country_probability)
        i += 1

    where = " AND ".join(conditions)

    # Validate sort params
    sort_col = sort_by if sort_by in VALID_SORT_FIELDS else "created_at"
    sort_dir = order.upper() if order in VALID_ORDERS else "ASC"

    # Total count
    total = await conn.fetchval(f"SELECT COUNT(*) FROM profiles WHERE {where}", *params)

    # Paginated results
    offset = (page - 1) * limit
    rows = await conn.fetch(
        f"""
        SELECT id, name, gender, gender_probability, age, age_group,
               country_id, country_name, country_probability, created_at
        FROM profiles
        WHERE {where}
        ORDER BY {sort_col} {sort_dir}
        LIMIT ${i} OFFSET ${i+1}
        """,
        *params, limit, offset,
    )

    return total, [ProfileSummary(**_format_row(row)) for row in rows]


# POST /api/profiles

@router.post("", status_code=201)
async def create_profile(body: ProfileRequest):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Missing or empty name")

    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT * FROM profiles WHERE name = $1", name.lower()
        )
        if existing:
            return {
                "status": "success",
                "message": "Profile already exists",
                "data": ProfileFull(**_format_row(existing)),
            }

    gender_data, age_data, nation_data = await fetch_all(name)

    age_group = get_age_group(age_data["age"])
    country_id, country_probability = get_top_country(nation_data["country"])

    # Resolve country name from seed country map (fallback to code)
    from services.parser import COUNTRY_MAP
    country_name_map = {v: k.title() for k, v in COUNTRY_MAP.items()}
    country_name = country_name_map.get(country_id, country_id)

    profile = {
        "id": str(uuid6.uuid7()),
        "name": name.lower(),
        "gender": gender_data["gender"],
        "gender_probability": gender_data["probability"],
        "age": age_data["age"],
        "age_group": age_group,
        "country_id": country_id,
        "country_name": country_name,
        "country_probability": country_probability,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO profiles
                (id, name, gender, gender_probability, age, age_group,
                 country_id, country_name, country_probability, created_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
        """,
            profile["id"], profile["name"], profile["gender"],
            profile["gender_probability"], profile["age"], profile["age_group"],
            profile["country_id"], profile["country_name"],
            profile["country_probability"],
            datetime.now(timezone.utc).replace(tzinfo=None),
        )

    return {"status": "success", "data": ProfileFull(**profile)}


# GET /api/profiles/search

@router.get("/search")
async def search_profiles(
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
):
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Missing or empty query")

    filters = parse_query(q.strip())
    if filters is None:
        return {"status": "error", "message": "Unable to interpret query"}

    pool = await get_pool()
    async with pool.acquire() as conn:
        total, data = await _query_profiles(conn, page=page, limit=limit, **filters)

    return {
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total,
        "data": data,
    }


# GET /api/profiles

@router.get("")
async def get_all_profiles(
    gender: Optional[str] = Query(None),
    age_group: Optional[str] = Query(None),
    country_id: Optional[str] = Query(None),
    min_age: Optional[int] = Query(None),
    max_age: Optional[int] = Query(None),
    min_gender_probability: Optional[float] = Query(None),
    min_country_probability: Optional[float] = Query(None),
    sort_by: Optional[str] = Query("created_at"),
    order: Optional[str] = Query("asc"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
):
    # Validate sort params early
    if sort_by and sort_by not in VALID_SORT_FIELDS:
        raise HTTPException(status_code=400, detail="Invalid query parameters")
    if order and order not in VALID_ORDERS:
        raise HTTPException(status_code=400, detail="Invalid query parameters")

    pool = await get_pool()
    async with pool.acquire() as conn:
        total, data = await _query_profiles(
            conn,
            gender=gender,
            age_group=age_group,
            country_id=country_id,
            min_age=min_age,
            max_age=max_age,
            min_gender_probability=min_gender_probability,
            min_country_probability=min_country_probability,
            sort_by=sort_by,
            order=order,
            page=page,
            limit=limit,
        )

    return {
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total,
        "data": data,
    }


# GET /api/profiles/{id}

@router.get("/{profile_id}")
async def get_profile(profile_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM profiles WHERE id = $1", profile_id
        )
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"status": "success", "data": ProfileFull(**_format_row(row))}


# DELETE /api/profiles/{id}

@router.delete("/{profile_id}", status_code=204)
async def delete_profile(profile_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM profiles WHERE id = $1", profile_id
        )
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Profile not found")
    return Response(status_code=204)