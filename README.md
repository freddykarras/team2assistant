# Team 2 — Research Assistant Prototype

A local, deterministic prototype for exploring Virginia Tech faculty research and drafting undergraduate outreach. It supports an experience survey, demographic self-disclosure masking, research keyword extraction, explainable faculty rankings, and direct (A) or scaffolded (B) guidance.

**Python 3.10 or newer. No packages, API keys, or internet connection are required to run it after downloading.** This is a terminal application, not a hosted website. Faculty data is a bundled snapshot; current projects and openings are not confirmed.

## Start here

Download or clone this repository, open a terminal in its folder, then run:

```bash
python3 main.py
```

On Windows, use `py -3 main.py` if `python3` is unavailable. Check the version with `python3 --version` (or `py -3 --version`). Keep `faculty_data.json` and all Python files together.

The interactive session asks three experience questions, suggests a guidance tier you can override, and accepts a research description. Use fictional inputs for team testing. It displays every supported candidate with matching evidence, warns about ties, and lets you select a candidate ID for another outreach example.

If you received a prototype ZIP, extract the complete folder first. Other teams can use that copy independently; it does not require a GitHub account to run. Ensure they use the updated package rather than an older checkout of the repository.

## Run the benchmarks or your own case

The original three scenarios are now available explicitly as a demo. Running `main.py` without arguments starts the interactive session.

```bash
python3 main.py --demo
python3 main.py --text "I built a vulnerability scanner in CS 4264" --tier Intermediate
python3 main.py --text "I am not interested in cybersecurity. I want machine learning." --tier novice --condition B
python3 main.py --text "I study HCI and accessibility" --tier Experienced --condition both
```

Conditions:

- `A`: faculty information and a direct outreach task.
- `B`: guidance tailored to the selected experience tier (default).
- `both`: both outputs for debugging/comparison. Do not treat this as a blind experimental assignment.

To choose a different supported candidate, rerun the same input with `--faculty-id fac_XXX`, using an ID from the results. Invalid IDs or unsupported candidates are rejected.

For machine-readable results:

```bash
python3 main.py --demo --json
python3 main.py --text "machine learning" --tier Novice --condition both --json
```

JSON goes to standard output and contains tags, rankings, score evidence, tie count, selected faculty ID, guidance, and limitations. It omits the original description and masked description. The application does not automatically save student responses. Shell command history can retain descriptions passed to `--text`; use fictional inputs.

Use `--data path/to/faculty.json` for an alternate dataset and `--help` for all options. Data is loaded relative to the application by default, so running from another working directory also works. Errors produce a readable message and exit status 2; ending an interactive session with Ctrl+C/EOF exits with 130. A legitimate no-match result exits successfully with 0.

## October 21 correctness update (v2.1)

This update preserves the team's neutral gender wording and fixes name masking that could consume GPA values. Structured personal labels must start a line or follow a semicolon, so project names are not treated as personal names. Explicit professional roles are preserved.

Extraction now recognizes SQL injection regardless of case, handles common topic-before-negation forms (such as “cybersecurity isn't for me”), and distinguishes a lack of experience from a rejected topic. Case and repeated whitespace do not downgrade an exact keyword match from +2 to +1. Meaningful partial matches still score +1 under the rule below.

Malformed lab URLs are displayed as unavailable instead of crashing guidance. UTF-8 BOM datasets are accepted; malformed in-memory records and IDs with surrounding whitespace get clear errors. The interactive session lets testers retry after a no-match result. Dataset warnings expose missing labs, possible duplicate names, and single-word names without modifying unverified source records.

## How the prototype makes decisions

### Experience survey

The provisional rubric is: yes to all three questions → Experienced; yes to one or two → Intermediate; no to all three → Novice. The three questions cover prior research participation, advanced relevant coursework, and a substantial relevant project. This is a transparent guidance setting, not a validated assessment. Users can override it. Class standing and GPA do not determine the tier or faculty ranking. All tiers use the same extraction and retrieval logic.

### Masking

`masking_filter.py` masks configured demographic terms in explicit introductions (for example, “I'm an Asian woman”), explicit `Name:`, `Gender:`, `Race:`, `Ethnicity:`, `Pronouns:`, and `Age:` fields, and a few direct personal statements. Use semicolons or newlines between structured fields.

Academic standing, grades, GPA, courses, and project experience are retained. Research subjects such as “Black student experiences” and phrases such as “black-box testing” remain intact. Grades are preserved in preprocessing but are not used as research-match scores or copied into generated outreach.

This is **limited rule-based masking, not full anonymization**. Names without explicit introductions, contact details, and unfamiliar demographic wording may remain. Do not enter real identifiers. Generated output is an editable draft, not an automatically sent email.

### Extraction

The extractor uses the bundled faculty vocabulary plus a small topic taxonomy, with a maximum of five tags. Exact vocabulary phrases are prioritized, then mapped phrases, then input position with deterministic alphabetical tie-breaking. Simple negative clauses are excluded; a later contrast such as “but I want machine learning” is retained. Complex negation, sarcasm, and unstated intent are outside the prototype's scope. User brackets are retained; only recognized mask tokens are removed.

CS 4264 maps to security topics based on the [official VT course page](https://courses.cs.vt.edu/~cs4264/), checked October 16, 2026. A bare `4264` or generic `scanner` does not automatically imply cybersecurity. Course mappings describe subject matter; they do not prove completion or eligibility.

### Faculty matching

- Exact keyword phrase: **2 points** per distinct tag.
- Partial phrase overlap: **1 point** only when at least two substantive words overlap and cover at least half of each phrase's substantive words.
- Common connecting words do not contribute.
- Only candidates with positive evidence are shown. No match produces a request for more specific interests, never a fallback professor.
- Tied scores are disclosed and sorted alphabetically by name, then ID, for stable display. The first is only an outreach example; users can select another candidate.

Scores are heuristic evidence totals, not probabilities. Related tags can overlap conceptually. Broad interests such as AI will produce many equally scored candidates. A candidate's matching keyword does not prove that every requested topic is covered, and dataset-wide vocabulary coverage is incomplete.

### Guidance and dataset limitations

Guidance uses matched topics and does not assert that a student completed a course or published research. Suggested preparation is explicitly not a verified prerequisite. Replace all email placeholders with truthful details before use.

The dataset contains 79 faculty records imported from the team's source sheet. All 79 lab names/URLs and plain summaries are currently missing; 33 titles are missing, and one record has no keywords or technical summary. Missing values are shown as unavailable. No lab details were fabricated. Record-by-record source verification is still a team task; do not interpret the bundled snapshot as independently verified current information.

The loader checks required IDs, names, keyword lists, optional field types, duplicate IDs, and malformed/empty files. Records with no keywords remain in the dataset but cannot receive a keyword match.

## Test and share

```bash
python3 -m unittest discover -s tests -v
python3 main.py --demo
```

See [TESTING.md](TESTING.md) for a short independent team test session, expected outcomes, and a bug-report template. GitHub Actions runs the automated suite and demo on Python 3.10 and 3.13 after pushes and pull requests.

## Files

| File | Purpose |
|---|---|
| `main.py` | Interactive survey, pipeline, ranking, guidance, CLI, JSON output |
| `masking_filter.py` | Context-limited personal-disclosure masking |
| `keyword_extractor.py` | Research vocabulary/taxonomy and simple negation |
| `faculty_data.py` | Shared dataset loading and validation |
| `faculty_data.json` | Original team dataset; source data unchanged |
| `tests/test_prototype.py` | Original regressions and command-line tests |
| `tests/test_regressions.py` | October 21 masking, extraction, scoring, data, and CLI regressions |
| `TESTING.md` | Independent team testing instructions |
| `.github/workflows/tests.yml` | Automated checks on GitHub |
| `.gitignore` | Keeps generated Python caches and local results out of Git |

## Team follow-up

Madeline can expand self-disclosure coverage against the masking tests; Mrithika can expand the documented taxonomy and negation cases; Sindhu can verify faculty sources and maintain evidence-based retrieval; Freddy can refine the survey and guidance rubric.

Before a formal study, define the participant task, assignment/counterbalancing, outcome measures, blind evaluator protocol, and inter-rater reliability calculation. The prototype provides condition outputs and reproducible results, but does not implement participant randomization, evaluator scoring, statistical analysis, or claim validated effectiveness.
