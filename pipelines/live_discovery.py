"""Live public-source discovery for SEA startup leads.

This module uses public news/RSS discovery for startup/funding/launch signals.
It also creates founder/contact fields for the dashboard. Founder names are
extracted only when they are visible in the public headline/description; emails
and phones are not guessed. Production contact enrichment should use official
company websites or licensed enrichment APIs.
"""

from __future__ import annotations

import hashlib
import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, List, Tuple
from urllib.parse import quote_plus

import pandas as pd
import requests

COUNTRIES = ["Singapore", "Indonesia", "Vietnam", "Malaysia", "Thailand", "Philippines"]

QUERY_TEMPLATES = [
    '"{country}" startup funding OR raised OR seed OR Series A founder',
    '"{country}" fintech OR SaaS OR ecommerce OR marketplace startup launch OR funding founder',
]

COUNTRY_PRIORITY = {
    "Singapore": 10,
    "Indonesia": 10,
    "Vietnam": 8,
    "Malaysia": 7,
    "Philippines": 7,
    "Thailand": 7,
}

SEGMENT_KEYWORDS = {
    "Fintech Infrastructure": ["fintech", "payment", "payments", "payout", "wallet", "banking", "lending", "checkout"],
    "E-commerce": ["ecommerce", "e-commerce", "commerce", "retail", "merchant", "checkout", "cart"],
    "SaaS": ["saas", "software", "platform", "subscription", "b2b"],
    "Marketplace": ["marketplace", "sellers", "vendors", "gig", "platform"],
    "D2C Commerce": ["d2c", "direct-to-consumer", "brand", "consumer"],
    "Travel Marketplace": ["travel", "hotel", "tourism", "booking"],
}

GROWTH_KEYWORDS = ["raises", "raised", "funding", "funded", "seed", "series", "backs", "backed", "investment", "launch", "launches", "expands", "growth", "hiring"]
PAYMENT_KEYWORDS = ["payment", "payments", "checkout", "payout", "subscription", "billing", "fintech", "ecommerce", "marketplace", "merchant", "cross-border", "reconciliation"]


def google_news_rss_url(query: str) -> str:
    encoded = quote_plus(query)
    return f"https://news.google.com/rss/search?q={encoded}&hl=en-SG&gl=SG&ceid=SG:en"


def strip_html(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_rss_items(query: str, country: str, max_items: int = 8) -> List[Dict[str, str]]:
    url = google_news_rss_url(query)
    headers = {"User-Agent": "SEA-Startup-Lead-Engine/1.0"}
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    items: List[Dict[str, str]] = []
    for item in root.findall(".//item")[:max_items]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        published = (item.findtext("pubDate") or "").strip()
        description = strip_html(item.findtext("description") or "")
        source_el = item.find("source")
        source = (source_el.text if source_el is not None and source_el.text else "Google News").strip()
        items.append({
            "title": title,
            "description": description,
            "source_url": link,
            "published_at": published,
            "source_name": source,
            "country": country,
            "query": query,
        })
    return items


def clean_headline(title: str) -> str:
    # Google News often appends source as " - Publisher".
    return re.sub(r"\s+-\s+[^-]+$", "", title).strip()


def infer_segment(text: str) -> str:
    text_l = text.lower()
    best_segment = "Startup"
    best_hits = 0
    for segment, keywords in SEGMENT_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in text_l)
        if hits > best_hits:
            best_segment = segment
            best_hits = hits
    return best_segment


def extract_startup_name(title: str) -> str:
    headline = clean_headline(title)
    patterns = [
        r"^(.*?)\s+(?:raises|raised|secures|secured|bags|bagged|lands|landed|closes|closed|gets|got)\s+",
        r"^(.*?)\s+(?:launches|launched|unveils|unveiled|expands|expanded)\s+",
        r"(?:startup|Startup)\s+([A-Z][A-Za-z0-9&.,'\- ]{2,50})\s+(?:raises|secures|launches|expands)",
    ]
    for pattern in patterns:
        match = re.search(pattern, headline)
        if match:
            candidate = match.group(1).strip(" :,-|'\"")
            candidate = re.sub(r"^(SEA|Asian|Singapore|Indonesia|Vietnam|Malaysia|Thailand|Philippines)\s+", "", candidate, flags=re.I).strip()
            if 2 <= len(candidate) <= 60:
                return candidate
    return headline[:70]


def extract_founder(text: str) -> Tuple[str, str, str]:
    """Best-effort founder extraction from public headline/description only.

    Returns (founder_name, founder_title, enrichment_status).
    We intentionally avoid guessing; if no reliable phrase is found, the record
    is flagged for compliant enrichment.
    """
    cleaned = strip_html(text)
    patterns = [
        (r"(?:founded by|co-founded by|cofounder|co-founder)\s+([A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]+){0,3}(?:\s+(?:and|&)\s+[A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]+){0,3})?)", "Founder / Co-founder"),
        (r"(?:founder|co-founder|CEO|chief executive)\s+([A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]+){0,3})", "Founder / leadership"),
        (r"([A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]+){1,3}),\s+(?:founder|co-founder|CEO|chief executive)", "Founder / leadership"),
    ]
    for pattern, title in patterns:
        match = re.search(pattern, cleaned)
        if match:
            name = match.group(1).strip(" .,-")
            # Basic guardrails against extracting company/news terms as people.
            bad_terms = {"Startup", "Singapore", "Indonesia", "Vietnam", "Malaysia", "Thailand", "Philippines", "Series", "Seed"}
            if name and not any(term in name.split() for term in bad_terms):
                return name, title, "Founder extracted from public article text"
    return "To be enriched", "Founder / leadership to verify", "Founder not present in RSS signal"


def parse_date(date_text: str):
    if not date_text:
        return pd.NaT
    try:
        return parsedate_to_datetime(date_text)
    except Exception:
        return pd.NaT


def score_lead(row: Dict[str, str]) -> int:
    text = f"{row.get('title','')} {row.get('segment','')} {row.get('trigger','')} {row.get('description','')}".lower()
    icp_fit = 25 if row.get("segment") in {"Fintech Infrastructure", "E-commerce", "SaaS", "Marketplace", "D2C Commerce", "Travel Marketplace"} else 10
    payment_relevance = min(25, 8 + 4 * sum(1 for kw in PAYMENT_KEYWORDS if kw in text))
    growth_signal = min(20, 5 + 4 * sum(1 for kw in GROWTH_KEYWORDS if kw in text))
    market_priority = COUNTRY_PRIORITY.get(row.get("country", ""), 5)
    contactability = 10 if row.get("business_email") and "not publicly" not in str(row.get("business_email")).lower() else 0
    timing_trigger = 10
    return int(min(100, icp_fit + payment_relevance + growth_signal + market_priority + contactability + timing_trigger))


def priority_from_score(score: int) -> str:
    if score >= 80:
        return "High"
    if score >= 65:
        return "Medium"
    return "Low"


def razorpay_angle(segment: str, title: str) -> str:
    text = f"{segment} {title}".lower()
    if "marketplace" in text:
        return "Marketplace payouts, split payments, and reconciliation automation"
    if "saas" in text or "subscription" in text:
        return "Subscription billing, cross-border card payments, and invoice automation"
    if "ecommerce" in text or "commerce" in text or "merchant" in text:
        return "Checkout optimization, local payment methods, refunds, and merchant reconciliation"
    if "fintech" in text or "payment" in text:
        return "Payment APIs, payout rails, and finance operations automation"
    if "travel" in text or "booking" in text:
        return "Multi-market checkout, refunds, and vendor payout workflows"
    return "Payment gateway, cross-border collections, payouts, and reconciliation"


def discover_live_leads(max_items_per_query: int = 8) -> pd.DataFrame:
    raw_items: List[Dict[str, str]] = []
    for country in COUNTRIES:
        for template in QUERY_TEMPLATES:
            query = template.format(country=country)
            try:
                raw_items.extend(fetch_rss_items(query, country, max_items=max_items_per_query))
            except Exception:
                continue

    records: List[Dict[str, object]] = []
    seen = set()
    for item in raw_items:
        unique = hashlib.md5((item.get("title", "") + item.get("source_url", "")).encode("utf-8")).hexdigest()
        if unique in seen:
            continue
        seen.add(unique)

        title = item.get("title", "")
        description = item.get("description", "")
        text_blob = f"{title}. {description}"
        segment = infer_segment(text_blob)
        startup_name = extract_startup_name(title)
        published_dt = parse_date(item.get("published_at", ""))
        trigger = clean_headline(title)
        founder_name, founder_title, contact_status = extract_founder(text_blob)
        record = {
            "startup_name": startup_name,
            "country": item.get("country", ""),
            "city": "",
            "segment": segment,
            "stage": "Signal-based lead",
            "founder_name": founder_name,
            "founder_title": founder_title,
            "business_email": "Not publicly listed in source",
            "business_phone": "Not publicly listed in source",
            "contact_enrichment_status": contact_status,
            "website": "To be enriched from official company site",
            "source_url": item.get("source_url", ""),
            "source_name": item.get("source_name", ""),
            "trigger": trigger,
            "payment_signal": razorpay_angle(segment, title),
            "published_at": published_dt,
            "last_verified": datetime.now(timezone.utc).date().isoformat(),
            "data_confidence": "Medium - public news signal",
            "crm_status": "New",
            "raw_headline": title,
            "description": description,
        }
        score = score_lead(record)
        record["lead_score"] = score
        record["priority"] = priority_from_score(score)
        record["razorpay_angle"] = razorpay_angle(segment, title)
        records.append(record)

    df = pd.DataFrame(records)
    if df.empty:
        return df
    df = df.sort_values(["lead_score", "published_at"], ascending=[False, False], na_position="last")
    return df.reset_index(drop=True)


if __name__ == "__main__":
    leads = discover_live_leads()
    print(leads.head(20).to_string(index=False))
