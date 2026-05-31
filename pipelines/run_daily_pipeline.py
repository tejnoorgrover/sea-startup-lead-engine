import pandas as pd
from pathlib import Path
from models.lead_scoring import priority_from_score, score_lead

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "sample_enriched_leads.csv"
OUTPUT = ROOT / "data" / "sample_enriched_leads.csv"


def run_daily_pipeline():
    """MVP pipeline that recalculates scores on the sample dataset."""
    df = pd.read_csv(INPUT)
    df["lead_score"] = df.apply(lambda row: score_lead(row.to_dict()), axis=1)
    df["priority"] = df["lead_score"].apply(priority_from_score)
    df.to_csv(OUTPUT, index=False)
    return df


if __name__ == "__main__":
    result = run_daily_pipeline()
    print(f"Updated {len(result)} leads.")
