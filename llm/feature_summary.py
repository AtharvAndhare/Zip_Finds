# llm/feature_summary.py

def describe_metric(name: str, score: float) -> str:
    if score >= 85:
        grade = "Excellent"
    elif score >= 70:
        grade = "Strong"
    elif score >= 50:
        grade = "Moderate"
    elif score >= 30:
        grade = "Weak"
    else:
        grade = "Very Low"

    return f"{name}: {score}/100 ({grade})"

def build_feature_summary(scores: dict) -> str:
    summary_lines = []
    
    for key, value in scores.items():
        if key == "OverallCivicScore":
            continue
        summary_lines.append(describe_metric(key, value))

    return "\n".join(summary_lines)
