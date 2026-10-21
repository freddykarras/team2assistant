"""Conservative self-disclosure masking; academic preparation is retained.

This is a transparent rule-based prototype, not a general anonymization service.
Demographic terms describing research subjects are intentionally preserved.
"""

import re

_IDENTITY = r"(?:women|woman|men|man|female|male|non[- ]binary|Asian|Black|Hispanic|White|Latino|Latina)"
_INTRO = re.compile(
    r"\b(?:I\s+am|I'm|I’m|as)\s+(?:an?\s+)?"
    r"(?:(?:first[- ]year|freshman|sophomore|junior|senior|student|CS\s+major|"
    r"undergraduate|graduate|and|,|" + _IDENTITY + r")\b[ ,]*)+",
    re.IGNORECASE,
)
_TERMS = re.compile(r"\b" + _IDENTITY + r"\b", re.IGNORECASE)
_TECHNICAL = re.compile(
    r"\b(?:black[- ](?:box|hat)|white[- ](?:box|hat)|white\s+(?:papers?|noise)|"
    r"black\s+holes?|man[- ]in[- ]the[- ]middle)\b", re.IGNORECASE
)
_LABEL = re.compile(
    r"\b(?:gender|race|ethnicity|pronouns|age|name)\s*:\s*[^;\n.]+?"
    r"(?=\s+\b(?:GPA|grades?|courses?|experience)\b|[;\n.]|$)", re.IGNORECASE
)


def mask_demographics(text: str) -> str:
    """Mask explicit disclosures, never grades, courses, or class standing.

    Structured labels end at a semicolon, newline, or period. Users should put
    academic information in separate fields/sentences, not inside these labels.
    Unrecognized free-form identity descriptions may remain; do not submit PII.
    """
    if not isinstance(text, str):
        raise TypeError("Student input must be text.")

    def mask_intro(match):
        phrase = match.group()
        protected = [m.span() for m in _TECHNICAL.finditer(text)]

        def replace(term):
            start = match.start() + term.start()
            end = match.start() + term.end()
            if any(a <= start and end <= b for a, b in protected):
                return term.group()
            if term.group().lower() in {
                "woman", "man", "female", "male", "non binary", "nonbinary", "non-binary"
            }:
                return "student"
            if term.group().lower() in {"women", "men"}:
                return "students"
            return "[DEMOGRAPHIC]"

        phrase = _TERMS.sub(replace, phrase)
        return re.sub(
            r"\b(students?)(?:\s+\1)+\b",
            r"\1",
            phrase,
            flags=re.IGNORECASE,
        )

    masked = _INTRO.sub(mask_intro, text)
    masked = _LABEL.sub("[PERSONAL]", masked)
    masked = re.sub(r"\bmy\s+pronouns\s+are\s+[a-z]+(?:\s*/\s*[a-z]+)+",
                    "[PERSONAL]", masked, flags=re.IGNORECASE)
    masked = re.sub(r"\b(?:I am|I'm|I’m)\s+\d{1,3}\s*(?:years? old|[- ]year[- ]old)\b",
                    "[PERSONAL]", masked, flags=re.IGNORECASE)
    # Only explicit name introductions; don't guess names from arbitrary prose.
    masked = re.sub(r"\bmy name is\s+[^.;\n]+?(?=\s+(?:and|GPA|grades?|courses?|experience)\b|[.;\n]|$)",
                    "[PERSONAL]", masked, flags=re.IGNORECASE)
    return masked
