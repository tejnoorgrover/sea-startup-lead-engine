from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# Allow Streamlit Cloud to import project modules.
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from pipelines.live_discovery import discover_live_leads

st.set_page_config(
    page_title="SEA Startup Lead Engine",
    page_icon="🚀",
    layout="wide",
)

@st.cache_data(ttl=60 * 60 * 6, show_spinner="Fetching live SEA startup signals...")
def load_live_data() -> pd.DataFrame:
    """Fetch real public startup/news signals. Cached for 6 hours."""
    return discover_live_leads(max_items_per_query=8, max_enrich_contacts=15)

leads = load_live_data()

st.title("🚀 SEA Startup Lead Engine — Live Verified Signals")
st.caption(
    "Live dashboard pulling current SEA startup/funding/launch signals from public sources. "
    "Startup names are shown only when extracted with confidence; raw article headlines are kept separately as signal titles."
)

if leads.empty:
    st.warning(
        "No high-confidence live startup leads were found right now. This means the app avoided showing article headlines as startup names. "
        "Click refresh later or broaden the source pipeline."
    )
    st.stop()

with st.sidebar:
    st.header("Filters")
    countries = st.multiselect("Country", sorted(leads["country"].dropna().unique()), default=sorted(leads["country"].dropna().unique()))
    segments = st.multiselect("Segment", sorted(leads["segment"].dropna().unique()), default=sorted(leads["segment"].dropna().unique()))
    priorities = st.multiselect("Priority", sorted(leads["priority"].dropna().unique()), default=sorted(leads["priority"].dropna().unique()))
    min_score = st.slider("Minimum lead score", 0, 100, 60)
    st.info("Data refreshes automatically every 6 hours. Use the refresh button below to force a reload.")
    if st.button("Refresh live data"):
        st.cache_data.clear()
        st.rerun()

filtered = leads[
    leads["country"].isin(countries)
    & leads["segment"].isin(segments)
    & leads["priority"].isin(priorities)
    & (leads["lead_score"] >= min_score)
].copy()

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Verified startup leads", len(filtered))
kpi2.metric("High priority", int((filtered["priority"] == "High").sum()) if len(filtered) else 0)
kpi3.metric("Avg. lead score", round(filtered["lead_score"].mean(), 1) if len(filtered) else 0)
kpi4.metric("Public business emails", int((filtered["business_email"].astype(str).str.contains("@", regex=False)).sum()) if len(filtered) else 0)

st.divider()

chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    country_counts = filtered.groupby("country", as_index=False).size() if len(filtered) else pd.DataFrame(columns=["country", "size"])
    fig = px.bar(country_counts, x="country", y="size", title="Lead volume by country", labels={"size": "Leads"})
    st.plotly_chart(fig, use_container_width=True)

with chart_col2:
    segment_scores = filtered.groupby("segment", as_index=False)["lead_score"].mean().sort_values("lead_score", ascending=False) if len(filtered) else pd.DataFrame(columns=["segment", "lead_score"])
    fig = px.bar(segment_scores, x="segment", y="lead_score", title="Average score by segment")
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Daily Prioritized Live Leads")

visible_columns = [
    "startup_name",
    "country",
    "segment",
    "founder_name",
    "founder_title",
    "founder_email",
    "business_email",
    "business_phone",
    "website",
    "signal_title",
    "payment_signal",
    "lead_score",
    "priority",
    "source_name",
    "published_at",
    "data_confidence",
    "crm_status",
]

if len(filtered):
    st.dataframe(
        filtered[visible_columns].sort_values("lead_score", ascending=False),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.warning("No leads match the current filters. Lower the score threshold or broaden filters.")

csv = filtered.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download CRM-ready CSV",
    data=csv,
    file_name="sea_startup_live_leads.csv",
    mime="text/csv",
)

st.divider()
st.subheader("Sales Call Brief")

if len(filtered):
    selected_startup = st.selectbox("Choose a lead", filtered.sort_values("lead_score", ascending=False)["startup_name"])
    row = filtered[filtered["startup_name"] == selected_startup].iloc[0]

    left, right = st.columns([1, 1])

    with left:
        st.markdown(f"### {row['startup_name']}")
        st.write(f"**Country:** {row['country']}")
        st.write(f"**Segment:** {row['segment']}")
        st.write(f"**Founder:** {row.get('founder_name', 'To be enriched')}")
        st.write(f"**Founder title:** {row.get('founder_title', 'Founder / leadership to verify')}")
        st.write(f"**Founder email:** {row.get('founder_email', 'Not publicly listed in source')}")
        st.write(f"**Business email:** {row.get('business_email', 'Not publicly listed in source')}")
        st.write(f"**Business phone:** {row.get('business_phone', 'Not publicly listed in source')}")
        st.write(f"**Website:** {row.get('website', 'To be enriched')}")
        st.write(f"**Lead score:** {row['lead_score']} / 100")
        st.write(f"**Priority:** {row['priority']}")
        if row.get("source_url"):
            st.link_button("Open source article", row["source_url"])

    with right:
        st.markdown("### Why call now")
        st.write(row["signal_title"])
        st.markdown("### Razorpay angle")
        st.write(row["razorpay_angle"])
        st.markdown("### Suggested opener")
        st.info(
            f"Saw the recent signal around {row['startup_name']}. "
            f"Given your work in {row['segment']}, Razorpay could help simplify {row['razorpay_angle'].lower()} as you scale across SEA."
        )
        st.markdown("### Contact enrichment status")
        st.write(row.get("contact_enrichment_status", "To be enriched"))

st.divider()
st.subheader("Source, Contact Enrichment & Compliance")
st.write(
    "This version separates company name from article headline. If a company name cannot be extracted confidently, the record is skipped instead of showing a headline as the startup name. "
    "Founder emails are not guessed. Public business emails are collected only from official-looking company websites when available. "
    "Production founder contacts should come from approved enrichment APIs, official company websites, or CRM-compliant data providers."
)

audit_cols = [
    "startup_name", "signal_title", "founder_name", "founder_email", "business_email", "business_phone",
    "contact_enrichment_status", "source_name", "source_url", "data_confidence", "last_verified"
]
st.dataframe(
    filtered[audit_cols] if len(filtered) else pd.DataFrame(columns=audit_cols),
    use_container_width=True,
    hide_index=True,
)
