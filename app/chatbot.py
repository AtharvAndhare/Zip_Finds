# app/chatbot.py
from config.settings import settings
from llm.feature_summary import build_raw_data_summary
from llm.llm_client import get_llm_client


def _build_system_prompt(
    zip_code: str,
    persona: str,
    scores: dict,
    raw_data: dict | None = None,
    location: dict | None = None,
) -> str:
    overall = scores.get("OverallCivicScore")
    if overall is not None:
        civic_line = (
            f"The official Civic Score for ZIP {zip_code} is {overall:.1f} out of 100. "
            "Always reference this exact value when describing the civic score."
        )
    else:
        civic_line = f"Civic score for ZIP {zip_code} is unavailable."

    score_lines = "\n".join(f"- {metric}: {value}" for metric, value in scores.items())
    raw_summary = build_raw_data_summary(raw_data, location)

    return (
        "You are a helpful civic intelligence chatbot for Zip Finds.\n"
        "Answer using ONLY the data provided below. If a metric is N/A or missing, say so.\n"
        "Use civic scores verbatim when referencing them. Be concise and practical.\n\n"
        f"{civic_line}\n\n"
        f"Persona: {persona}\n"
        f"ZIP: {zip_code}\n\n"
        "Score breakdown:\n"
        f"{score_lines}\n\n"
        "Raw metrics:\n"
        f"{raw_summary}"
    )


def _normalize_history(history: list | None) -> list[dict]:
    """Convert frontend history to OpenAI message roles."""
    if not history:
        return []

    messages = []
    for item in history[-8:]:
        role = item.get("role")
        text = (item.get("text") or "").strip()
        if not text:
            continue
        if role == "user":
            messages.append({"role": "user", "content": text})
        elif role in ("ai", "assistant"):
            messages.append({"role": "assistant", "content": text})
    return messages


def answer_followup(
    zip_code: str,
    persona: str,
    scores: dict,
    question: str,
    raw_data: dict | None = None,
    location: dict | None = None,
    history: list | None = None,
) -> str:
    model = get_llm_client()
    system_prompt = _build_system_prompt(zip_code, persona, scores, raw_data, location)
    prior_messages = _normalize_history(history)

    if hasattr(model, "generate_content"):
        transcript = "\n".join(
            f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
            for m in prior_messages
        )
        prompt = f"{system_prompt}\n\n"
        if transcript:
            prompt += f"Conversation so far:\n{transcript}\n\n"
        prompt += f"User question: {question}"
        resp = model.generate_content(prompt)
        return resp.text

    messages = [{"role": "system", "content": system_prompt}, *prior_messages]
    messages.append({"role": "user", "content": question})

    resp = model.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
    )
    return resp.choices[0].message.content
