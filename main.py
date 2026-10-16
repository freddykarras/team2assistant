import json

# ==============================================================================
# STAGE 1: SINDHU'S FACULTY DATASET (CACHED LOCAL JSON)
# ==============================================================================
FACULTY_DATABASE = [
    {
        "name": "Dr. Autonomous Systems",
        "lab": "Autonomous Systems Lab",
        "categories": ["AI/ML", "Robotics", "Systems"],
        "keywords": ["autonomous vehicles", "robotics", "machine learning", "self-driving cars"],
        "description": "Focuses on motion planning and safe control algorithms for autonomous vehicles.",
        "url": "https://website.cs.vt.edu/research/areas/robotics.html"
    },
    {
        "name": "Dr. Cyber Security",
        "lab": "Secure Systems Lab",
        "categories": ["Cybersecurity", "Systems"],
        "keywords": ["cybersecurity", "web security", "vulnerability scanning", "privacy"],
        "description": "Investigates software vulnerability isolation and network security protocols.",
        "url": "https://website.cs.vt.edu/research/areas/security.html"
    },
    {
        "name": "Dr. Interactive AI",
        "lab": "HCI & Accessible Tech Lab",
        "categories": ["Human-Computer Interaction", "AI/ML"],
        "keywords": ["human-computer interaction", "accessibility", "generative ai", "user studies"],
        "description": "Designs accessible user interfaces and studies human interaction with AI models.",
        "url": "https://website.cs.vt.edu/research/areas/hci.html"
    }
]

# ==============================================================================
# STAGE 2: MADELINE'S DEMOGRAPHIC MASKING MODULE
# ==============================================================================
def mask_demographics(raw_input: str) -> str:
    """Strips race, gender, and class standing terms while keeping technical background."""
    masked = raw_input
    sensitive_words = [
        "woman", "man", "female", "male", "Asian", "Black", "Hispanic", "White",
        "freshman", "sophomore", "junior", "senior", "first-year"
    ]
    for word in sensitive_words:
        masked = masked.replace(word, "").replace("  ", " ")
    return masked.strip()

# ==============================================================================
# STAGE 3: MRITHIKA'S KEYWORD EXTRACTOR MODULE
# ==============================================================================
def extract_keywords(masked_input: str) -> list:
    """Extracts 2-3 technical keywords by matching text against research taxonomy."""
    text_lower = masked_input.lower()
    extracted = []
    taxonomy_terms = [
        "autonomous vehicles", "robotics", "machine learning", "self-driving cars",
        "cybersecurity", "web security", "vulnerability scanning", "privacy",
        "human-computer interaction", "accessibility", "generative ai", "user studies"
    ]
    for term in taxonomy_terms:
        if term in text_lower:
            extracted.append(term)
    return extracted[:3]

# ==============================================================================
# STAGE 4: SINDHU'S RETRIEVAL ENGINE
# ==============================================================================
def retrieve_faculty(keywords: list) -> dict:
    """Retrieves matched faculty profile from local JSON database based on keywords."""
    for record in FACULTY_DATABASE:
        for kw in keywords:
            if kw in record["keywords"]:
                return record
    return FACULTY_DATABASE[0] # Fallback default

# ==============================================================================
# STAGE 5: FREDDY'S DUAL GUIDANCE GENERATOR (CONDITION A VS CONDITION B)
# ==============================================================================
def generate_condition_a_direct_answer(faculty: dict) -> str:
    """Condition A: Direct-Answer Baseline (No Scaffolding/Templates)."""
    return (
        f"[CONDITION A - DIRECT-ANSWER BASELINE]\n"
        f"Matched Faculty: {faculty['name']} ({faculty['lab']})\n"
        f"Research Area: {', '.join(faculty['categories'])}\n"
        f"Overview: {faculty['description']}\n"
        f"Source Link: {faculty['url']}\n\n"
        f"Task Instruction: Write an email to {faculty['name']} expressing interest in their research."
    )

def generate_condition_b_scaffolded(faculty: dict, experience_tier: str) -> str:
    """Condition B: 3-Tier Scaffolded Guidance (Experience-Tailored)."""
    output = f"[CONDITION B - 3-TIER SCAFFOLDED GUIDANCE ({experience_tier.upper()} TIER)]\n"
    output += f"Matched Faculty: {faculty['name']} ({faculty['lab']})\n"
    output += f"Source Link: {faculty['url']}\n\n"
    
    if experience_tier == "Novice":
        output += (
            f"1. Plain-Language Summary: This lab builds software to make autonomous systems operate safely.\n"
            f"2. Foundational Prerequisites: CS 2114 (Data Structures) provides core pathfinding logic.\n"
            f"3. Checklist: Review the lab webpage, highlight CS 2114 projects on your resume.\n"
            f"4. Outreach Email Template:\n"
            f"   Subject: Undergraduate Research Inquiry - {faculty['lab']}\n"
            f"   Dear {faculty['name']},\n"
            f"   I am an undergraduate student interested in {faculty['keywords'][0]}. "
            f"I recently completed CS 2114 and would appreciate 15 minutes to learn more about your lab."
        )
    elif experience_tier == "Intermediate":
        output += (
            f"1. Domain Alignment: Maps your upper-level coursework directly to {faculty['lab']} research.\n"
            f"2. Recommended Paper: Read their recent work on safe motion planning.\n"
            f"3. Targeted Email Draft: Focus on linking your class project experience to their active tools."
        )
    else: # Experienced
        output += (
            f"1. Technical Brief: Cites recent publications and active grant directions.\n"
            f"2. Methodologies: Highlights specialized algorithms and datasets used.\n"
            f"3. Technical Email Outline: Bullet points for peer-to-peer technical outreach."
        )
    return output

# ==============================================================================
# PIPELINE DEMONSTRATION HARNESS
# ==============================================================================
if __name__ == "__main__":
    print("="*80)
    print("VTURCS TEAM 2 - EXPERIMENTAL PROTOTYPE V1 EXECUTION TRACE")
    print("="*80)
    
    # Non-participant synthetic benchmark input
    sample_input = "I'm a sophomore Asian female student. I loved CS 2114 and want to build self-driving cars and robotics, but I've never done research before."
    student_tier = "Novice" # From Freddy's survey criteria
    
    print(f"\n[STEP 1: RAW INPUT] -> \"{sample_input}\"")
    
    masked_text = mask_demographics(sample_input)
    print(f"[STEP 2: MADELINE'S MASKING] -> \"{masked_text}\"")
    
    keywords = extract_keywords(masked_text)
    print(f"[STEP 3: MRITHIKA'S KEYWORDS] -> {keywords}")
    
    faculty_match = retrieve_faculty(keywords)
    print(f"[STEP 4: SINDHU'S RETRIEVAL] -> Matched {faculty_match['name']}")
    
    print("\n" + "-"*80)
    print(generate_condition_a_direct_answer(faculty_match))
    print("-"*80)
    print(generate_condition_b_scaffolded(faculty_match, student_tier))
    print("="*80)