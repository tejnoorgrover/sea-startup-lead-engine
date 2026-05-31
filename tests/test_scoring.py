from models.lead_scoring import priority_from_score, score_lead


def test_score_lead_high_priority():
    lead = {
        "segment": "Marketplace",
        "country": "Singapore",
        "trigger": "Raised seed funding and expanding seller base",
        "payment_signal": "Split payments and vendor payouts",
        "business_email": "hello@example.com",
        "business_phone": "+65-5555-0101",
    }
    score = score_lead(lead)
    assert score >= 80
    assert priority_from_score(score) == "High"
