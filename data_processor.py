"""
data_processor.py — Transaction ingestion, categorization, and feature engineering.

Pipeline:
  CSV/PDF → parse → categorize → engineer features → summary stats
"""

import pandas as pd
import numpy as np
import io
import re
from datetime import datetime
from typing import Optional

# ─── CATEGORY RULES ──────────────────────────────────────────────────────────
# Pattern → Category mapping (order matters: first match wins)

CATEGORY_RULES = {
    "Food & Dining": [
        r"zomato", r"swiggy", r"dominos?", r"pizza", r"mcdonald", r"kfc",
        r"burger", r"subway", r"dunkin", r"starbucks", r"cafe|coffee", r"restaurant",
        r"blinkit", r"zepto", r"instamart", r"bigbasket", r"grofer", r"fresh",
        r"food|dining|eat|meal|snack|bakery|hotel|dhaba",
    ],
    "Transport": [
        r"uber", r"ola\b", r"rapido", r"auto\b", r"taxi", r"cab\b",
        r"petrol|fuel|petroleum|hp petro|iocl|bpcl", r"metro|dmrc|bmtc|best\s+bus",
        r"irctc|indian rail|railway", r"redbus|abhibus", r"parking",
    ],
    "Shopping": [
        r"amazon", r"flipkart", r"myntra", r"ajio", r"meesho", r"nykaa",
        r"reliance\s*retail|jio\s*mart", r"dmart", r"big\s*bazaar", r"mall",
        r"shoppers?\s*stop", r"westside", r"pantaloon", r"lifestyle",
        r"h&m|zara|uniqlo|forever21", r"daraz",
    ],
    "Subscriptions": [
        r"netflix", r"spotify", r"hotstar|disney", r"amazon\s*prime|primevideo",
        r"youtube\s*premium", r"linkedin", r"microsoft\s*365|office\s*365",
        r"adobe", r"dropbox", r"notion", r"zoom", r"slack", r"github",
        r"playstation|xbox\s*game", r"apple\s*(tv|music|one)", r"jiocinema",
    ],
    "Utilities": [
        r"electricity|bescom|msedcl|bses|tata\s*power|torrent\s*power",
        r"water\s*board|bwssb|mcgm", r"gas\s*(agency|pipe|supply)|indane|hp\s*gas|bharat\s*gas",
        r"airtel|jio|vodafone|vi\b|bsnl|tata\s*sky|dish\s*tv|d2h",
        r"internet|broadband|fiber",
    ],
    "Rent & Housing": [
        r"rent|landlord|pg\s*(accommodation|rent)", r"maintenance\s*(charge|fee)",
        r"society\s*(fee|maintenance)", r"housing\s*loan|home\s*loan|hdfc\s*home",
        r"property\s*tax",
    ],
    "Health & Medical": [
        r"hospital|clinic|doctor|medical|pharma|pharmacy|apollo|practo",
        r"1mg|netmeds|tata\s*1mg", r"health\s*insurance|star\s*health|niva|care\s*health",
        r"gym|cult\s*fit|fitness|yoga", r"lab\s*test|diagnostics|lal\s*path",
    ],
    "Education": [
        r"udemy|coursera|unacademy|byju|vedantu", r"school\s*fee|college\s*fee|tuition",
        r"book(s)?|amazon\s*kindle|flipkart\s*book", r"coaching",
    ],
    "Entertainment": [
        r"bookmyshow|pvr|inox|cinepolis", r"gaming|steam|epic\s*games",
        r"concert|event|ticket", r"bowling|fun\s*zone|amusement",
    ],
    "Travel": [
        r"makemytrip|goibibo|yatra|easemytrip", r"oyo|treebo|fabhotels?|hotel",
        r"airways|air\s*india|indigo|spice\s*jet|go\s*air|vistara|akasa",
        r"flight|airport", r"hostel|resort|airbnb",
    ],
    "Finance & Investments": [
        r"zerodha|groww|upstox|paytm\s*money|angel\s*broking",
        r"mutual\s*fund|sip\s*(debit|investment)|nifty|sensex",
        r"ppf|nps|epfo|lic|insurance\s*premium",
        r"emi|loan\s*(repay|payment)|credit\s*card\s*(bill|payment)",
        r"fd\s*(creation|deposit)|recurring\s*deposit",
    ],
    "ATM & Cash": [
        r"atm\s*(cash|withdrawal)|cash\s*withdrawal",
    ],
    "Transfers": [
        r"neft|rtgs|imps|upi|transfer|self\s*transfer|sweep",
        r"paytm|phonepe|gpay|google\s*pay|bhim",
    ],
}

def categorize_transaction(description: str) -> str:
    """Rule-based categorization using regex patterns."""
    desc = description.lower().strip()
    for category, patterns in CATEGORY_RULES.items():
        for pattern in patterns:
            if re.search(pattern, desc):
                return category
    return "Others"


# ─── DATA INGESTION ───────────────────────────────────────────────────────────

def parse_csv(file_content: bytes) -> pd.DataFrame:
    """
    Parse a bank statement CSV. Tries to auto-detect common column formats.
    Expected columns (flexible): Date, Description/Narration, Debit/Credit/Amount
    """
    try:
        df = pd.read_csv(io.BytesIO(file_content))
    except Exception as e:
        raise ValueError(f"Could not parse CSV: {e}")

    df.columns = df.columns.str.strip().str.lower()

    # ── Map date column ──
    date_candidates = ["date", "txn date", "transaction date", "value date", "posting date"]
    date_col = next((c for c in df.columns if any(d in c for d in date_candidates)), None)
    if date_col is None:
        raise ValueError("No date column found. Expected one of: Date, Txn Date, Transaction Date")
    df["date"] = pd.to_datetime(df[date_col], dayfirst=True, errors="coerce")

    # ── Map description column ──
    desc_candidates = ["description", "narration", "particulars", "details", "remarks", "transaction details"]
    desc_col = next((c for c in df.columns if any(d in c for d in desc_candidates)), None)
    if desc_col is None:
        raise ValueError("No description column found.")
    df["description"] = df[desc_col].astype(str).str.strip()

    # ── Map amount columns ──
    # Case 1: Separate debit/credit columns
    debit_col = next((c for c in df.columns if "debit" in c or "dr" == c), None)
    credit_col = next((c for c in df.columns if "credit" in c or "cr" == c), None)

    if debit_col and credit_col:
        df["debit"] = pd.to_numeric(df[debit_col].astype(str).str.replace(",", ""), errors="coerce").fillna(0)
        df["credit"] = pd.to_numeric(df[credit_col].astype(str).str.replace(",", ""), errors="coerce").fillna(0)
        df["amount"] = df["debit"].where(df["debit"] > 0, df["credit"])
        df["type"] = df.apply(lambda r: "debit" if r["debit"] > 0 else "credit", axis=1)
    else:
        # Case 2: Single amount column with +/- sign
        amount_col = next((c for c in df.columns if "amount" in c or "amt" in c), None)
        if amount_col is None:
            raise ValueError("No amount column found.")
        df["amount"] = pd.to_numeric(df[amount_col].astype(str).str.replace(",", ""), errors="coerce").fillna(0)
        df["type"] = df["amount"].apply(lambda x: "credit" if x > 0 else "debit")
        df["amount"] = df["amount"].abs()

    # ── Clean up ──
    df = df.dropna(subset=["date", "amount"])
    df = df[df["amount"] > 0]
    df["category"] = df["description"].apply(categorize_transaction)
    df["month"] = df["date"].dt.to_period("M")
    df["year_month"] = df["date"].dt.strftime("%Y-%m")

    return df[["date", "description", "amount", "type", "category", "month", "year_month"]]


def parse_pdf(file_content: bytes) -> pd.DataFrame:
    """Extract transactions from PDF bank statements using pdfplumber."""
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("pdfplumber not installed. Run: pip install pdfplumber")

    rows = []
    with pdfplumber.open(io.BytesIO(file_content)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table[1:]:  # skip header
                    if row and len(row) >= 3:
                        rows.append(row)

    if not rows:
        raise ValueError("No tables found in PDF. Try CSV format.")

    df = pd.DataFrame(rows)
    df.columns = [f"col_{i}" for i in range(len(df.columns))]

    # Best-effort: assume col_0=date, col_1=desc, col_2=debit, col_3=credit
    df.rename(columns={"col_0": "date", "col_1": "description", "col_2": "debit_raw", "col_3": "credit_raw"}, inplace=True)
    df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
    df["description"] = df.get("description", "").astype(str)
    df["debit"] = pd.to_numeric(df.get("debit_raw", "0").astype(str).str.replace(",", ""), errors="coerce").fillna(0)
    df["credit"] = pd.to_numeric(df.get("credit_raw", "0").astype(str).str.replace(",", ""), errors="coerce").fillna(0)
    df["amount"] = df["debit"].where(df["debit"] > 0, df["credit"])
    df["type"] = df.apply(lambda r: "debit" if r["debit"] > 0 else "credit", axis=1)
    df = df.dropna(subset=["date", "amount"])
    df = df[df["amount"] > 0]
    df["category"] = df["description"].apply(categorize_transaction)
    df["month"] = df["date"].dt.to_period("M")
    df["year_month"] = df["date"].dt.strftime("%Y-%m")
    return df[["date", "description", "amount", "type", "category", "month", "year_month"]]


# ─── FEATURE ENGINEERING ─────────────────────────────────────────────────────

def compute_financial_summary(df: pd.DataFrame) -> dict:
    """
    Core feature engineering — turns raw transactions into meaningful signals.
    Returns a rich summary dict used by the RAG pipeline.
    """
    debits = df[df["type"] == "debit"].copy()
    credits = df[df["type"] == "credit"].copy()

    months = sorted(df["year_month"].unique())
    latest_month = months[-1] if months else None
    prev_month = months[-2] if len(months) >= 2 else None

    # ── Per category, per month spend ──
    monthly_cat = (
        debits.groupby(["year_month", "category"])["amount"]
        .sum()
        .reset_index()
        .rename(columns={"amount": "spend"})
    )

    # ── MoM change per category ──
    mom_changes = {}
    if latest_month and prev_month:
        for cat in debits["category"].unique():
            curr = monthly_cat[(monthly_cat["year_month"] == latest_month) & (monthly_cat["category"] == cat)]["spend"].sum()
            prev = monthly_cat[(monthly_cat["year_month"] == prev_month) & (monthly_cat["category"] == cat)]["spend"].sum()
            if prev > 0:
                mom_changes[cat] = round(((curr - prev) / prev) * 100, 1)
            elif curr > 0:
                mom_changes[cat] = 100.0

    # ── Latest month stats ──
    latest_debits = debits[debits["year_month"] == latest_month] if latest_month else debits
    latest_credits = credits[credits["year_month"] == latest_month] if latest_month else credits

    total_spend = float(latest_debits["amount"].sum())
    total_income = float(latest_credits["amount"].sum())
    savings = total_income - total_spend
    savings_rate = round((savings / total_income) * 100, 1) if total_income > 0 else 0

    # ── Category breakdown ──
    cat_spend = latest_debits.groupby("category")["amount"].sum().sort_values(ascending=False)
    cat_pct = (cat_spend / total_spend * 100).round(1) if total_spend > 0 else cat_spend * 0

    # ── Top merchants ──
    top_merchants = (
        latest_debits.groupby("description")["amount"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .to_dict()
    )

    # ── Monthly trend ──
    monthly_spend = debits.groupby("year_month")["amount"].sum().to_dict()
    monthly_income = credits.groupby("year_month")["amount"].sum().to_dict()

    # ── Transaction count ──
    txn_count = len(debits)

    return {
        "latest_month": latest_month,
        "prev_month": prev_month,
        "total_spend": round(total_spend, 2),
        "total_income": round(total_income, 2),
        "savings": round(savings, 2),
        "savings_rate": savings_rate,
        "category_spend": cat_spend.to_dict(),
        "category_pct": cat_pct.to_dict(),
        "mom_changes": mom_changes,
        "top_merchants": top_merchants,
        "monthly_spend": monthly_spend,
        "monthly_income": monthly_income,
        "transaction_count": txn_count,
        "months_available": months,
    }


def summary_to_text(summary: dict) -> str:
    """Convert financial summary to human-readable text for LLM context."""
    lines = [
        f"## Financial Summary — {summary.get('latest_month', 'N/A')}",
        "",
        f"**Income:** ₹{summary['total_income']:,.0f}",
        f"**Total Spending:** ₹{summary['total_spend']:,.0f}",
        f"**Savings:** ₹{summary['savings']:,.0f} ({summary['savings_rate']}% savings rate)",
        "",
        "### Spending by Category:",
    ]
    for cat, amount in summary["category_spend"].items():
        pct = summary["category_pct"].get(cat, 0)
        mom = summary["mom_changes"].get(cat)
        mom_str = f" [MoM: {'+' if mom and mom > 0 else ''}{mom}%]" if mom is not None else ""
        lines.append(f"- {cat}: ₹{amount:,.0f} ({pct}%){mom_str}")

    lines.append("")
    lines.append("### Month-over-Month Changes (significant):")
    for cat, chg in sorted(summary["mom_changes"].items(), key=lambda x: abs(x[1]), reverse=True):
        if abs(chg) >= 10:
            arrow = "↑" if chg > 0 else "↓"
            lines.append(f"- {cat}: {arrow} {abs(chg)}%")

    lines.append("")
    lines.append("### Top Merchants (latest month):")
    for merchant, amt in list(summary["top_merchants"].items())[:5]:
        lines.append(f"- {merchant[:50]}: ₹{amt:,.0f}")

    return "\n".join(lines)


def generate_sample_csv() -> str:
    """Generate a realistic sample CSV for demo purposes."""
    import random
    random.seed(42)

    data = []
    merchants = {
        "Food & Dining": [("Swiggy", 350), ("Zomato", 420), ("Starbucks", 680), ("McDonald's", 280), ("BigBasket", 1200)],
        "Transport": [("Uber", 250), ("Ola Cab", 180), ("IRCTC", 1200), ("Petrol Pump", 3000)],
        "Shopping": [("Amazon.in", 1500), ("Myntra", 2200), ("Flipkart", 800)],
        "Subscriptions": [("Netflix India", 649), ("Spotify Premium", 119), ("Amazon Prime", 299)],
        "Utilities": [("Airtel Broadband", 999), ("BESCOM Electricity", 1800)],
        "Rent & Housing": [("Rent Payment", 18000)],
        "Health & Medical": [("Practo Consultation", 500), ("1mg Pharmacy", 320)],
    }

    # Two months of transactions
    import datetime
    for month_offset in [1, 0]:
        base_date = datetime.date.today().replace(day=1)
        if month_offset:
            base_date = (base_date - datetime.timedelta(days=1)).replace(day=1)

        for category, txns in merchants.items():
            freq = {"Food & Dining": 12, "Transport": 8, "Shopping": 3,
                    "Subscriptions": 1, "Utilities": 1, "Rent & Housing": 1, "Health & Medical": 1}
            count = freq.get(category, 2)
            for _ in range(count):
                merchant, base_amt = random.choice(txns)
                # Increase food spend in latest month for demo
                if month_offset == 0 and category == "Food & Dining":
                    amount = base_amt * random.uniform(1.3, 1.6)
                else:
                    amount = base_amt * random.uniform(0.8, 1.2)
                day = random.randint(1, 28)
                date = base_date.replace(day=day)
                data.append({
                    "Date": date.strftime("%d/%m/%Y"),
                    "Description": merchant,
                    "Debit": round(amount, 2),
                    "Credit": ""
                })

        # Add salary credit
        data.append({
            "Date": base_date.strftime("%d/%m/%Y"),
            "Description": "SALARY CREDIT NEFT",
            "Debit": "",
            "Credit": 75000
        })

    df = pd.DataFrame(data)
    return df.to_csv(index=False)