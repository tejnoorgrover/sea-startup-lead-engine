# Live Validated Startup Name Fix

This update fixes the issue where article headlines were appearing inside the `startup_name` column.

## What changed

- `startup_name` is now populated only when the app can extract a company name with high confidence.
- The full article/news headline is stored separately as `signal_title`.
- Low-confidence records are skipped instead of being shown as fake startup names.
- Dashboard now includes:
  - `startup_name`
  - `signal_title`
  - `founder_name`
  - `founder_email`
  - `business_email`
  - `business_phone`
  - `website`
  - `data_confidence`
  - `contact_enrichment_status`

## Contact handling

Founder emails are not guessed. The app shows public business emails only when found on official-looking company websites. In production, founder-level contact enrichment should come from compliant enrichment APIs, CRM-approved vendors, or official company pages.
