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

FALLBACK_DATA_PATH = ROOT / "data" / "sample_enriched_leads.csv"

st.set_page_config(
    page_title="SEA Startup Lead Engine",
    page_icon="🚀",
    layout="wide",
)

@st.cache_data(ttl=60 * 60 * 6, show_spinner="Fetching live SEA startup signals...")
def load_live_data() -> pd.DataFrame:
    """Fetch real public startup/news signals. Cached for 6 hours."""
    df = discover_live_leads(max_items_per_query=8)
    if df.empty:
        fallback = pd.read_csv(FALLBACK_DATA_PATH)
        fallback["source_name"] = "Sample fallback"
        fallback["published_at"] = ""
        fallback["raw_headline"] = fallback["trigger"]
        return fallback
    return df

leads = load_live_data()

st.title("🚀 SEA Startup Lead Engine — Live Public Signals")
st.caption(
    "Live dashboard pulling current SEA startup/funding/launch signals from public news RSS. "
    "Founder contacts are marked for compliant enrichment rather than guessed."
)

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
kpi1.metric("Live signals", len(filtered))
kpi2.metric("High priority", int((filtered["priority"] == "High").sum()) if len(filtered) else 0)
kpi3.metric("Avg. lead score", round(filtered["lead_score"].mean(), 1) if len(filtered) else 0)
kpi4.metric("Contacts enriched", int((filtered["founder_name"] != "To be enriched").sum()) if len(filtered) and "founder_name" in filtered.columns else 0)

st.divider()

chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    country_counts = filtered.groupby("country", as_index=False).size() if len(filtered) else pd.DataFrame(columns=["country", "size"])
    fig = px.bar(country_counts, x="country", y="size", title="Live signal volume by country", labels={"size": "Signals"})
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
    "business_email",
    "business_phone",
    "contact_enrichment_status",
    "trigger",
    "payment_signal",
    "lead_score",
    "priority",
    "source_name",
    "published_at",
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
        st.write(f"**Business email:** {row.get('business_email', 'Not publicly listed in source')}")
        st.write(f"**Business phone:** {row.get('business_phone', 'Not publicly listed in source')}")
        st.write(f"**Contact status:** {row.get('contact_enrichment_status', 'To be enriched')}")
        st.write(f"**Lead score:** {row['lead_score']} / 100")
        st.write(f"**Priority:** {row['priority']}")
        if row.get("source_url"):
            st.link_button("Open source article", row["source_url"])

    with right:
        st.markdown("### Why call now")
        st.write(row["trigger"])
        st.markdown("### Razorpay angle")
        st.write(row["razorpay_angle"])
        st.markdown("### Suggested opener")
        st.info(
            f"Saw the recent signal around {row['startup_name']}. "
            f"Given your work in {row['segment']}, Razorpay could help simplify {row['razorpay_angle'].lower()} as you scale across SEA."
        )

st.divider()
st.subheader("Contact Enrichment & Compliance")
st.write(
    "This live version discovers real startup signals from public sources. "
    "Founder names are extracted only when available in public article text. "
    "Email and phone fields are now visible, but are marked as 'Not publicly listed' unless a compliant source provides them. "
    "Production should enrich these via official company websites, licensed enrichment APIs, or clearly published business contacts."
)

audit_cols = ["startup_name", "founder_name", "business_email", "business_phone", "contact_enrichment_status", "source_name", "source_url", "data_confidence", "last_verified"]
st.dataframe(
    filtered[audit_cols] if len(filtered) else pd.DataFrame(columns=audit_cols),
    use_container_width=True,
    hide_index=True,
)
