"""
anomaly_detector.py — Statistical anomaly detection for transaction data.

Methods:
  1. Z-score per category (flags transactions > 2 std devs from category mean)
  2. Absolute threshold (unusually large single transactions)
  3. Velocity detection (sudden category-level spend spikes)
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional


def detect_transaction_anomalies(df: pd.DataFrame, z_threshold: float = 2.0) -> List[Dict]:
    """
    Flag individual transactions that are statistical outliers within their category.
    Uses Z-score: anomaly if |z| > z_threshold (default 2.0 = ~95th percentile)
    """
    anomalies = []
    debits = df[df["type"] == "debit"].copy()

    for category in debits["category"].unique():
        cat_df = debits[debits["category"] == category]
        if len(cat_df) < 3:
            continue  # Not enough data for stats

        mean = cat_df["amount"].mean()
        std = cat_df["amount"].std()

        if std == 0:
            continue

        for _, row in cat_df.iterrows():
            z = (row["amount"] - mean) / std
            if abs(z) > z_threshold:
                anomalies.append({
                    "date": str(row["date"].date()),
                    "description": row["description"],
                    "amount": float(row["amount"]),
                    "category": category,
                    "z_score": round(float(z), 2),
                    "category_mean": round(float(mean), 2),
                    "reason": f"₹{row['amount']:,.0f} is {abs(z):.1f}σ above normal {category} spend (avg ₹{mean:,.0f})",
                    "severity": "high" if abs(z) > 3 else "medium"
                })

    return sorted(anomalies, key=lambda x: abs(x["z_score"]), reverse=True)


def detect_category_spikes(summary: dict, spike_threshold: float = 30.0) -> List[Dict]:
    """
    Detect month-over-month category-level spend spikes.
    Flags categories with > spike_threshold % increase vs previous month.
    """
    spikes = []
    for category, change_pct in summary.get("mom_changes", {}).items():
        current_spend = summary["category_spend"].get(category, 0)
        if change_pct >= spike_threshold and current_spend > 500:  # ignore tiny amounts
            spikes.append({
                "category": category,
                "change_pct": change_pct,
                "current_spend": current_spend,
                "severity": "high" if change_pct > 60 else "medium",
                "message": f"{category} spending up {change_pct:+.1f}% vs last month (₹{current_spend:,.0f} this month)"
            })
    return sorted(spikes, key=lambda x: x["change_pct"], reverse=True)


def compute_savings_alert(summary: dict) -> Optional[Dict]:
    """Check if savings rate is dangerously low."""
    rate = summary.get("savings_rate", 0)
    if rate < 10:
        return {
            "type": "savings_rate",
            "severity": "high",
            "message": f"Savings rate is critically low at {rate}%. Target minimum 20%.",
            "savings_rate": rate
        }
    elif rate < 20:
        return {
            "type": "savings_rate",
            "severity": "medium",
            "message": f"Savings rate {rate}% is below recommended 20%. Small cuts can unlock ₹{(0.2 * summary['total_income'] - summary['savings']):,.0f}/month more.",
            "savings_rate": rate
        }
    return None


def compute_category_budget_alerts(summary: dict) -> List[Dict]:
    """
    Flag categories exceeding recommended % of income.
    Based on 50/30/20 rule adapted for Indian context.
    """
    alerts = []
    income = summary.get("total_income", 0)
    if income <= 0:
        return alerts

    benchmarks = {
        "Food & Dining": 0.20,
        "Transport": 0.10,
        "Shopping": 0.10,
        "Subscriptions": 0.05,
        "Entertainment": 0.05,
        "Travel": 0.10,
    }

    for category, limit_pct in benchmarks.items():
        actual = summary["category_spend"].get(category, 0)
        limit_amt = income * limit_pct
        actual_pct = (actual / income * 100) if income > 0 else 0

        if actual > limit_amt * 1.2:  # 20% buffer
            overspend = actual - limit_amt
            alerts.append({
                "category": category,
                "actual": actual,
                "limit": limit_amt,
                "actual_pct": round(actual_pct, 1),
                "limit_pct": limit_pct * 100,
                "overspend": round(overspend, 0),
                "severity": "high" if actual > limit_amt * 1.5 else "medium",
                "message": f"{category} at ₹{actual:,.0f} ({actual_pct:.1f}% of income) exceeds ₹{limit_amt:,.0f} recommended limit"
            })

    return sorted(alerts, key=lambda x: x["overspend"], reverse=True)


def full_anomaly_report(df: pd.DataFrame, summary: dict) -> dict:
    """Run all anomaly detectors and compile unified report."""
    txn_anomalies = detect_transaction_anomalies(df)
    category_spikes = detect_category_spikes(summary)
    savings_alert = compute_savings_alert(summary)
    budget_alerts = compute_category_budget_alerts(summary)

    all_alerts = []
    if savings_alert:
        all_alerts.append(savings_alert)
    for a in budget_alerts:
        all_alerts.append({"type": "budget_exceeded", **a})
    for s in category_spikes:
        all_alerts.append({"type": "category_spike", **s})

    return {
        "transaction_anomalies": txn_anomalies[:5],  # top 5
        "category_spikes": category_spikes,
        "savings_alert": savings_alert,
        "budget_alerts": budget_alerts,
        "all_alerts": all_alerts,
        "alert_count": len(all_alerts),
        "has_critical": any(a.get("severity") == "high" for a in all_alerts),
    }


def anomalies_to_text(report: dict) -> str:
    """Convert anomaly report to text for LLM context."""
    lines = ["## Anomaly & Alert Report", ""]

    if report["savings_alert"]:
        a = report["savings_alert"]
        lines.append(f"🚨 SAVINGS ALERT: {a['message']}")

    if report["budget_alerts"]:
        lines.append("\n### Budget Overruns:")
        for a in report["budget_alerts"]:
            lines.append(f"- ⚠️  {a['message']}")

    if report["category_spikes"]:
        lines.append("\n### Category Spikes (MoM):")
        for s in report["category_spikes"]:
            lines.append(f"- 📈 {s['message']}")

    if report["transaction_anomalies"]:
        lines.append("\n### Unusual Transactions:")
        for t in report["transaction_anomalies"][:3]:
            lines.append(f"- {t['date']} | {t['description'][:40]} | ₹{t['amount']:,.0f} | {t['reason']}")

    return "\n".join(lines)