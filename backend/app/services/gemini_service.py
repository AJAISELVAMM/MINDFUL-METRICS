from __future__ import annotations
import logging
from typing import Any
import httpx
from ..config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)

CANDIDATE_MODELS = [
    "gemini-flash-lite-latest",
    "gemini-flash-latest",
    GEMINI_MODEL,
    "gemini-pro-latest",
]

# Ensure candidate models list has unique ordered items
CANDIDATE_MODELS = list(dict.fromkeys(m for m in CANDIDATE_MODELS if m))


def generate_chat_response(
    system_prompt: str,
    user_prompt: str,
    conversation_history: list[dict[str, str]] | None = None,
    timeout_seconds: float = 7.0,
) -> str | None:
    """
    Calls the Google Gemini API to generate a grounded, conversational response.
    Returns the generated response text or None if all candidate calls fail.
    """
    key = GEMINI_API_KEY
    if not key or key == "YOUR_GEMINI_API_KEY":
        logger.warning("GEMINI_API_KEY is not set or using placeholder.")
        return None

    # Prepare Gemini payload contents
    contents: list[dict[str, Any]] = []

    # Bounded conversation history (last 6 turns)
    if conversation_history:
        for turn in conversation_history[-6:]:
            role_val = turn.get("role") or turn.get("from") or "user"
            role = "user" if role_val in ("user", "employee") else "model"
            text = (turn.get("text") or turn.get("message") or "").strip()
            if text:
                contents.append({
                    "role": role,
                    "parts": [{"text": text}],
                })

    # Append current user prompt
    contents.append({
        "role": "user",
        "parts": [{"text": user_prompt}],
    })

    payload = {
        "system_instruction": {
            "parts": [{"text": system_prompt}],
        },
        "contents": contents,
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 700,
        },
    }

    # Attempt candidate models in sequence
    for model in CANDIDATE_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        try:
            with httpx.Client(timeout=timeout_seconds) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates") or []
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and "text" in parts[0]:
                            text_out = parts[0]["text"].strip()
                            if text_out:
                                return text_out
                elif res.status_code in (404, 503, 429):
                    logger.info(f"Gemini model {model} returned status {res.status_code}, trying next model.")
                    continue
                else:
                    logger.warning(f"Gemini API returned status {res.status_code}")
        except Exception as exc:
            logger.warning(f"Error calling Gemini with model {model}: {exc}")
            continue

    return None
