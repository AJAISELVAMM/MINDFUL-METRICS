STRESS = {"stressed", "stress", "anxious", "overwhelmed", "exhausted", "tired", "burnt", "pressure", "panic", "drained"}
WORKLOAD = {"deadline", "overtime", "backlog", "overload", "too many", "blocked", "blocker", "sprint", "urgent"}
NEGATIVE = {"frustrated", "unhappy", "angry", "hopeless", "cannot", "can't", "fail", "worst"}
POSITIVE = {"good", "great", "calm", "energized", "satisfied", "balanced", "ok", "fine", "better"}


def analyze_text(text: str) -> dict:
    t = (text or "").lower()
    words = set(t.replace(",", " ").replace(".", " ").split())
    stress = len(words & STRESS) + (1 if "overwhelm" in t else 0)
    work = len(words & WORKLOAD)
    neg = len(words & NEGATIVE)
    pos = len(words & POSITIVE)
    sentiment = max(-1.0, min(1.0, (pos - neg - stress * 0.4) / 4))
    return {
        "sentiment_score": round(sentiment, 3),
        "stress_keyword_score": min(1.0, stress / 4),
        "workload_language_score": min(1.0, work / 4),
        "negative_language_score": min(1.0, neg / 3),
    }
