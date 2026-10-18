def recommendations_from_factors(factors: list[dict], risk_level: str) -> list[str]:
    recs = []
    names = " ".join(f.get("feature", f.get("name", "")).lower() for f in factors[:5])
    if "workload" in names:
        recs.append("Review task allocation and prioritize critical work.")
    if "overtime" in names:
        recs.append("Review working-hour patterns and reduce recurring overtime.")
    if "stress" in names or "communication" in names:
        recs.append("Review workload-related concerns and encourage appropriate support.")
    if "work_life" in names or "balance" in names:
        recs.append("Review after-hours work patterns.")
    if "deadline" in names:
        recs.append("Revisit near-term deadlines with your manager.")
    if not recs:
        recs.append("Keep logging check-ins so risk indicators stay current.")
    recs.append("These are workplace wellbeing insights, not a medical diagnosis.")
    return recs[:5]
