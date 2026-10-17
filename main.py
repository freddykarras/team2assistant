"""Team 2 research-assistant prototype: interactive, demo, and reproducible CLI modes."""

import argparse
import json
import re
import sys
from urllib.parse import urlparse

from faculty_data import DATA_PATH, load_faculty_database, vocabulary
from keyword_extractor import extract_keywords
from masking_filter import mask_demographics

TIERS = ("Novice", "Intermediate", "Experienced")
_STOP_WORDS = {"a", "an", "and", "or", "the", "of", "for", "in", "on", "to", "with", "by", "from", "research"}


def normalize_tier(value):
    if not isinstance(value, str) or value.strip().title() not in TIERS:
        raise ValueError("Experience tier must be Novice, Intermediate, or Experienced.")
    return value.strip().title()


def classify_experience(research_experience, advanced_coursework, project_experience):
    """Provisional self-report rubric, not a validated assessment of ability."""
    if any(type(answer) is not bool for answer in
           (research_experience, advanced_coursework, project_experience)):
        raise ValueError("Experience survey answers must be yes/no values.")
    if research_experience:
        return "Experienced"
    if advanced_coursework or project_experience:
        return "Intermediate"
    return "Novice"


def _tokens(phrase):
    return set(re.findall(r"\w+", phrase.lower())) - _STOP_WORDS


def rank_faculty(tags, faculty_database=None):
    """Exact phrase +2; substantial overlap +1 per distinct input tag.

    Partial evidence needs at least two substantive words and at least half of
    each phrase's substantive tokens. Ties use name/ID ordering for display only.
    These are heuristic scores, not probabilities or verified lab availability.
    """
    records = load_faculty_database() if faculty_database is None else faculty_database
    tags = sorted({tag.strip().lower() for tag in tags if tag.strip()})
    ranked = []
    for faculty in records:
        keywords = sorted({k.strip().lower() for k in faculty.get("keywords", [])})
        evidence = []
        for tag in tags:
            if tag in keywords:
                evidence.append({"tag": tag, "keyword": tag, "points": 2, "kind": "exact"})
                continue
            tag_words = _tokens(tag)
            overlaps = []
            for keyword in keywords:
                words = _tokens(keyword)
                shared = tag_words & words
                if (len(shared) >= 2 and len(shared) * 2 >= len(tag_words)
                        and len(shared) * 2 >= len(words)):
                    overlaps.append((len(shared), keyword))
            if overlaps:
                _, keyword = sorted(overlaps, key=lambda item: (-item[0], item[1]))[0]
                evidence.append({"tag": tag, "keyword": keyword, "points": 1, "kind": "partial"})
        if evidence:
            ranked.append({"faculty": faculty, "score": sum(e["points"] for e in evidence),
                           "evidence": evidence})
    return sorted(ranked, key=lambda item: (-item["score"], item["faculty"]["name"].casefold(),
                                           item["faculty"]["id"]))


def retrieve_faculty(tags, faculty_database=None):
    """Compatibility wrapper; the interactive pipeline exposes rankings and ties."""
    ranked = rank_faculty(tags, faculty_database)
    return ranked[0]["faculty"] if ranked else None


def _text(faculty, key):
    return faculty.get(key) or "Not available in the dataset"


def _safe_url(value):
    if not isinstance(value, str):
        return None
    parsed = urlparse(value)
    return value if parsed.scheme in ("https", "http") and parsed.netloc else None


def faculty_details(faculty):
    return (f"Faculty: {faculty['name']} ({faculty['id']})\n"
            f"Research area: {_text(faculty, 'research_area')}\n"
            f"Dataset summary: {_text(faculty, 'technical_summary')}\n"
            f"Lab name: {_text(faculty, 'lab_name')}\n"
            f"Lab URL: {_safe_url(faculty.get('lab_url')) or 'Not available in the dataset'}")


def generate_condition_a_direct_answer(faculty):
    return ("[CONDITION A — DIRECT ANSWER]\n" + faculty_details(faculty) +
            "\n\nTask: Draft a short outreach email explaining your interest in this faculty "
            "member's research. Current projects and undergraduate openings are unverified.")


def _plain_explanation(tags):
    explanations = {
        "artificial intelligence": "building computer systems that perform tasks such as reasoning or prediction",
        "machine learning": "building systems that learn patterns from examples",
        "human-computer interaction": "studying how people use and experience technology",
        "cybersecurity": "finding and reducing risks in computer systems",
        "security and privacy": "protecting systems and people's information",
        "software engineering": "designing, testing, and maintaining software",
        "natural language processing": "helping computers work with human language",
        "computer science education": "studying how people learn computing",
    }
    items = [explanations[tag] for tag in tags if tag in explanations]
    return "; ".join(dict.fromkeys(items)) or "Ask the faculty member for an introductory overview of the matched topic."


def generate_condition_b_scaffolded(faculty, experience_tier, matched_tags=None):
    tier = normalize_tier(experience_tier)
    topics = matched_tags or faculty.get("keywords", [])
    topic = topics[0] if topics else "your research"
    output = f"[CONDITION B — {tier.upper()} GUIDANCE]\n" + faculty_details(faculty) + "\n\n"
    if tier == "Novice":
        output += (
            f"Topic explanation: {_plain_explanation(topics)}.\n"
            "Preparation suggestions (not verified prerequisites): Read an introductory "
            "overview and identify one question. Ask which background would be useful.\n"
            "Checklist: Confirm the faculty member's current work; choose an accurate example "
            "of your interests; replace every bracketed placeholder before sending.\n\n"
            f"Subject: Undergraduate research inquiry — {topic}\n"
            f"Dear {faculty['name']},\n"
            f"I am an undergraduate interested in {topic}. "
            "[Describe a relevant interest, course, or project truthfully; omit if not applicable.] "
            "Would you be available for a short conversation about your research and how "
            "an undergraduate could prepare to contribute?\nThank you,\n[Your name]"
        )
    elif tier == "Intermediate":
        output += (
            f"Connection to explore: {', '.join(topics)}.\n"
            "1. Choose a course or project you actually completed and describe your contribution.\n"
            "2. Explain how that experience relates to a matched topic; confirm the faculty "
            "member's current work before naming a project.\n"
            "3. Ask about undergraduate opportunities and useful preparation.\n"
            "Email outline: [Specific interest] → [Your relevant work] → [Question or meeting request]."
        )
    else:
        output += (
            f"Technical connection to investigate: {', '.join(topics)}.\n"
            "1. Describe a research question, method, and your actual contribution.\n"
            "2. Connect it to a current publication you have checked; do not assume a lab project is active.\n"
            "3. Ask about research fit and availability. Mention publications only if you have them.\n"
            "Email outline: [Prior research] → [Verified connection] → [Proposed discussion]."
        )
    return output


def run_pipeline(text, tier, condition="B", faculty_database=None, faculty_id=None):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Enter a research interest or project description.")
    if len(text) > 10000:
        raise ValueError("Please keep the description under 10,000 characters.")
    tier = normalize_tier(tier)
    if condition not in ("A", "B", "both"):
        raise ValueError("Condition must be A, B, or both.")
    records = load_faculty_database() if faculty_database is None else faculty_database
    masked = mask_demographics(text)
    tags = extract_keywords(masked, vocabulary(records))
    ranked = rank_faculty(tags, records)
    result = {"prototype_version": "2", "tier": tier, "condition": condition,
              "tags": tags, "matches": ranked, "top_tie_count": 0,
              "selected_faculty_id": None, "guidance": {}, "warnings": [
                  "Scores reflect keyword evidence, not fit probabilities or confirmed openings.",
                  "Masking and negation use limited rules; do not enter personal identifiers."]}
    if not ranked:
        if faculty_id:
            raise ValueError("The selected faculty member has no supported match for this input.")
        result["warnings"].append("No supported match. Try a more specific research topic or project.")
        return result
    result["top_tie_count"] = sum(item["score"] == ranked[0]["score"] for item in ranked)
    if faculty_id:
        selected = next((item for item in ranked if item["faculty"]["id"] == faculty_id), None)
        if selected is None:
            raise ValueError("Faculty ID must be one of the supported candidates for this input.")
    else:
        selected = ranked[0]
        if result["top_tie_count"] > 1:
            result["warnings"].append(
                f"{result['top_tie_count']} candidates tie for the highest score. "
                "The first alphabetically is used only as an outreach example; "
                "use --faculty-id to choose another candidate.")
    faculty = selected["faculty"]
    result["selected_faculty_id"] = faculty["id"]
    matched_tags = [item["tag"] for item in selected["evidence"]]
    if condition in ("A", "both"):
        result["guidance"]["A"] = generate_condition_a_direct_answer(faculty)
    if condition in ("B", "both"):
        result["guidance"]["B"] = generate_condition_b_scaffolded(faculty, tier, matched_tags)
    return result


def render_result(result):
    lines = [f"Experience tier: {result['tier']}",
             "Research tags: " + (", ".join(result["tags"]) or "None")]
    for warning in result["warnings"]:
        lines.append("Note: " + warning)
    if result["matches"]:
        lines.append("\nSupported candidates (all scores shown; ties are not a unique best match):")
        for item in result["matches"]:
            faculty = item["faculty"]
            evidence = "; ".join(f"{e['tag']} → {e['keyword']} (+{e['points']}, {e['kind']})"
                                 for e in item["evidence"])
            lines.append(f"  {faculty['id']} | {faculty['name']} | score {item['score']} | {evidence}")
    lines.extend("\n" + guidance for guidance in result["guidance"].values())
    return "\n".join(lines)


SCENARIOS = [
    ("Novice", "I'm a sophomore female student. I loved CS 2114 and want to build self-driving cars and robotics, but I have no research experience."),
    ("Intermediate", "I am a junior male CS major. I built a web vulnerability scanner in CS 4264 and know Python/Git, but I've never worked in a lab."),
    ("Experienced", "I'm a senior who worked 2 semesters in an HCI lab doing user studies on accessibility. Looking to publish on generative AI."),
]


def run_demo(records=None):
    records = load_faculty_database() if records is None else records
    results = [run_pipeline(text, tier, "both", records) for tier, text in SCENARIOS]
    for index, result in enumerate(results, 1):
        print(f"\n{'=' * 60}\nBenchmark scenario {index}\n{'=' * 60}")
        print(render_result(result))
    return results


def _yes_no(prompt):
    while True:
        answer = input(prompt + " [y/n]: ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("Please enter y or n.")


def interactive(records):
    print("TEAM 2 — RESEARCH ASSISTANT PROTOTYPE")
    print("Use fictional descriptions for testing. Do not enter names or contact details.")
    print("This survey controls guidance detail; it does not assess your ability or eligibility.")
    research = _yes_no("Have you previously participated in a research project or lab?")
    coursework = _yes_no("Have you completed advanced coursework relevant to your interests?")
    projects = _yes_no("Have you built a substantial project relevant to your interests?")
    tier = classify_experience(research, coursework, projects)
    print(f"Suggested guidance tier: {tier}")
    while True:
        override = input("Press Enter to accept, or enter Novice / Intermediate / Experienced: ").strip()
        try:
            tier = normalize_tier(override or tier)
            break
        except ValueError as exc:
            print(exc)
    while True:
        condition = input("Guidance condition A or B [B]: ").strip().upper() or "B"
        if condition in ("A", "B"):
            break
        print("Please enter A or B.")
    while True:
        text = input("Describe your research interests or a project: ").strip()
        if text and len(text) <= 10000:
            break
        print("Enter 1–10,000 characters.")
    result = run_pipeline(text, tier, condition, records)
    print("\n" + render_result(result))
    if result["matches"]:
        while True:
            choice = input("\nEnter another candidate ID for its guidance, or Enter to finish: ").strip()
            if not choice:
                break
            try:
                print("\n" + render_result(run_pipeline(text, tier, condition, records, choice)))
            except ValueError as exc:
                print(exc)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Team 2 research-assistant prototype (Python 3.10+; no packages required).")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--demo", action="store_true", help="Run three fictional benchmarks with both conditions")
    modes.add_argument("--text", help="Research interest/project description (omit identifiers)")
    parser.add_argument("--tier", type=normalize_tier, help="Novice, Intermediate, or Experienced; required with --text")
    parser.add_argument("--condition", choices=("A", "B", "both"), default="B")
    parser.add_argument("--faculty-id", help="Choose a supported faculty ID instead of the first candidate")
    parser.add_argument("--json", action="store_true", help="Print structured results (requires --text or --demo)")
    parser.add_argument("--data", default=str(DATA_PATH), help="Path to an alternate faculty JSON dataset")
    args = parser.parse_args(argv)
    if args.text is not None and not args.tier:
        parser.error("--tier is required with --text")
    if args.text is None and (args.tier or args.faculty_id or args.condition != "B"):
        parser.error("--tier, --faculty-id, and --condition apply only to --text")
    if args.json and not (args.demo or args.text is not None):
        parser.error("--json requires --text or --demo")
    try:
        records = load_faculty_database(args.data)
        if args.demo:
            if args.json:
                print(json.dumps([run_pipeline(text, tier, "both", records)
                                  for tier, text in SCENARIOS], indent=2))
            else:
                run_demo(records)
        elif args.text is not None:
            result = run_pipeline(args.text, args.tier, args.condition, records, args.faculty_id)
            print(json.dumps(result, indent=2) if args.json else render_result(result))
        else:
            interactive(records)
        return 0
    except (EOFError, KeyboardInterrupt):
        print("\nSession ended.", file=sys.stderr)
        return 130
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
