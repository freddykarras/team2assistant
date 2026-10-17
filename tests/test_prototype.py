"""Behavioral regressions and end-to-end tests; run with unittest discovery."""

import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from faculty_data import load_faculty_database, vocabulary
from keyword_extractor import extract_keywords, load_vocab
from main import (classify_experience, generate_condition_b_scaffolded, interactive,
                  main, normalize_tier, rank_faculty, render_result, run_pipeline,
                  SCENARIOS)
from masking_filter import mask_demographics

ROOT = Path(__file__).resolve().parents[1]


def faculty(identifier="f1", name="Example Faculty", keywords=None, **fields):
    return {"id": identifier, "name": name,
            "keywords": keywords if keywords is not None else ["machine learning"], **fields}


class MaskingTests(unittest.TestCase):
    def test_preserves_all_academic_information(self):
        for standing in ("freshman", "sophomore", "junior", "senior", "first-year"):
            text = (f"I'm a {standing} female student. GPA 3.8/4.0; "
                    "A in CS 2114, B+ in math, 95% in Python; 2 semesters in a lab.")
            with self.subTest(standing=standing):
                self.assertEqual(mask_demographics(text), text.replace("female", "[DEMOGRAPHIC]"))

    def test_personal_demographics_are_case_insensitive(self):
        for term in ("Asian", "woman", "male", "Black", "Hispanic", "White", "non-binary"):
            with self.subTest(term=term):
                self.assertIn("[DEMOGRAPHIC]", mask_demographics(f"I am {term.upper()}. I like AI."))

    def test_identity_sequence(self):
        self.assertEqual(mask_demographics("I'm an Asian woman and senior."),
                         "I'm an [DEMOGRAPHIC] [DEMOGRAPHIC] and senior.")

    def test_research_subjects_and_technical_words_preserved(self):
        for text in ("I study Black student experiences in computing.",
                     "I study women in computer science education.",
                     "human-computer interaction, performance, management",
                     "I am interested in black-box testing and white-hat security.",
                     "I am a white hat researcher.", "I study white noise and black holes."):
            with self.subTest(text=text):
                self.assertEqual(mask_demographics(text), text)

    def test_explicit_identity_fields(self):
        text = "Name: Jane Smith; Gender: female; Age: 19; Pronouns: she/her; GPA: 3.9"
        masked = mask_demographics(text)
        for value in ("Jane", "female", "19", "she/her"):
            self.assertNotIn(value, masked)
        self.assertIn("GPA: 3.9", masked)

    def test_academic_labels_after_name_preserved(self):
        self.assertIn("GPA 3.9", mask_demographics("Name: Jane Smith GPA 3.9"))
        self.assertIn("grades A", mask_demographics("My name is Jane Smith grades A"))

    def test_explicit_personal_prose(self):
        masked = mask_demographics("My name is Jane Smith. I am 19 years old. My pronouns are she/her. I like AI.")
        self.assertNotIn("Jane", masked)
        self.assertNotIn("19", masked)
        self.assertNotIn("she/her", masked)
        self.assertIn("I like AI", masked)

    def test_masking_idempotent(self):
        masked = mask_demographics("I'm a Black senior with a 3.9 GPA.")
        self.assertEqual(mask_demographics(masked), masked)
        self.assertEqual(mask_demographics(""), "")

    def test_disclosures_do_not_change_research_tags(self):
        baseline = "I like human-computer interaction and machine learning."
        self.assertEqual(extract_keywords(mask_demographics("I'm an Asian woman. " + baseline)),
                         extract_keywords(baseline))


class ExtractionTests(unittest.TestCase):
    def test_negative_interest_excluded(self):
        for text in ("I am not interested in cybersecurity. I want machine learning.",
                     "I don't want cybersecurity but I like machine learning.",
                     "I want machine learning, not cybersecurity.",
                     "I have no interest in cybersecurity; I enjoy machine learning."):
            with self.subTest(text=text):
                self.assertEqual(extract_keywords(text), ["machine learning"])

    def test_no_research_experience_does_not_exclude_interest(self):
        self.assertIn("machine learning", extract_keywords("I have no research experience but like machine learning."))

    def test_not_only_is_positive(self):
        tags = extract_keywords("Not only AI but also machine learning.")
        self.assertIn("artificial intelligence", tags)
        self.assertIn("machine learning", tags)

    def test_bracketed_interests_are_not_mask_tokens(self):
        self.assertEqual(extract_keywords("[DEMOGRAPHIC] likes [machine learning]"), ["machine learning"])

    def test_security_terms_and_verified_course(self):
        for text in ("vulnerability detector", "vulnerability scanner", "vulnerabilities",
                     "CS 4264", "cs4264", "CS-4264", "penetration testing"):
            with self.subTest(text=text):
                self.assertIn("cybersecurity", extract_keywords(text))

    def test_generic_scanner_and_bare_number_not_security(self):
        self.assertEqual(extract_keywords("I used a document scanner for 4264 pages."), [])

    def test_max_tags_and_normalized_vocabulary(self):
        self.assertEqual(extract_keywords("machine learning", ["Machine Learning"]), ["machine learning"])
        self.assertEqual(extract_keywords("AI", max_tags=0), [])
        with self.assertRaises(ValueError):
            extract_keywords("AI", max_tags=-1)

    def test_repeatable_across_python_hash_seeds(self):
        code = ("import json; from keyword_extractor import extract_keywords; "
                "print(json.dumps(extract_keywords('alpha beta gamma', ['alpha beta','beta gamma'])))")
        outputs = [subprocess.check_output([sys.executable, "-c", code], cwd=ROOT,
                   env={**os.environ, "PYTHONHASHSEED": str(seed)}, text=True) for seed in range(5)]
        self.assertEqual(len(set(outputs)), 1)


class RetrievalTests(unittest.TestCase):
    def test_exact_and_partial_scores(self):
        data = [faculty("f1", keywords=["machine learning"]),
                faculty("f2", keywords=["applied machine learning"])]
        matches = rank_faculty(["machine learning"], data)
        self.assertEqual([m["score"] for m in matches], [2, 1])
        self.assertEqual(matches[1]["evidence"][0]["kind"], "partial")

    def test_stopwords_and_single_words_do_not_match(self):
        self.assertEqual(rank_faculty(["security and privacy"],
                         [faculty(keywords=["systems and networking"])]), [])
        self.assertEqual(rank_faculty(["human-computer interaction"],
                         [faculty(keywords=["ai-mediated human systems"])]), [])

    def test_no_evidence_or_empty_database(self):
        self.assertEqual(rank_faculty([], [faculty()]), [])
        self.assertEqual(rank_faculty(["unknown topic"], [faculty()]), [])
        self.assertEqual(rank_faculty(["machine learning"], []), [])

    def test_duplicate_tags_do_not_inflate_scores(self):
        self.assertEqual(rank_faculty(["machine learning", "Machine Learning"], [faculty()])[0]["score"], 2)

    def test_order_independent_ties_are_disclosed(self):
        data = [faculty("f2", "Zeta"), faculty("f1", "Alpha")]
        self.assertEqual(rank_faculty(["machine learning"], data),
                         rank_faculty(["machine learning"], list(reversed(data))))
        result = run_pipeline("machine learning", "Novice", faculty_database=data)
        self.assertEqual(result["top_tie_count"], 2)
        self.assertTrue(any("tie" in warning for warning in result["warnings"]))
        self.assertEqual(result["selected_faculty_id"], "f1")

    def test_candidate_can_be_selected(self):
        data = [faculty("f1", "Alpha"), faculty("f2", "Zeta")]
        result = run_pipeline("machine learning", "Novice", faculty_database=data, faculty_id="f2")
        self.assertEqual(result["selected_faculty_id"], "f2")
        self.assertIn("Zeta", result["guidance"]["B"])
        with self.assertRaises(ValueError):
            run_pipeline("machine learning", "Novice", faculty_database=data, faculty_id="missing")


class PipelineTests(unittest.TestCase):
    def test_survey_and_tier_validation(self):
        self.assertEqual(classify_experience(False, False, False), "Novice")
        self.assertEqual(classify_experience(False, True, False), "Intermediate")
        self.assertEqual(classify_experience(False, False, True), "Intermediate")
        self.assertEqual(classify_experience(True, False, False), "Experienced")
        self.assertEqual(normalize_tier(" novice "), "Novice")
        with self.assertRaises(ValueError):
            normalize_tier("expert")
        with self.assertRaises(ValueError):
            classify_experience("no", False, False)

    def test_guidance_uses_no_invented_student_credentials(self):
        output = generate_condition_b_scaffolded(faculty(), "novice")
        self.assertIn("NOVICE", output)
        self.assertIn("[Describe", output)
        self.assertNotIn("I recently completed", output)
        self.assertNotIn("CS 2114", output)
        self.assertIn("not verified prerequisites", output)

    def test_missing_data_does_not_render_none_or_fake_url(self):
        output = generate_condition_b_scaffolded(faculty(technical_summary=None, lab_url="javascript:alert(1)"), "Experienced")
        self.assertNotIn("None", output)
        self.assertNotIn("javascript:", output)
        self.assertIn("Not available", output)

    def test_condition_changes_guidance_only(self):
        a = run_pipeline("cybersecurity", "Novice", "A")
        b = run_pipeline("cybersecurity", "Experienced", "B")
        self.assertEqual(a["tags"], b["tags"])
        self.assertEqual(a["matches"], b["matches"])
        self.assertEqual(set(a["guidance"]), {"A"})
        self.assertEqual(set(b["guidance"]), {"B"})

    def test_no_match_has_no_outreach(self):
        result = run_pipeline("Not sure yet, I just like computers.", "Novice")
        self.assertEqual(result["matches"], [])
        self.assertEqual(result["guidance"], {})
        self.assertIn("No supported match", render_result(result))

    def test_json_excludes_student_description(self):
        result = run_pipeline("My name is Jane Smith. I like machine learning.", "Novice")
        self.assertNotIn("Jane Smith", json.dumps(result))
        self.assertNotIn("masked_input", result)
        self.assertNotIn("raw_input", result)

    def test_all_benchmarks_have_supported_matches(self):
        for tier, text in SCENARIOS:
            with self.subTest(tier=tier):
                result = run_pipeline(text, tier, "both")
                self.assertTrue(result["matches"])
                self.assertEqual(set(result["guidance"]), {"A", "B"})

    def test_bad_input_rejected(self):
        for text in ("", "   ", "a" * 10001):
            with self.assertRaises(ValueError):
                run_pipeline(text, "Novice")
        with self.assertRaises(ValueError):
            run_pipeline("AI", "Novice", condition="C")

    def test_interactive_flow_and_validation(self):
        answers = ["maybe", "no", "no", "yes", "expert", "intermediate", "C", "B", "", "machine learning", ""]
        with patch("builtins.input", side_effect=answers), contextlib.redirect_stdout(io.StringIO()) as output:
            interactive([faculty()])
        self.assertIn("Suggested guidance tier: Intermediate", output.getvalue())
        self.assertIn("Example Faculty", output.getvalue())


class DataTests(unittest.TestCase):
    def test_real_database_loads(self):
        data = load_faculty_database()
        self.assertEqual(len(data), 79)
        self.assertTrue(vocabulary(data))

    def test_schema_errors(self):
        invalid = [[], {}, {"faculty": []}, {"faculty": [None]},
                   {"faculty": [faculty(), faculty()]},
                   {"faculty": [faculty(keywords="machine learning")]},
                   {"faculty": [faculty(title=10)]}]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.json"
            for value in invalid:
                with self.subTest(value=value):
                    path.write_text(json.dumps(value))
                    with self.assertRaises(ValueError):
                        load_faculty_database(path)
            path.write_text("broken json")
            with self.assertRaises(ValueError):
                load_faculty_database(path)
            with self.assertRaises(ValueError):
                load_faculty_database(Path(directory) / "missing.json")

    def test_vocabulary_reads_each_dataset(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.json"
            path.write_text(json.dumps({"faculty": [faculty()]}))
            self.assertEqual(load_vocab(path), ["machine learning"])
            path.write_text(json.dumps({"faculty": [faculty(keywords=["cybersecurity"])]}))
            self.assertEqual(load_vocab(path), ["cybersecurity"])


class CLITests(unittest.TestCase):
    def run_cli(self, *args, input=None):
        return subprocess.run([sys.executable, str(ROOT / "main.py"), *args],
                              input=input, text=True, capture_output=True, cwd=tempfile.gettempdir())

    def test_json_mode_from_another_directory(self):
        process = self.run_cli("--text", "CS 4264", "--tier", "intermediate", "--json")
        self.assertEqual(process.returncode, 0, process.stderr)
        result = json.loads(process.stdout)
        self.assertIn("cybersecurity", result["tags"])

    def test_demo_json(self):
        process = self.run_cli("--demo", "--json")
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(len(json.loads(process.stdout)), 3)

    def test_interactive_cli(self):
        process = self.run_cli(input="n\nn\nn\n\nB\nmachine learning\n\n")
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertIn("NOVICE GUIDANCE", process.stdout)

    def test_invalid_arguments_and_missing_data(self):
        cases = [("--text", "AI"), ("--text", "AI", "--tier", "wrong"),
                 ("--demo", "--text", "AI"), ("--json",),
                 ("--demo", "--data", "/does-not-exist/faculty.json")]
        for args in cases:
            with self.subTest(args=args):
                process = self.run_cli(*args)
                self.assertEqual(process.returncode, 2)
                self.assertNotIn("Traceback", process.stderr)

    def test_end_of_input_is_clean(self):
        process = self.run_cli(input="")
        self.assertEqual(process.returncode, 130)
        self.assertNotIn("Traceback", process.stderr)


if __name__ == "__main__":
    unittest.main()
