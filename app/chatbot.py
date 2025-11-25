# app/chatbot.py
from llm.llm_client import get_llm_client


def _build_prompt(zip_code: str, persona: str, scores: dict, question: str) -> str:
    overall = scores.get("OverallCivicScore", None)
    if overall is not None:
        civic_line = (
            f"The official Civic Score for ZIP {zip_code} is {overall:.1f} out of 100. "
            "Always reference this exact value when describing the civic score."
        )
    else:
        civic_line = (
            f"Civic score for ZIP {zip_code} is unavailable. "
            "If needed, note that it is unavailable."
        )

    score_lines = "\n".join(f"- {metric}: {value}" for metric, value in scores.items())

    return (
        "You are a helpful civic chatbot. "
        "Use the provided civic scores verbatim when referencing them.\n\n"
        f"{civic_line}\n\n"
        f"Persona: {persona}\n"
        f"ZIP: {zip_code}\n"
        "Score breakdown:\n"
        f"{score_lines}\n\n"
        f"User question: {question}"
    )


def answer_followup(zip_code: str, persona: str, scores: dict, question: str) -> str:
    model = get_llm_client()
    base_context = _build_prompt(zip_code, persona, scores, question)

    if hasattr(model, "generate_content"):
        resp = model.generate_content(base_context)
        return resp.text
    else:
        resp = model.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful civic chatbot. Use the provided civic scores verbatim.",
                },
                {"role": "user", "content": base_context},
            ],
        )
        return resp.choices[0].message.content
