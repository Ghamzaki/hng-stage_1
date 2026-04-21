import re
from typing import Optional

# All country names found in the dataset + common aliases
COUNTRY_MAP = {
    "algeria": "DZ",
    "angola": "AO",
    "australia": "AU",
    "benin": "BJ",
    "botswana": "BW",
    "brazil": "BR",
    "burkina faso": "BF",
    "burundi": "BI",
    "cameroon": "CM",
    "canada": "CA",
    "cape verde": "CV",
    "central african republic": "CF",
    "chad": "TD",
    "china": "CN",
    "comoros": "KM",
    "ivory coast": "CI",
    "cote d'ivoire": "CI",
    "côte d'ivoire": "CI",
    "dr congo": "CD",
    "democratic republic of congo": "CD",
    "drc": "CD",
    "djibouti": "DJ",
    "egypt": "EG",
    "equatorial guinea": "GQ",
    "eritrea": "ER",
    "eswatini": "SZ",
    "swaziland": "SZ",
    "ethiopia": "ET",
    "france": "FR",
    "gabon": "GA",
    "gambia": "GM",
    "germany": "DE",
    "ghana": "GH",
    "guinea": "GN",
    "guinea-bissau": "GW",
    "india": "IN",
    "japan": "JP",
    "kenya": "KE",
    "lesotho": "LS",
    "liberia": "LR",
    "libya": "LY",
    "madagascar": "MG",
    "malawi": "MW",
    "mali": "ML",
    "mauritania": "MR",
    "mauritius": "MU",
    "morocco": "MA",
    "mozambique": "MZ",
    "namibia": "NA",
    "niger": "NE",
    "nigeria": "NG",
    "republic of the congo": "CG",
    "congo": "CG",
    "rwanda": "RW",
    "senegal": "SN",
    "seychelles": "SC",
    "sierra leone": "SL",
    "somalia": "SO",
    "south africa": "ZA",
    "south sudan": "SS",
    "sudan": "SD",
    "sao tome and principe": "ST",
    "são tomé and príncipe": "ST",
    "tanzania": "TZ",
    "togo": "TG",
    "tunisia": "TN",
    "uganda": "UG",
    "united kingdom": "GB",
    "uk": "GB",
    "britain": "GB",
    "united states": "US",
    "usa": "US",
    "america": "US",
    "western sahara": "EH",
    "zambia": "ZM",
    "zimbabwe": "ZW",
}

# All valid 2-letter codes for direct code matching
VALID_CODES = set(COUNTRY_MAP.values())


def parse_query(q: str) -> Optional[dict]:
    """
    Parse a plain English query into filter parameters.
    Returns a dict of filters, or None if nothing could be interpreted.

    Supported mappings:
    - Gender: male/males/man/men → gender=male
              female/females/woman/women/lady/ladies → gender=female
    - Age descriptors: young → min_age=16, max_age=24
    - Age groups: child/children, teenager/teen/teens, adult/adults, senior/seniors/elderly/old
    - Numeric age: above/over/older than X → min_age=X
                   below/under/younger than X → max_age=X
                   between X and Y → min_age=X, max_age=Y
    - Country: from/in [country name or 2-letter code]
    """
    text = q.lower().strip()

    if not text:
        return None

    filters = {}

    # --- Gender ---
    if re.search(r'\b(males?|men|man)\b', text):
        filters["gender"] = "male"
    elif re.search(r'\b(females?|women|woman|lady|ladies)\b', text):
        filters["gender"] = "female"

    # --- "young" keyword → ages 16–24 (parsing only, not a stored group) ---
    if re.search(r'\byoung\b', text):
        filters["min_age"] = 16
        filters["max_age"] = 24

    # --- Age groups ---
    if re.search(r'\b(children|child|kids?)\b', text):
        filters["age_group"] = "child"
    elif re.search(r'\b(teenagers?|teens?|adolescents?)\b', text):
        filters["age_group"] = "teenager"
    elif re.search(r'\badults?\b', text):
        filters["age_group"] = "adult"
    elif re.search(r'\b(seniors?|elderly|old people|old)\b', text):
        filters["age_group"] = "senior"

    # --- Numeric age: between X and Y ---
    between = re.search(r'\bbetween\s+(\d+)\s+and\s+(\d+)\b', text)
    if between:
        filters["min_age"] = int(between.group(1))
        filters["max_age"] = int(between.group(2))
    else:
        # above / over / older than X
        above = re.search(r'\b(?:above|over|older\s+than)\s+(\d+)\b', text)
        if above:
            filters["min_age"] = int(above.group(1))

        # below / under / younger than X
        below = re.search(r'\b(?:below|under|younger\s+than)\s+(\d+)\b', text)
        if below:
            filters["max_age"] = int(below.group(1))

    # --- Country: "from X" or "in X" ---
    # Try multi-word country names first (longest match), then 2-letter codes
    country_match = re.search(r'\b(?:from|in)\s+([a-z][a-z\s\'\-\.]+?)(?:\s+(?:who|that|with|and|above|below|over|under)\b|$)', text)
    if country_match:
        raw = country_match.group(1).strip()
        # Try exact match first, then partial
        code = COUNTRY_MAP.get(raw)
        if not code:
            # Try matching any known country name that appears in the raw string
            for name, c in sorted(COUNTRY_MAP.items(), key=lambda x: -len(x[0])):
                if name in raw:
                    code = c
                    break
        if code:
            filters["country_id"] = code
    else:
        # Try bare 2-letter country code anywhere in query (e.g. "NG males")
        code_match = re.search(r'\b([A-Z]{2})\b', q)  # use original case
        if code_match and code_match.group(1) in VALID_CODES:
            filters["country_id"] = code_match.group(1)

    if not filters:
        return None

    return filters