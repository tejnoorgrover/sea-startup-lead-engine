# SEA Startup Lead Engine

A GitHub-ready case study project for building a daily **lead generation and augmentation dashboard** for Southeast Asian startups.

This project is designed for a Director of Marketing case study. It shows how Razorpay could identify high-fit SEA startups, enrich them with founder/company context, score their payment relevance, and create sales-call insights.

---

## 1. Business Objective

Build a daily revenue intelligence engine that answers:

> Which SEA startups should Razorpay sales contact today, why now, and what should the sales team say?

This is not just a scraper. It is a pipeline engine that combines discovery, enrichment, lead scoring, compliance, and sales enablement.

---

## 2. What the Dashboard Shows

The Streamlit dashboard includes:

- Daily startup leads
- Country and segment filters
- Lead score and priority band
- Founder and business contact fields
- Trigger insights for sales calls
- Razorpay pitch angle
- CRM-ready CSV export
- Compliance/source audit fields

---

## 3. Target ICP

The first version prioritizes SEA startups that are more likely to need payments infrastructure:

- E-commerce and D2C brands
- SaaS businesses with subscription or cross-border needs
- Marketplaces requiring seller payouts or split payments
- Fintech-adjacent startups
- Recently funded or fast-hiring startups
- India-SEA corridor companies

---

## 4. Demo Screenshot

Run the app locally to view the dashboard:

```bash
streamlit run app/dashboard.py
```

---

## 5. Project Architecture

```text
Data Sources
   ↓
Discovery Connectors
   ↓
Raw Startup Records
   ↓
Deduplication + Normalization
   ↓
Contact and Company Enrichment
   ↓
Lead Scoring Engine
   ↓
Sales Insight Generator
   ↓
Dashboard + CRM Export
```

---

## 6. Repository Structure

```text
sea-startup-lead-engine/
├── app/
│   └── dashboard.py
├── connectors/
│   ├── accelerators.py
│   ├── news_rss.py
│   └── vc_portfolios.py
├── data/
│   ├── sample_enriched_leads.csv
│   └── suppression_list.csv
├── docs/
│   ├── architecture.md
│   ├── compliance.md
│   └── roadmap.md
├── models/
│   ├── lead_scoring.py
│   └── schemas.py
├── pipelines/
│   ├── discover_startups.py
│   ├── enrich_contacts.py
│   ├── generate_insights.py
│   └── run_daily_pipeline.py
├── tests/
│   └── test_scoring.py
├── requirements.txt
└── README.md
```

---

## 7. How to Run Locally

### Step 1: Clone or download this repository

```bash
git clone <your-github-repo-url>
cd sea-startup-lead-engine
```

### Step 2: Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows:

```bash
.venv\Scripts\activate
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Run the dashboard

```bash
streamlit run app/dashboard.py
```

---

## 8. Sample Lead Scoring Model

Each startup is scored out of 100:

| Signal | Weight |
|---|---:|
| ICP fit | 25 |
| Payment relevance | 25 |
| Growth signal | 20 |
| SEA strategic value | 10 |
| Contactability | 10 |
| Timing trigger | 10 |

---

## 9. Compliance Principles

This project is designed as a responsible prototype:

- Use business contact data only.
- Store source URL and date collected for every record.
- Avoid unauthorized scraping of restricted platforms.
- Maintain suppression and opt-out lists.
- Do not store personal phone numbers unless explicitly published for business use.
- Add country-specific privacy checks before production deployment.

---

## 10. Roadmap

### 30 days

- MVP dashboard
- Sample startup dataset
- Manual/CSV imports
- Scoring model
- Sales-call brief generation

### 60 days

- Add APIs and source connectors
- Add contact verification
- Add CRM export
- Add daily digest

### 90 days

- Use sales conversion feedback to improve scores
- Add account-based marketing segments
- Add country-specific compliance logic
- Add HubSpot/Salesforce integration

---

## 11. Case Study Positioning

A strong way to present this project:

> I would build this as a revenue intelligence engine, not a raw scraping tool. The value is not in collecting every startup; the value is in identifying which SEA startups Razorpay should speak to this week, why they are relevant, and what the sales team should say.

