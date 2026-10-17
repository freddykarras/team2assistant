"""
keyword_extractor.py -- VTURCS Fall 2026, Team 2, Stage 3. Owner: Mrithika.

Interface used by main.py:
    extract_keywords(masked_text) -> list[str]

The returned tags are phrases from the faculty_data.json "keywords" vocabulary,
because retrieve_faculty() scores each tag against each professor's keywords
(exact match = 2 pts, shared word = 1 pt).

Design:
  - Deterministic (no LLM call): identical input gives identical output, so the
    extractor is held constant across Condition A and Condition B.
  - Two sources of tags, in priority order:
      1. Faculty vocabulary phrases found verbatim in the student's text.
      2. Student wording mapped to a canonical vocabulary phrase through the
         interest taxonomy below (e.g. "self-driving" -> "machine learning").
    Mapped tags are only emitted if the canonical phrase exists in the
    vocabulary, so the taxonomy can never return a tag retrieval cannot use.
  - Expects text that has already been through Madeline's masking stage.
"""

import re

from faculty_data import DATA_PATH, load_faculty_database, vocabulary

MAX_TAGS = 5

# Student wording -> canonical faculty-vocabulary phrase(s).
# Keys are regexes matched against lowercased text.
TAXONOMY = {
    # AI / ML
    r"\bai\b|\bartificial intelligence\b": ["artificial intelligence"],
    r"\bml\b|\bmachine learning\b|\bdeep learning\b|\bneural net\w*|\bpytorch\b|"
    r"\btensorflow\b|\bclassifier\b|\breinforcement learning\b": ["machine learning"],
    r"\bnlp\b|\blanguage models?\b|\bllms?\b|\btransformers?\b|\bchatbots?\b|"
    r"\bnatural language\b": ["natural language processing"],
    r"\bcomputer vision\b|\bimage (?:classif|recogn)\w*": ["computer vision", "machine learning"],
    # Robotics / autonomy (VT lists these under AI/ML and Systems)
    r"\bautonomous (?:vehicles?|systems?|cars?)\b|\bself[- ]driving\b|\brobot\w*|\bdrones?\b":
        ["machine learning", "artificial intelligence"],
    # HCI
    r"\bhci\b|\bux\b|\bui/ux\b|\buser experience\b|\busability\b|\buser interfaces?\b|"
    r"\binteraction design\b|\baccessibility\b": ["human-computer interaction"],
    r"\bvr\b|\bvirtual reality\b": ["virtual reality"],
    r"\bar\b|\baugmented reality\b": ["augmented reality"],
    # Security. CS 4264 verified against https://courses.cs.vt.edu/~cs4264/
    # (Principles of Computer Security); a bare number or generic scanner is not enough.
    r"\bcs\s*[- ]?\s*4264\b": ["cybersecurity", "security and privacy"],
    r"\bcyber ?security\b|\bhacking\b|\bweb security\b|\bmalware\b|"
    r"\bvulnerabilit(?:y|ies)\b|\bpenetration testing\b|\bSQL injection\b|\bcross[- ]site scripting\b": ["cybersecurity", "security and privacy"],
    r"\bprivacy\b": ["privacy", "security and privacy"],
    r"\bcryptography\b|\bencryption\b": ["applied cryptography"],
    # Data
    r"\bdata science\b|\bdata analysis\b|\banalytics\b|\bdatasets?\b": ["data analytics"],
    r"\bbig data\b": ["big data"],
    r"\bdata mining\b": ["data mining"],
    # Systems / HPC
    r"\bhpc\b|\bsupercomput\w*|\bhigh[- ]performance computing\b":
        ["high-performance computing and computational science", "high performance computing"],
    r"\bdistributed systems?\b": ["distributed systems"],
    r"\bnetwork(?:s|ing)?\b|\bwireless\b": ["wireless networks"],
    r"\boperating systems?\b|\bstorage\b": ["storage systems"],
    # SWE / education / bio
    r"\bsoftware (?:engineering|development|testing)\b|\bdebugging\b|\bdevops\b": ["software engineering"],
    r"\bprogramming languages?\b|\bcompilers?\b": ["programming languages"],
    r"\bteaching\b|\btutoring\b|\bcs education\b|\bcurriculum\b|\bedtech\b":
        ["computer science education"],
    r"\bbioinformatics\b|\bgenomics?\b|\bcomputational biology\b|\bbiology\b":
        ["computational biology and bioinformatics"],
    r"\bquantum\b": ["quantum computing"],
}

# Only known placeholder tokens are removed; user brackets remain searchable.
_MASK_TOKENS = re.compile(r"\[(?:DEMOGRAPHIC|PERSONAL|NAME-INTRO|PRONOUNS)\]", re.I)
_NEGATION = re.compile(
    r"\b(?:not(?!\s+(?:only|just|sure)\b)|never\s+(?:want|interested)|"
    r"(?:do\s+not|don't|don’t)\s+(?:want|like|enjoy)|"
    r"no\s+interest\s+in|avoid(?:ing)?|exclude)\b", re.I
)
_CONTRAST = re.compile(
    r"[.!?;\n]|\b(?:but|however|instead|rather)\b|"
    r"\band\s+(?=(?:I\b|want\b|like\b|enjoy\b|am\s+interested))", re.I
)


def positive_interest_text(text):
    """Exclude simple negative clauses, keeping later contrast clauses.

    Complex negation, sarcasm and ambiguous wording are not fully understood.
    This deliberately uses conservative rules rather than guessing intent.
    """
    clauses = []
    for clause in _CONTRAST.split(_MASK_TOKENS.sub(" ", text)):
        negative = _NEGATION.search(clause)
        clauses.append(clause[:negative.start()] if negative else clause)
    return " . ".join(clauses).lower()


def load_vocab(path=DATA_PATH):
    # No process-wide cache: different datasets and corrected files must be read.
    return vocabulary(load_faculty_database(path))


def extract_keywords(masked_text, vocab=None, max_tags=MAX_TAGS):
    """Return up to max_tags faculty-vocabulary phrases for the student's text."""
    if not isinstance(masked_text, str):
        raise TypeError("Research description must be text.")
    if not isinstance(max_tags, int) or isinstance(max_tags, bool) or max_tags < 0:
        raise ValueError("max_tags must be a nonnegative integer.")
    vocab = load_vocab() if vocab is None else vocab
    vset = {phrase.strip().lower() for phrase in vocab if phrase.strip()}
    low = positive_interest_text(masked_text)

    # (position, tag) so output order follows the student's own wording
    hits = {}

    # 1) vocabulary phrases found verbatim (longest first, so specific beats generic)
    claimed = []
    for phrase in sorted(vset, key=lambda phrase: (-len(phrase), phrase)):
        if len(phrase) < 4:
            continue
        for m in re.finditer(r"(?<![a-z])" + re.escape(phrase) + r"(?![a-z])", low):
            s, e = m.span()
            if any(s < ce and cs < e for cs, ce in claimed):
                continue
            claimed.append((s, e))
            hits.setdefault(phrase, (0, s))

    # 2) taxonomy: student wording -> canonical vocabulary phrase
    for pattern, canon_list in TAXONOMY.items():
        m = re.search(pattern, low)
        if not m:
            continue
        for canon in canon_list:
            if canon in vset and canon not in hits:
                hits[canon] = (1, m.start())

    ordered = sorted(hits, key=lambda t: (*hits[t], t))  # verbatim matches first, then mapped
    return ordered[:max_tags]


if __name__ == "__main__":
    tests = [
        "I'm [NAME-INTRO], a freshman. [PRONOUNS]. I just started programming in Python and I think AI is cool.",
        "a junior CS major. I took data structures and machine learning, and built a Python image classifier with PyTorch. they are interested in computer vision.",
        "I have been an undergraduate research assistant working on transformers and language models and want to continue in NLP research.",
        "I'm into web security, hacking, and privacy.",
        "I love autonomous vehicles and robotics.",
        "Not sure yet, I just like computers.",
    ]
    for t in tests:
        print(f"\n{t}\n  -> {extract_keywords(t)}")
    assert extract_keywords(tests[0]) == extract_keywords(tests[0])  # deterministic
    print("\nVocabulary size:", len(load_vocab()))
