import pandas as pd
import plotly.express as px
import streamlit as st
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "sample_enriched_leads.csv"

st.set_page_config(
    page_title="SEA Startup Lead Engine",
    page_icon="🚀",
    layout="wide",
)

@st.cache_data
def load_data() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH)

leads = load_data()

st.title("🚀 SEA Startup Lead Engine")
st.caption("Daily startup discovery, enrichment, scoring, and sales-call insights for Razorpay-style GTM teams.")

with st.sidebar:
    st.header("Filters")
    countries = st.multiselect("Country", sorted(leads["country"].unique()), default=sorted(leads["country"].unique()))
    segments = st.multiselect("Segment", sorted(leads["segment"].unique()), default=sorted(leads["segment"].unique()))
    priorities = st.multiselect("Priority", sorted(leads["priority"].unique()), default=sorted(leads["priority"].unique()))
    min_score = st.slider("Minimum lead score", 0, 100, 60)

filtered = leads[
    leads["country"].isin(countries)
    & leads["segment"].isin(segments)
    & leads["priority"].isin(priorities)
    & (leads["lead_score"] >= min_score)
].copy()

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Leads", len(filtered))
kpi2.metric("High priority", int((filtered["priority"] == "High").sum()))
kpi3.metric("Avg. lead score", round(filtered["lead_score"].mean(), 1) if len(filtered) else 0)
kpi4.metric("Verified email fields", int(filtered["business_email"].notna().sum()))

st.divider()

chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    country_counts = filtered.groupby("country", as_index=False).size()
    fig = px.bar(country_counts, x="country", y="size", title="Lead volume by country", labels={"size": "Leads"})
    st.plotly_chart(fig, use_container_width=True)

with chart_col2:
    segment_scores = filtered.groupby("segment", as_index=False)["lead_score"].mean().sort_values("lead_score", ascending=False)
    fig = px.bar(segment_scores, x="segment", y="lead_score", title="Average score by segment")
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Daily Prioritized Leads")

visible_columns = [
    "startup_name",
    "country",
    "segment",
    "stage",
    "founder_name",
    "business_email",
    "trigger",
    "payment_signal",
    "lead_score",
    "priority",
    "razorpay_angle",
    "crm_status",
]

st.dataframe(
    filtered[visible_columns].sort_values("lead_score", ascending=False),
    use_container_width=True,
    hide_index=True,
)

csv = filtered.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download CRM-ready CSV",
    data=csv,
    file_name="sea_startup_leads.csv",
    mime="text/csv",
)

st.divider()
st.subheader("Sales Call Brief")

if len(filtered):
    selected_startup = st.selectbox("Choose a startup", filtered.sort_values("lead_score", ascending=False)["startup_name"])
    row = filtered[filtered["startup_name"] == selected_startup].iloc[0]

    left, right = st.columns([1, 1])

    with left:
        st.markdown(f"### {row['startup_name']}")
        st.write(f"**Country:** {row['country']}")
        st.write(f"**Segment:** {row['segment']}")
        st.write(f"**Founder:** {row['founder_name']} ({row['founder_title']})")
        st.write(f"**Business email:** {row['business_email']}")
        st.write(f"**Lead score:** {row['lead_score']} / 100")
        st.write(f"**Priority:** {row['priority']}")

    with right:
        st.markdown("### Why call now")
        st.write(row["trigger"])
        st.markdown("### Razorpay angle")
        st.write(row["razorpay_angle"])
        st.markdown("### Suggested opener")
        st.info(
            f"Congrats on the recent momentum at {row['startup_name']}. "
            f"Given your work in {row['segment']}, Razorpay could help simplify {row['payment_signal'].lower()} as you scale across SEA."
        )

st.divider()
st.subheader("Compliance and Source Audit")
st.write(
    "Every record should retain source URL, date collected, contact verification status, and opt-out/suppression handling before production outreach."
)
st.dataframe(
    filtered[["startup_name", "source_url", "data_confidence", "last_verified"]],
    use_container_width=True,
    hide_index=True,
)
