"""Reproductions discovered during the October 21 review."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from faculty_data import dataset_warnings, load_faculty_database
from keyword_extractor import extract_keywords
from main import (faculty_details, interactive, main, rank_faculty, run_pipeline)
from masking_filter import mask_demographics


def record(**changes):
    return dict(id="f1", name="Example Faculty", keywords=["machine learning"], **changes)


class ReviewRegressions(unittest.TestCase):
    def test_names_do_not_consume_grades_or_interests(self):
        for separator in (", I have ", " with ", " "):
            text = "My name is Jane Smith" + separator + "3.8 GPA and I like AI."
            with self.subTest(text=text):
                masked = mask_demographics(text)
                self.assertNotIn("Jane Smith", masked)
                self.assertIn("3.8 GPA", masked)
                self.assertIn("artificial intelligence", extract_keywords(masked))

    def test_structured_name_stops_at_comma(self):
        masked = mask_demographics("Name: Jane Smith, I have a 3.8 GPA and like AI.")
        self.assertNotIn("Jane Smith", masked)
        self.assertIn("3.8 GPA", masked)

    def test_project_name_is_not_a_personal_name(self):
        text = "Project name: machine learning for accessibility."
        self.assertEqual(mask_demographics(text), text)

    def test_explicit_professional_role_is_preserved(self):
        for role in ("professor", "researcher", "engineer", "teacher"):
            masked = mask_demographics(f"I am a female {role} studying AI.")
            self.assertNotIn("student", masked)
            self.assertIn(role, masked)
            self.assertNotIn("female", masked)

    def test_sql_case_variants(self):
        for text in ("SQL injection", "sql injection", "Sql Injection"):
            with self.subTest(text=text):
                self.assertIn("cybersecurity", extract_keywords(text))

    def test_postpositive_negation(self):
        for phrase in ("Cybersecurity is not for me", "Cybersecurity isn't for me",
                       "Cybersecurity does not interest me", "Cybersecurity is not my interest"):
            self.assertEqual(extract_keywords(phrase + ". I want machine learning."), ["machine learning"])

    def test_experience_gap_is_not_rejection(self):
        for phrase in ("I do not have research experience in machine learning.",
                       "I'm not experienced in machine learning.",
                       "I don't have experience in machine learning."):
            self.assertIn("machine learning", extract_keywords(phrase))

    def test_lack_of_interest_is_distinct_from_lack_of_experience(self):
        for phrase in ("I don't have any interest in cybersecurity.",
                       "I do not have interest in cybersecurity."):
            self.assertEqual(extract_keywords(phrase + " I like machine learning."), ["machine learning"])

    def test_dislikes_are_not_positive_tags(self):
        self.assertEqual(extract_keywords("I dislike cybersecurity but I like machine learning."), ["machine learning"])

    def test_whitespace_does_not_downgrade_exact_match(self):
        rows = [{"id": "f1", "name": "Example", "keywords": [" Machine  Learning "]}]
        tags = extract_keywords("machine\tlearning", ["machine  learning"])
        self.assertEqual(tags, ["machine learning"])
        self.assertEqual(rank_faculty(tags, rows)[0]["score"], 2)
        self.assertEqual(rank_faculty(["machine learning", "Machine  Learning"], rows)[0]["score"], 2)

    def test_exact_match_does_not_match_identifier_suffix(self):
        self.assertEqual(extract_keywords("quantum2", ["quantum"]), [])
        self.assertEqual(extract_keywords("quantum_id", ["quantum"]), [])

    def test_updated_security_tags_follow_two_point_rule(self):
        tags = extract_keywords("SQL injection")
        rows = [{"id": str(i), "name": f"Faculty {i}", "keywords": [tag]} for i, tag in enumerate(tags)]
        self.assertTrue(tags)
        for match in rank_faculty(tags, rows):
            self.assertEqual(match["score"], 2)
            self.assertEqual(match["evidence"][0]["kind"], "exact")

    def test_malformed_urls_do_not_crash_guidance(self):
        for url in ("https://[broken", "https://example.org:99999/", "https://example.org:abc/",
                    "https://user:password@example.org/", "https://bad host.org"):
            with self.subTest(url=url):
                output = faculty_details(record(lab_url=url))
                self.assertIn("Lab URL: Not available", output)
        self.assertIn("https://example.org/lab", faculty_details(record(lab_url="https://example.org/lab")))

    def test_in_memory_schema_errors_are_clear(self):
        for data in ([{"id":"x"}], [None], "not a list"):
            with self.assertRaises(ValueError):
                run_pipeline("AI", "Novice", faculty_database=data)
        for tags in ("machine learning", [None]):
            with self.assertRaises(ValueError):
                rank_faculty(tags, [record()])
        with self.assertRaises(ValueError):
            extract_keywords("AI", vocab=[None])

    def test_utf8_bom_dataset_and_id_whitespace(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.json"
            path.write_text(json.dumps({"faculty":[record()]}), encoding="utf-8-sig")
            self.assertEqual(load_faculty_database(path)[0]["id"], "f1")
            invalid = record()
            invalid["id"] = " f1 "
            path.write_text(json.dumps({"faculty":[invalid]}))
            with self.assertRaises(ValueError):
                load_faculty_database(path)

    def test_known_data_quality_gaps_are_visible(self):
        warnings = " ".join(dataset_warnings(load_faculty_database()))
        self.assertIn("79 of 79", warnings)
        self.assertIn("fac_073, fac_074", warnings)
        self.assertIn("fac_077", warnings)

    def test_no_match_can_be_retried(self):
        answers = ["n", "n", "n", "", "B", "no relevant topic", "machine learning", ""]
        with patch("builtins.input", side_effect=answers), contextlib.redirect_stdout(io.StringIO()) as output:
            interactive([record()])
        self.assertIn("No supported match", output.getvalue())
        self.assertIn("Example Faculty", output.getvalue())

    def test_demo_rejects_explicit_condition_instead_of_ignoring_it(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            main(["--demo", "--condition", "B"])
        self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
