# Live Data Upgrade

This version turns the dashboard from a sample-data demo into a live public-signal dashboard.

## What is live now

- Pulls real startup/funding/launch signals from public Google News RSS searches.
- Covers Singapore, Indonesia, Vietnam, Malaysia, Thailand, and the Philippines.
- Infers segment, Razorpay angle, lead score, and priority from each headline.
- Stores source URL, source name, published date, data confidence, and verification date.
- Refreshes every 6 hours in Streamlit; users can also click **Refresh live data**.

## Important limitation

The live public RSS layer does not guess founder emails or phone numbers. Those should be added only through compliant enrichment methods:

- Official company websites/contact pages
- Licensed enrichment APIs
- Clearly published business contact details
- CRM-approved enrichment vendors

## Files changed

- `app/dashboard.py`
- `pipelines/live_discovery.py`
- `requirements.txt`
- `runtime.txt`

## Streamlit settings

Use:

- Branch: `main`
- Main file path: `app/dashboard.py`
- Python version: `3.11`
