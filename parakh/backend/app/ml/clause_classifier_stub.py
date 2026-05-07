def suggest_clause_tags(text: str) -> list[str]:
    tags: list[str] = []
    lowered = text.lower()
    if "industrial license" in lowered:
        tags.append("legal")
    if "turnover" in lowered:
        tags.append("financial")
    if "level-6" in lowered or "bis" in lowered:
        tags.append("ballistic")
    if "camouflage" in lowered:
        tags.append("technical")
    return tags
