# llm/narrative_generator.py

from config.settings import settings
from llm.llm_client import get_llm_client
from llm.feature_summary import build_feature_summary


def generate_narrative(zip_code: str, scores: dict, persona: str | None):
    features = build_feature_summary(scores)

    prompt = f"""
    Provide an analytical yet readable civic explanation for ZIP {zip_code}.
    Focus on safety, health, education, economy, affordability, broadband, environment, and accessibility.

    **Civic Performance Summary**
    {features}

    Persona type: {persona}.
    Provide insights on livability, resident experience, and opportunities.
    Do NOT repeat numeric values excessively—explain what they mean.
    """

    # ==========================
    # LLM Client (Gemini or OpenAI)
    # ==========================
    client = get_llm_client()

    # GEMINI
    if hasattr(client, "generate_content"):
        response = client.generate_content(prompt)
        return response.text

    # OPENAI
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "You are a civic intelligence analyst."},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content
