def generate_sales_insight(lead: dict) -> str:
    """Generate a short sales-call brief from trigger and payment signals."""
    startup = lead.get("startup_name", "this startup")
    segment = lead.get("segment", "their segment")
    payment_signal = lead.get("payment_signal", "payment operations")
    return (
        f"{startup} is active in {segment}. Lead with how Razorpay can help improve "
        f"{payment_signal.lower()} while they scale across SEA."
    )
