# Independent team test guide

## Get running (about 2 minutes)

1. Download the complete repository/review branch, not just `main.py`.
2. Check that Python is version 3.10 or newer.
3. Open a terminal in the downloaded folder.
4. Run `python3 -m unittest discover -s tests -v`. All tests should pass.
5. Run `python3 main.py` and try the guided session. On Windows, substitute `py -3` for `python3`.

No pip installation, API key, or external service is required. Use fictional student descriptions. The program never sends outreach emails.

## Manual test session (about 10 minutes)

Use `python3 main.py --text "YOUR DESCRIPTION" --tier Novice --condition both` for each case below. Try Intermediate and Experienced as well; the ranking should stay unchanged while condition B guidance changes.

| Case | Description | Expected behavior |
|---|---|---|
| Academic information | `I'm a sophomore female student with a 3.8 GPA and an A in CS 2114. I like machine learning.` | ML matches. Preprocessing preserves standing/GPA/grade, masks explicit gender. The terminal does not echo the personal input; preservation is checked by automated tests. |
| Security project | `I built a web vulnerability scanner in CS 4264.` | Security tags and supported security candidates; no arbitrary fallback. |
| Course only | `I enjoyed CS 4264.` | Security tags. Does not claim that a course was completed. |
| Negated interest | `I am not interested in cybersecurity. I want machine learning.` | ML tags; no cybersecurity or security/privacy tag. |
| Bracketed topic | `I want [machine learning] research.` | ML tags remain. |
| Research about demographics | `I study Black student experiences in computer science education.` | Education tags; research-subject wording is preserved by preprocessing. |
| Unclear interest | `I am not sure yet. I just like computers.` | No supported match and a request for specificity; no outreach draft. |
| Multiple interests | `I study HCI and generative AI.` | Exact/meaningful evidence only; no HCI bonus solely from the word “human.” Ties explicitly identified. |
| Broad interest | `machine learning` | Multiple candidates may tie. Alphabetical order is not a claim of better fit. |

In the interactive session, answer an invalid yes/no response and an invalid tier once. The program should explain how to correct them. Select another displayed candidate ID and confirm the outreach changes to that faculty member.

## Additional regression cases (v2.1)

- `My name is Jane Smith, I have a 3.8 GPA and like AI.`: name masked, GPA retained in preprocessing, AI tags present.
- `SQL injection`: security tags present for any capitalization.
- `Cybersecurity isn't for me. I want machine learning.`: only the positive ML interest survives.
- `I don't have research experience in machine learning.`: an experience gap does not remove the topic.
- `Project name: machine learning for accessibility.`: project context is preserved.
- An unclear interactive description: the session offers another try instead of ending immediately.

These preprocessing behaviors are checked directly by `tests/test_regressions.py`; the normal interface intentionally does not print the student's description. All 79 records still need verified lab data; possible duplicate and incomplete names are warnings rather than guessed corrections.

## Check failure handling

```bash
python3 main.py --text "AI" --tier expert
python3 main.py --text "AI"
python3 main.py --demo --data missing-file.json
```

Each should report a readable error and stop, without a traceback or fabricated recommendation. Ctrl+C should end the interactive session cleanly.

## Reproduce and compare

```bash
python3 main.py --demo --json
python3 main.py --text "machine learning" --tier Novice --condition both --json
```

Repeating the same command with the same dataset should produce identical JSON. To save a fictional test result, redirect output to a local file, e.g. append `> result.json`. JSON includes the evidence behind every candidate and omits student input text. Do not share real participant descriptions or identifiers in bug reports.

Compare condition A and B outputs for the same input and tier. Both should refer to the same selected candidate; only guidance changes. Use a different `--faculty-id` only if intentionally testing candidate selection.

## Record feedback

Copy this template into your team's usual issue/feedback channel:

- Code version: output of `git rev-parse --short HEAD` (or downloaded branch/version)
- Python version and operating system:
- Command or interactive answers used (fictional data only):
- Expected result:
- Actual result / exact error:
- Could you repeat it?
- Was the ranking evidence understandable?
- Did guidance make an unsupported claim?
- Suggested improvement:

## Scope of this test

This is a usability and correctness pilot, not a validated research study. Passing the software tests does not establish recommendation quality or fairness. The experience rubric, broader language handling, faculty source verification, and formal evaluator protocol still require team review. Unknown lab information should stay unknown until a source is verified.
