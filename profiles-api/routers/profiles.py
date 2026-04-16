from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from typing import Optional
import uuid6
from datetime import datetime, timezone

from app.database import get_pool
from app.models import ProfileRequest, ProfileFull, ProfileSummary
from app.services.external import fetch_all
from app.services.classifier import get_age_group, get_top_country

router = APIRouter(prefix="/api/profiles")


@router.post("", status_code=201)
async def create_profile(body: ProfileRequest):
    name = body.name.strip()

    if not name:
        raise HTTPException(status_code=400, detail="Missing or empty name")

    pool = await get_pool()

    # Check for existing profile (idempotency)
    async with pool.acquire() as conn:
        existing = await conn.fetchrow("SELECT * FROM profiles WHERE name = $1", name.lower())

    if existing:
        return {
            "status": "success",
            "message": "Profile already exists",
            "data": ProfileFull(**dict(existing)),
        }

    # Fetch from all 3 external APIs concurrently
    gender_data, age_data, nation_data = await fetch_all(name)

    # Classify
    age_group = get_age_group(age_data["age"])
    country_id, country_probability = get_top_country(nation_data["country"])

    profile = {
        "id": str(uuid6.uuid7()),
        "name": name.lower(),
        "gender": gender_data["gender"],
        "gender_probability": gender_data["probability"],
        "sample_size": gender_data["count"],
        "age": age_data["age"],
        "age_group": age_group,
        "country_id": country_id,
        "country_probability": country_probability,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO profiles (id, name, gender, gender_probability, sample_size,
                                  age, age_group, country_id, country_probability, created_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
        """,
            profile["id"], profile["name"], profile["gender"],
            profile["gender_probability"], profile["sample_size"],
            profile["age"], profile["age_group"], profile["country_id"],
            profile["country_probability"], profile["created_at"],
        )

    return {"status": "success", "data": ProfileFull(**profile)}


@router.get("")
async def get_all_profiles(
    gender: Optional[str] = Query(None),
    country_id: Optional[str] = Query(None),
    age_group: Optional[str] = Query(None),
):
    pool = await get_pool()

    query = "SELECT id, name, gender, age, age_group, country_id FROM profiles WHERE 1=1"
    params = []
    i = 1

    if gender:
        query += f" AND LOWER(gender) = ${i}"
        params.append(gender.lower())
        i += 1
    if country_id:
        query += f" AND LOWER(country_id) = ${i}"
        params.append(country_id.lower())
        i += 1
    if age_group:
        query += f" AND LOWER(age_group) = ${i}"
        params.append(age_group.lower())
        i += 1

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)

    data = [ProfileSummary(**dict(row)) for row in rows]
    return {"status": "success", "count": len(data), "data": data}


@router.get("/{profile_id}")
async def get_profile(profile_id: str):
    pool = await get_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM profiles WHERE id = $1", profile_id)

    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")

    return {"status": "success", "data": ProfileFull(**dict(row))}


@router.delete("/{profile_id}", status_code=204)
async def delete_profile(profile_id: str):
    pool = await get_pool()

    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM profiles WHERE id = $1", profile_id)

    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Profile not found")

    return Response(status_code=204)