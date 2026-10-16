"""
main.py -- VTURCS Fall 2026, Team 2 Integrated Prototype v1.
Owner / Lead: Freddy (Team 2 Lead)

Pipeline Architecture:
  - Stage 1: Experience Classification & Survey Input (Freddy)
  - Stage 2: Demographic Masking Filter (Madeline)
  - Stage 3: Keyword Extractor & Intent Mapper (Mrithika via keyword_extractor.py)
  - Stage 4: Faculty JSON Retrieval Engine (Sindhu via faculty_data.json)
  - Stage 5: Dual Guidance Engine (Freddy - Condition A Direct-Answer vs Condition B Scaffolded)
"""

import json
import sys
from pathlib import Path

# Load Mrithika's keyword extractor module directly
try:
    from keyword_extractor import extract_keywords
except ImportError:
    print("CRITICAL ERROR: Could not import extract_keywords from keyword_extractor.py!")
    print("Ensure keyword_extractor.py is in the same directory as main.py.")
    sys.exit(1)

# File path to Sindhu's verified faculty JSON dataset
DATA_PATH = Path(__file__).with_name("faculty_data.json")

# ==============================================================================
# STAGE 4: SINDHU'S FACULTY DATASET LOADER
# ==============================================================================
def load_faculty_database(path=DATA_PATH) -> list:
    """Loads all 79 faculty records from Sindhu's faculty_data.json file."""
    if not path.exists():
        print(f"CRITICAL ERROR: Could not find dataset file at {path.resolve()}!")
        print("Ensure faculty_data.json is saved in the same directory as main.py.")
        sys.exit(1)
        
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            faculty_list = data.get("faculty", [])
            if not faculty_list:
                print("WARNING: faculty_data.json loaded, but 'faculty' array is empty!")
            return faculty_list
    except (json.JSONDecodeError, OSError) as e:
        print(f"CRITICAL ERROR: Failed to parse faculty_data.json: {e}")
        sys.exit(1)

# Initialize live faculty database
FACULTY_DATABASE = load_faculty_database()

# ==============================================================================
# STAGE 2: MADELINE'S DEMOGRAPHIC MASKING PRE-PROCESSOR
# ==============================================================================
def mask_demographics(raw_input: str) -> str:
    """
    Strips demographic markers (gender, race, class standing) from raw student input
    while preserving technical skills and project context.
    """
    masked = raw_input
    sensitive_words = [
        "woman", "man", "female", "male", "Asian", "Black", "Hispanic", "White",
        "freshman", "sophomore", "junior", "senior", "first-year"
    ]
    for word in sensitive_words:
        masked = masked.replace(word, "").replace("  ", " ")
    return masked.strip()

# ==============================================================================
# STAGE 4: SINDHU'S RETRIEVAL ENGINE (MATCHES MRITHIKA'S EXTRACTED TAGS)
# ==============================================================================
def retrieve_faculty(tags: list) -> dict:
    """
    Scores every faculty member in Sindhu's 79-record dataset against Mrithika's tags:
      - Exact match in professor's keywords array = +2 pts
      - Word overlap in professor's keywords array = +1 pt
    Returns the highest-scoring faculty object from faculty_data.json.
    """
    best_match = None
    best_score = -1

    for prof in FACULTY_DATABASE:
        score = 0
        prof_keywords = [k.lower() for k in prof.get("keywords", [])]
        
        for tag in tags:
            tag_lower = tag.lower()
            if tag_lower in prof_keywords:
                score += 2
            elif any(word in kw for kw in prof_keywords for word in tag_lower.split()):
                score += 1
                
        if score > best_score:
            best_score = score
            best_match = prof

    # Fallback to first professor if no tags match
    return best_match if best_match else FACULTY_DATABASE[0]

# ==============================================================================
# STAGE 5: FREDDY'S DUAL GUIDANCE GENERATOR
# ==============================================================================
def generate_condition_a_direct_answer(faculty: dict) -> str:
    """Condition A: Direct-Answer Baseline (Unscaffolded Control)."""
    title = f", {faculty['title'].title()}" if faculty.get("title") else ""
    return (
        f"[CONDITION A - DIRECT-ANSWER BASELINE]\n"
        f"Matched Faculty: {faculty['name']}{title}\n"
        f"Research Area: {faculty.get('research_area', 'N/A')}\n"
        f"Technical Summary: {faculty.get('technical_summary', 'N/A')}\n\n"
        f"Task Instruction: Based on this faculty match, draft a short outreach email "
        f"expressing your interest in joining their lab or learning about their research."
    )

def generate_condition_b_scaffolded(faculty: dict, experience_tier: str) -> str:
    """Condition B: 3-Tier Scaffolded Guidance (Experience-Tailored Treatment)."""
    title = f", {faculty['title'].title()}" if faculty.get("title") else ""
    keywords_list = faculty.get('keywords', [])
    kw_str = ', '.join(keywords_list) if keywords_list else faculty.get('research_area', 'Computer Science')
    
    output = f"[CONDITION B - 3-TIER SCAFFOLDED GUIDANCE ({experience_tier.upper()} TIER)]\n"
    output += f"Matched Faculty: {faculty['name']}{title}\n"
    output += f"Research Area: {faculty.get('research_area', 'N/A')}\n\n"
    
    if experience_tier == "Novice":
        output += (
            f"1. Plain-Language Summary: {faculty['name']}'s lab focuses on {kw_str}.\n"
            f"2. Prerequisites Needed: Introductory CS coursework (e.g., CS 2114) provides core algorithmic concepts for this area.\n"
            f"3. Preparation Checklist: Review recent VT directory publications and highlight class projects on your resume.\n"
            f"4. Guided Email Template:\n"
            f"   Subject: Undergraduate Research Inquiry - {faculty.get('research_area', 'Research')}\n"
            f"   Dear {faculty['name']},\n"
            f"   I am an undergraduate student interested in {keywords_list[0] if keywords_list else 'your research'}. "
            f"I recently completed foundational CS coursework and would appreciate 15 minutes to learn more about potential opportunities in your lab."
        )
    elif experience_tier == "Intermediate":
        output += (
            f"1. Domain Alignment: Connects your upper-level coursework directly to {faculty['name']}'s focus in {faculty.get('research_area', 'CS')}.\n"
            f"2. Core Toolsets & Methodologies: {kw_str}.\n"
            f"3. Targeted Email Draft Outline:\n"
            f"   - Link specific 3000/4000-level projects (e.g., vulnerability scanners, web apps) to lab goals.\n"
            f"   - Express interest in ongoing lab directions.\n"
            f"   - Propose a 15-minute discussion on undergraduate research availability."
        )
    else:  # Experienced
        output += (
            f"1. Technical Brief: {faculty.get('technical_summary', 'Advanced research trajectory.')}\n"
            f"2. Specialized Keywords: {kw_str}.\n"
            f"3. Concise Technical Outreach Outline:\n"
            f"   - Cite prior research lab exposure, publications, or symposium presentations.\n"
            f"   - Propose specific methodological synergies with {faculty['name']}'s active research."
        )
    return output

# ==============================================================================
# EXECUTION HARNESS
# ==============================================================================
def run_demo():
    print("=" * 80)
    print("VTURCS TEAM 2 - INTEGRATED EXPERIMENTAL PROTOTYPE V1")
    print(f"Loaded Database: {len(FACULTY_DATABASE)} Verified VT CS Faculty Records from faculty_data.json")
    print("=" * 80)

    # 3 Non-Participant Benchmark Test Scenarios
    scenarios = [
        {
            "tier": "Novice",
            "title": "Benchmark Scenario 1 (Novice Tier)",
            "input": "I'm a sophomore female student. I loved CS 2114 and want to build self-driving cars and robotics, but I have no research experience."
        },
        {
            "tier": "Intermediate",
            "title": "Benchmark Scenario 2 (Intermediate Tier)",
            "input": "I am a junior male CS major. I built a web vulnerability scanner in CS 4264 and know Python/Git, but I've never worked in a lab."
        },
        {
            "tier": "Experienced",
            "title": "Benchmark Scenario 3 (Experienced Tier)",
            "input": "I'm a senior who worked 2 semesters in an HCI lab doing user studies on accessibility. Looking to publish on generative AI."
        }
    ]

    for scenario in scenarios:
        print("\n" + "=" * 80)
        print(f"RUNNING: {scenario['title']}")
        print("=" * 80)
        print(f"[STEP 1: RAW INPUT] -> \"{scenario['input']}\"")

        # Step 2: Masking
        masked_text = mask_demographics(scenario['input'])
        print(f"[STEP 2: MADELINE'S MASKING] -> \"{masked_text}\"")

        # Step 3: Mrithika's Extractor (Live execution against TAXONOMY and JSON vocabulary)
        extracted_tags = extract_keywords(masked_text)
        print(f"[STEP 3: MRITHIKA'S EXTRACTOR] -> Matched Tags: {extracted_tags}")

        # Step 4: Sindhu's Retrieval Engine (Searches all 79 faculty in JSON)
        faculty_match = retrieve_faculty(extracted_tags)
        print(f"[STEP 4: SINDHU'S RETRIEVAL] -> Best Match: {faculty_match['name']} ({faculty_match['id']})")

        # Step 5: Dual Guidance Generation
        print("\n" + "-" * 30 + " CONDITION A OUTPUT " + "-" * 30)
        print(generate_condition_a_direct_answer(faculty_match))
        print("\n" + "-" * 30 + " CONDITION B OUTPUT " + "-" * 30)
        print(generate_condition_b_scaffolded(faculty_match, scenario['tier']))
        print("-" * 80)

if __name__ == "__main__":
    run_demo()