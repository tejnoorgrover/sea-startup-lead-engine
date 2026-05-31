# Architecture

The SEA Startup Lead Engine has five layers:

1. **Discovery**: Source new startups from approved sources such as startup databases, VC portfolio pages, accelerator batches, public company websites, and news/RSS feeds.
2. **Enrichment**: Add country, segment, founder, website, source URL, funding stage, trigger event, and business contact fields.
3. **Scoring**: Rank each startup by ICP fit, payment relevance, growth signal, SEA strategic value, contactability, and timing trigger.
4. **Sales Intelligence**: Generate a concise sales-call brief and suggested pitch angle.
5. **Activation**: Display leads in the dashboard and export CSV for CRM upload.

The MVP uses sample CSV data. A production version would replace static CSV inputs with API connectors, scheduled jobs, contact verification, CRM integration, and compliance workflows.
