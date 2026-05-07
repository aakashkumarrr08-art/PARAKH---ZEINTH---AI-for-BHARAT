import re


def extract_quantities(text: str) -> dict[str, int]:
    patterns = {
        "size_m": r"\b1000\s*\(?M\)?\b",
        "size_l": r"\b3000\s*\(?L\)?\b",
        "size_xl": r"\b1000\s*\(?XL\)?\b",
    }
    result: dict[str, int] = {}
    for key, pattern in patterns.items():
        if re.search(pattern, text, re.IGNORECASE):
            result[key] = int(re.search(r"\d+", re.search(pattern, text, re.IGNORECASE).group(0)).group(0))
    return result
