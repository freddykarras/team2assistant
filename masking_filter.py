"""Rule-based self-disclosure masking; academic preparation is retained.

Gender disclosures use neutral student wording.
Demographic terms describing research subjects are intentionally preserved.
This prototype does not provide general anonymization.
"""

import re


_IDENTITY = (
    r"(?:women|woman|men|man|female|male|non[- ]?binary|"
    r"Asian|Black|Hispanic|White|Latino|Latina)"
)

_INTRO = re.compile(
    r"\b(?:I\s+am|I'm|I’m|as)\s+(?:an?\s+)?"
    r"(?:(?:first[- ]year|freshman|sophomore|junior|senior|student|CS\s+major|"
    r"undergraduate|graduate|and|,|" + _IDENTITY + r")\b[ ,]*)+",
    re.IGNORECASE,
)

_TERMS = re.compile(r"\b" + _IDENTITY + r"\b", re.IGNORECASE)

_TECHNICAL = re.compile(
    r"\b(?:black[- ](?:box|hat)|white[- ](?:box|hat)|"
    r"white\s+(?:papers?|noise)|black\s+holes?|"
    r"man[- ]in[- ]the[- ]middle)\b",
    re.IGNORECASE,
)

_LABEL = re.compile(
    r"\b(?:gender|race|ethnicity|pronouns|age|name)\s*:\s*[^;\n.]+?"
    r"(?=\s+\b(?:GPA|grades?|courses?|experience)\b|[;\n.]|$)",
    re.IGNORECASE,
)

_SINGULAR_GENDER = {
    "woman",
    "man",
    "female",
    "male",
    "non binary",
    "nonbinary",
    "non-binary",
}

_PLURAL_GENDER = {"women", "men"}


def mask_demographics(text: str) -> str:
    """Mask recognized disclosures while preserving academic information.

    Structured labels end at a semicolon, newline, or period.
    Put academic information in separate fields or sentences.
    Unrecognized identity descriptions may remain.
    """
    if not isinstance(text, str):
        raise TypeError("Student input must be text.")

    protected = [match.span() for match in _TECHNICAL.finditer(text)]

    def mask_intro(match):
        phrase = match.group()

        def replace(term):
            start = match.start() + term.start()
            end = match.start() + term.end()

            if any(a <= start and end <= b for a, b in protected):
                return term.group()

            value = term.group().lower()

            if value in _SINGULAR_GENDER:
                return "student"

            if value in _PLURAL_GENDER:
                return "students"

            return "[DEMOGRAPHIC]"

        phrase = _TERMS.sub(replace, phrase)

        # "female student" initially becomes "student student".
        phrase = re.sub(
            r"\b(students?)(?:\s+\1)+\b",
            r"\1",
            phrase,
            flags=re.IGNORECASE,
        )

        # Correct the article when a replacement follows "an".
        phrase = re.sub(
            r"\ban\s+(?=student\b)",
            "a ",
            phrase,
            flags=re.IGNORECASE,
        )

        # "I am female" becomes "I am a student".
        phrase = re.sub(
            r"\b(I\s+am|I'm|I’m|as)\s+(?=student\b)",
            r"\1 a ",
            phrase,
            flags=re.IGNORECASE,
        )

        return phrase

    masked = _INTRO.sub(mask_intro, text)
    masked = _LABEL.sub("[PERSONAL]", masked)

    masked = re.sub(
        r"\bmy\s+pronouns\s+are\s+[a-z]+(?:\s*/\s*[a-z]+)+",
        "[PERSONAL]",
        masked,
        flags=re.IGNORECASE,
    )

    masked = re.sub(
        r"\b(?:I am|I'm|I’m)\s+\d{1,3}\s*(?:years? old|[- ]year[- ]old)\b",
        "[PERSONAL]",
        masked,
        flags=re.IGNORECASE,
    )

    # Only mask explicit name introductions.
    masked = re.sub(
        r"\bmy name is\s+[^.;\n]+?"
        r"(?=\s+(?:and|GPA|grades?|courses?|experience)\b|[.;\n]|$)",
        "[PERSONAL]",
        masked,
        flags=re.IGNORECASE,
    )

    return masked
