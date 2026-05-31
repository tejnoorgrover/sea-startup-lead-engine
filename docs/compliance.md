# Compliance Approach

The project should be compliance-first because the use case involves founder contact information.

## Principles

- Collect business contact information only.
- Store source URL and collection date for every field.
- Avoid unauthorized scraping of restricted platforms.
- Do not store personal phone numbers unless explicitly published for business use.
- Maintain suppression and opt-out lists.
- Verify emails before outreach.
- Add country-specific privacy logic before production deployment.

## Production Controls

- Suppression list checked before export.
- Source audit trail visible in dashboard.
- Contact confidence score.
- Last verified date.
- CRM export logs.
- Manual review for sensitive fields.
