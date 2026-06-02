"""Live public-source discovery for SEA startup leads.

Key fix in this version:
- Do NOT put a news headline into startup_name.
- startup_name is populated only when a company name is extracted with high confidence.
- The original headline is stored separately as signal_title / trigger.
- Founder/email fields are visible, but emails are not guessed. Public business
  emails are collected only from official-looking company websites when available.

This is a compliant public-signal prototype, not a paid contact database. For
production founder-level emails, plug in licensed tools such as Apollo, Clay,
Clearbit/HubSpot enrichment, Hunter, or internal CRM enrichment approved by Legal.
"""

from __future__ import annotations

import hashlib
import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import quote_plus, urljoin, urlparse

import pandas as pd
import requests

COUNTRIES = ["Singapore", "Indonesia", "Vietnam", "Malaysia", "Thailand", "Philippines"]

QUERY_TEMPLATES = [
    '"{country}" startup raises funding seed Series A',
    '"{country}" fintech startup raises funding founder',
    '"{country}" SaaS startup raises funding founder',
    '"{country}" ecommerce startup raises funding founder',
    '"{country}" marketplace startup raises funding founder',
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
    "Fintech Infrastructure": ["fintech", "payment", "payments", "payout", "wallet", "banking", "lending", "checkout", "insurer", "insurance"],
    "E-commerce": ["ecommerce", "e-commerce", "commerce", "retail", "merchant", "checkout", "cart"],
    "SaaS": ["saas", "software", "platform", "subscription", "b2b"],
    "Marketplace": ["marketplace", "sellers", "vendors", "gig", "platform"],
    "D2C Commerce": ["d2c", "direct-to-consumer", "brand", "consumer"],
    "Travel Marketplace": ["travel", "hotel", "tourism", "booking"],
}

GROWTH_KEYWORDS = [
    "raises", "raised", "raise", "funding", "funded", "seed", "series", "backs", "backed", "investment",
    "secures", "secured", "bags", "bagged", "lands", "landed", "closes", "closed", "launch", "launches", "expands",
]
PAYMENT_KEYWORDS = [
    "payment", "payments", "checkout", "payout", "subscription", "billing", "fintech", "ecommerce", "marketplace",
    "merchant", "cross-border", "reconciliation", "wallet", "card", "cards",
]

# Articles containing these are usually analysis/listicles/programmes, not one startup lead.
BLOCKLIST_TERMS = [
    "programme", "program", "webinar", "trends", "trend", "market & investments", "market and investments",
    "funding slumps", "top funded", "why are", "female founders", "larger share", "taxman", "targets",
    "report", "reports", "ecosystem", "ranking", "rankings", "list of", "top ", "guide", "opinion",
    "refreshed startup", "refreshes startup", "accelerator opens", "applications open",
]

BAD_NAME_TERMS = {
    "startup", "startups", "funding", "funded", "series", "seed", "market", "markets", "trend", "trends", "programme",
    "program", "webinar", "founder", "founders", "venture", "ventures", "capital", "group", "consulting", "report",
    "raises", "raise", "raised", "secures", "secured", "philippine", "singapore", "indonesia", "indonesian",
    "vietnam", "vietnamese", "malaysia", "malaysian", "thailand", "thai", "philippines", "sea", "southeast",
    "asian", "asia", "fintech", "financial", "platform", "digital", "insurer", "company", "companies",
}

GENERIC_EMAIL_PREFIXES = ["hello", "contact", "info", "sales", "support", "partnerships", "business", "team"]


def google_news_rss_url(query: str) -> str:
    encoded = quote_plus(query)
    return f"https://news.google.com/rss/search?q={encoded}&hl=en-SG&gl=SG&ceid=SG:en"


def strip_html(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_headline(title: str) -> str:
    # Google News often appends source as " - Publisher".
    title = strip_html(title)
    title = re.sub(r"\s+-\s+[^-]+$", "", title).strip()
    title = title.replace("’", "'")
    return title


def fetch_rss_items(query: str, country: str, max_items: int = 8) -> List[Dict[str, str]]:
    url = google_news_rss_url(query)
    headers = {"User-Agent": "SEA-Startup-Lead-Engine/1.0 (+public RSS prototype)"}
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


def likely_company_name(candidate: str) -> bool:
    c = re.sub(r"[^A-Za-z0-9&.'\- ]", "", candidate).strip()
    if not (2 <= len(c) <= 55):
        return False
    if re.search(r"\$|\d+\s*(million|billion|m|bn)|%", c, flags=re.I):
        return False
    words = c.split()
    if len(words) > 5:
        return False
    # Reject candidates that are just descriptors/headline fragments.
    bad_hits = sum(1 for w in words if w.lower().strip("'s") in BAD_NAME_TERMS)
    if bad_hits >= max(1, len(words) // 2):
        return False
    # Reject full generic descriptions like "Philippine Fintech Startup".
    if any(term in c.lower() for term in ["startup", "funding", "market", "programme", "webinar", "trend"]):
        return False
    return True


def extract_startup_name(title: str, description: str = "") -> Optional[Tuple[str, str]]:
    """Return (startup_name, extraction_confidence) or None.

    This intentionally avoids using the full article title as startup_name.
    """
    headline = clean_headline(title)
    text = f"{headline}. {strip_html(description)}"
    lower_headline = headline.lower()

    if any(term in lower_headline for term in BLOCKLIST_TERMS):
        return None

    patterns: List[Tuple[str, str]] = [
        # "Roojai raises US$60m", "Aspire secures..."
        (r"^(?P<name>[A-Z][A-Za-z0-9&.'\- ]{1,55})\s+(?:raises|raised|raise|secures|secured|bags|bagged|lands|landed|closes|closed|gets|got|snags|scores)\b", "High - funding headline pattern"),
        # "Company, a Singapore fintech startup, raises..."
        (r"^(?P<name>[A-Z][A-Za-z0-9&.'\- ]{1,55}),\s+(?:a|an|the)\s+[A-Za-z0-9&.'\- ]{0,50}\b(?:startup|fintech|saas|platform|marketplace|company)\b", "High - appositive company pattern"),
        # "Digital insurer Roojai raises...", "Equity management platform Qapita secures..."
        (r"(?:digital\s+insurer|equity\s+management\s+platform|fintech\s+startup|saas\s+startup|ecommerce\s+startup|marketplace\s+startup|payments\s+startup|platform|company)\s+(?P<name>[A-Z][A-Za-z0-9&.'\-]{2,35})\s+(?:raises|raised|raise|secures|secured|launches|launched|expands|expanded|lands|landed|closes|closed|gets|got)\b", "Medium - descriptor plus company pattern"),
        # "Singapore's financial platform Aspire ..." but only if followed by funding/growth terms in article text.
        (r"(?:Singapore|Indonesian|Vietnamese|Malaysian|Thai|Philippine|SEA|Southeast Asian)'?s\s+(?:[A-Za-z\-]+\s+){0,4}(?:platform|startup|fintech|insurer|marketplace|company)\s+(?P<name>[A-Z][A-Za-z0-9&.'\-]{2,35})\b", "Medium - country descriptor company pattern"),
    ]

    for pattern, confidence in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        candidate = match.group("name").strip(" :,-|'\"")
        # Remove country adjectives accidentally captured at the beginning.
        candidate = re.sub(r"^(SEA|Southeast Asian|Asian|Singaporean|Singapore|Indonesian|Indonesia|Vietnamese|Vietnam|Malaysian|Malaysia|Thai|Thailand|Philippine|Philippines)\s+", "", candidate, flags=re.I).strip()
        if likely_company_name(candidate):
            return candidate, confidence
    return None


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


def extract_founder(text: str) -> Tuple[str, str, str]:
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
            if likely_person_name(name):
                return name, title, "Founder extracted from public article text"
    return "To be enriched", "Founder / leadership to verify", "Founder not present in public signal"


def likely_person_name(name: str) -> bool:
    bad = {"Startup", "Singapore", "Indonesia", "Vietnam", "Malaysia", "Thailand", "Philippines", "Series", "Seed", "Funding"}
    if any(part in bad for part in name.split()):
        return False
    if len(name.split()) > 4:
        return False
    return bool(re.match(r"^[A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]+){0,3}$", name))


def parse_date(date_text: str):
    if not date_text:
        return pd.NaT
    try:
        return parsedate_to_datetime(date_text)
    except Exception:
        return pd.NaT


def find_company_website(company_name: str) -> str:
    """Best-effort official website lookup using a public autocomplete endpoint.

    Returns a domain URL or a clear enrichment placeholder. This does not use
    paid/secret APIs and does not provide personal contacts.
    """
    if not company_name or company_name == "To be enriched":
        return "To be enriched from official company site"
    try:
        url = f"https://autocomplete.clearbit.com/v1/companies/suggest?query={quote_plus(company_name)}"
        response = requests.get(url, timeout=6, headers={"User-Agent": "SEA-Startup-Lead-Engine/1.0"})
        if not response.ok:
            return "To be enriched from official company site"
        results = response.json()
        if not results:
            return "To be enriched from official company site"
        # Pick the first result whose name roughly contains the queried token or vice versa.
        q = re.sub(r"\W+", "", company_name).lower()
        for item in results[:5]:
            domain = item.get("domain") or ""
            name = item.get("name") or ""
            n = re.sub(r"\W+", "", name).lower()
            if domain and (q in n or n in q or q[:6] in n):
                return "https://" + domain.strip("/")
        domain = results[0].get("domain")
        return "https://" + domain.strip("/") if domain else "To be enriched from official company site"
    except Exception:
        return "To be enriched from official company site"


def extract_emails(text: str) -> List[str]:
    emails = re.findall(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", text or "")
    clean: List[str] = []
    for email in emails:
        email = email.strip(".,;:()[]{}<>\"").lower()
        if any(bad in email for bad in ["example.com", "domain.com", "email.com", "yourname", "sentry", "wixpress", "godaddy"]):
            continue
        if email not in clean:
            clean.append(email)
    return clean


def pick_best_business_email(emails: Iterable[str], company_domain: str) -> str:
    emails = list(dict.fromkeys(emails))
    if not emails:
        return "Not publicly listed in source"
    parsed = urlparse(company_domain if company_domain.startswith("http") else "https://" + company_domain)
    domain = parsed.netloc.lower().replace("www.", "")
    same_domain = [e for e in emails if e.split("@")[-1].replace("www.", "") == domain]
    candidates = same_domain or emails
    for prefix in GENERIC_EMAIL_PREFIXES:
        for e in candidates:
            if e.startswith(prefix + "@"):
                return e
    return candidates[0]


def scrape_public_business_contact(website: str) -> Tuple[str, str, str]:
    """Return (business_email, business_phone, status) from official-looking site pages.

    Conservative by design: it collects public business emails only. Founder
    personal emails are not guessed.
    """
    if not website or "to be enriched" in website.lower():
        return "Not publicly listed in source", "Not publicly listed in source", "Official website not found yet"
    try:
        base = website if website.startswith("http") else "https://" + website
        paths = ["/", "/contact", "/contact-us", "/about", "/about-us"]
        all_text = ""
        headers = {"User-Agent": "SEA-Startup-Lead-Engine/1.0 (+public contact enrichment)"}
        for path in paths:
            url = urljoin(base.rstrip("/") + "/", path.lstrip("/"))
            try:
                r = requests.get(url, timeout=5, headers=headers, allow_redirects=True)
                if r.ok and "text" in r.headers.get("content-type", ""):
                    all_text += " " + r.text[:200000]
            except Exception:
                continue
        emails = extract_emails(all_text)
        business_email = pick_best_business_email(emails, base)
        # Conservative phone extraction: only return if visible near contact text.
        phone = "Not publicly listed in source"
        phone_matches = re.findall(r"(?:\+\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?){2,5}\d{3,4}", strip_html(all_text))
        if phone_matches:
            phone = phone_matches[0].strip()
        status = "Public business contact found on official website" if business_email != "Not publicly listed in source" or phone != "Not publicly listed in source" else "No public business contact found on website"
        return business_email, phone, status
    except Exception:
        return "Not publicly listed in source", "Not publicly listed in source", "Website contact enrichment failed"


def score_lead(row: Dict[str, str]) -> int:
    text = f"{row.get('startup_name','')} {row.get('signal_title','')} {row.get('segment','')} {row.get('trigger','')} {row.get('description','')}".lower()
    icp_fit = 25 if row.get("segment") in {"Fintech Infrastructure", "E-commerce", "SaaS", "Marketplace", "D2C Commerce", "Travel Marketplace"} else 10
    payment_relevance = min(25, 8 + 4 * sum(1 for kw in PAYMENT_KEYWORDS if kw in text))
    growth_signal = min(20, 5 + 4 * sum(1 for kw in GROWTH_KEYWORDS if kw in text))
    market_priority = COUNTRY_PRIORITY.get(row.get("country", ""), 5)
    contactability = 10 if row.get("business_email") and "not publicly" not in str(row.get("business_email")).lower() else 0
    timing_trigger = 10 if any(kw in text for kw in GROWTH_KEYWORDS) else 5
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
    if "ecommerce" in text or "e-commerce" in text or "commerce" in text or "merchant" in text:
        return "Checkout optimization, local payment methods, refunds, and merchant reconciliation"
    if "fintech" in text or "payment" in text or "wallet" in text:
        return "Payment APIs, payout rails, and finance operations automation"
    if "travel" in text or "booking" in text:
        return "Multi-market checkout, refunds, and vendor payout workflows"
    return "Payment gateway, cross-border collections, payouts, and reconciliation"


def discover_live_leads(max_items_per_query: int = 8, max_enrich_contacts: int = 15) -> pd.DataFrame:
    raw_items: List[Dict[str, str]] = []
    for country in COUNTRIES:
        for template in QUERY_TEMPLATES:
            query = template.format(country=country)
            try:
                raw_items.extend(fetch_rss_items(query, country, max_items=max_items_per_query))
            except Exception:
                continue

    records: List[Dict[str, object]] = []
    seen_articles = set()
    seen_companies = set()

    for item in raw_items:
        unique_article = hashlib.md5((item.get("title", "") + item.get("source_url", "")).encode("utf-8")).hexdigest()
        if unique_article in seen_articles:
            continue
        seen_articles.add(unique_article)

        title = item.get("title", "")
        description = item.get("description", "")
        extracted = extract_startup_name(title, description)
        if not extracted:
            # Important: skip low-confidence records instead of putting headline in startup_name.
            continue
        startup_name, extraction_confidence = extracted
        country = item.get("country", "")
        company_key = (startup_name.lower(), country.lower())
        if company_key in seen_companies:
            continue
        seen_companies.add(company_key)

        signal_title = clean_headline(title)
        text_blob = f"{signal_title}. {description}"
        segment = infer_segment(text_blob)
        published_dt = parse_date(item.get("published_at", ""))
        founder_name, founder_title, founder_status = extract_founder(text_blob)

        website = find_company_website(startup_name)
        business_email = "Not publicly listed in source"
        business_phone = "Not publicly listed in source"
        contact_status = founder_status + "; business contact pending"

        record = {
            "startup_name": startup_name,
            "country": country,
            "city": "",
            "segment": segment,
            "stage": "Signal-based lead",
            "founder_name": founder_name,
            "founder_title": founder_title,
            "founder_email": "Not publicly listed in source",
            "business_email": business_email,
            "business_phone": business_phone,
            "contact_enrichment_status": contact_status,
            "website": website,
            "source_url": item.get("source_url", ""),
            "source_name": item.get("source_name", ""),
            "signal_title": signal_title,
            "trigger": signal_title,
            "payment_signal": razorpay_angle(segment, signal_title),
            "published_at": published_dt,
            "last_verified": datetime.now(timezone.utc).date().isoformat(),
            "data_confidence": extraction_confidence,
            "crm_status": "New",
            "description": description,
        }
        record["razorpay_angle"] = razorpay_angle(segment, signal_title)
        record["lead_score"] = score_lead(record)
        record["priority"] = priority_from_score(record["lead_score"])
        records.append(record)

    df = pd.DataFrame(records)
    if df.empty:
        return df

    # Enrich public business contacts only for top scored leads to keep the app fast.
    df = df.sort_values(["lead_score", "published_at"], ascending=[False, False], na_position="last").reset_index(drop=True)
    enrich_count = min(max_enrich_contacts, len(df))
    for idx in range(enrich_count):
        website = str(df.at[idx, "website"])
        email, phone, status = scrape_public_business_contact(website)
        df.at[idx, "business_email"] = email
        df.at[idx, "business_phone"] = phone
        df.at[idx, "contact_enrichment_status"] = f"{df.at[idx, 'contact_enrichment_status']}; {status}"
        df.at[idx, "lead_score"] = score_lead(df.loc[idx].to_dict())
        df.at[idx, "priority"] = priority_from_score(int(df.at[idx, "lead_score"]))

    df = df.sort_values(["lead_score", "published_at"], ascending=[False, False], na_position="last")
    return df.reset_index(drop=True)


if __name__ == "__main__":
    leads = discover_live_leads(max_items_per_query=5, max_enrich_contacts=5)
    print(leads[["startup_name", "signal_title", "country", "segment", "business_email", "lead_score"]].head(20).to_string(index=False))
