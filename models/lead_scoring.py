ICP_SEGMENTS = {
    "E-commerce SaaS": 25,
    "D2C Commerce": 23,
    "Marketplace": 25,
    "Fintech Infrastructure": 24,
    "SaaS": 22,
    "Travel Marketplace": 20,
}

PAYMENT_KEYWORDS = {
    "checkout": 8,
    "subscription": 8,
    "recurring": 8,
    "payout": 8,
    "payouts": 8,
    "marketplace": 6,
    "cross-border": 8,
    "reconciliation": 8,
    "refund": 5,
    "billing": 7,
}

STRATEGIC_COUNTRIES = {
    "Singapore": 10,
    "Indonesia": 10,
    "Vietnam": 8,
    "Philippines": 8,
    "Malaysia": 8,
    "Thailand": 7,
}


def score_lead(row: dict) -> int:
    """Return a simple transparent score out of 100 for a startup lead."""
    segment = row.get("segment", "")
    country = row.get("country", "")
    trigger = str(row.get("trigger", "")).lower()
    payment_signal = str(row.get("payment_signal", "")).lower()
    email = row.get("business_email")
    phone = row.get("business_phone")

    score = 0

    # ICP fit: max 25
    score += ICP_SEGMENTS.get(segment, 12)

    # Payment relevance: max 25
    payment_score = 0
    combined_text = f"{payment_signal} {trigger}"
    for keyword, weight in PAYMENT_KEYWORDS.items():
        if keyword in combined_text:
            payment_score += weight
    score += min(payment_score, 25)

    # Growth signal: max 20
    growth_terms = ["raised", "funding", "hiring", "launched", "expanding", "announced"]
    growth_score = sum(5 for term in growth_terms if term in trigger)
    score += min(growth_score, 20)

    # SEA strategic value: max 10
    score += STRATEGIC_COUNTRIES.get(country, 5)

    # Contactability: max 10
    if email and phone:
        score += 10
    elif email:
        score += 7
    elif phone:
        score += 5

    # Timing trigger: max 10
    if trigger:
        score += 10

    return min(score, 100)


def priority_from_score(score: int) -> str:
    if score >= 80:
        return "High"
    if score >= 65:
        return "Medium"
    return "Low"
