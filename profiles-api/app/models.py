from pydantic import BaseModel


class ProfileRequest(BaseModel):
    name: str


class ProfileFull(BaseModel):
    id: str
    name: str
    gender: str
    gender_probability: float
    sample_size: int
    age: int
    age_group: str
    country_id: str
    country_probability: float
    created_at: str


class ProfileSummary(BaseModel):
    id: str
    name: str
    gender: str
    age: int
    age_group: str
    country_id: str