# Stage 3 Keyword Extractor: Evaluation (Week 9)

**Owner:** Mrithika  **Code version:** commit `75f7a66`  **Question (RQ1):** Does structured keyword extraction map student interest text to the faculty keyword vocabulary more accurately than standard keyword search?

## Method
- **Systems compared (same text preprocessing, same vocabulary):**
  - *Extractor*: `keyword_extractor.extract_keywords` as shipped (verbatim vocabulary matches plus the hand-built taxonomy).
  - *Baseline*: the same function with the taxonomy switched off, i.e. plain keyword search for faculty-vocabulary phrases in the student's text.
- **Test set:** 48 fictional student statements (`eval_set.json`): 12 direct-term, 16 paraphrase (no vocabulary words), 8 multi-interest/specialised, 5 project-wording, 2 negation, 5 with no stated interest. No real student text was used.
- **Labels:** for each statement, the set of vocabulary phrases a human would accept as reflecting the stated interest (empty for no-interest statements, where the correct output is no tags).
- **Metrics:** hit rate (at least one acceptable tag returned), tag precision, zero-tag rate, abstention on no-interest statements. 95% Wilson intervals; exact McNemar test for the paired hit comparison.
- **Procedure:** one run, results reported as obtained. The taxonomy was not tuned to this set.
- **Reproduce:** `python extractor_eval/evaluate_extractor.py extractor_eval/eval_set.json extractor_eval/results` from the repository root (results in `extractor_eval/results/`).

## Results (43 statements with an interest, 5 without)
| Metric | Extractor | Baseline (keyword search) |
|---|---|---|
| Hit rate | 26/43 = 60% (95% CI 46-74%) | 21/43 = 49% (35-63%) |
| Zero-tag rate | 14/43 = 33% (20-47%) | 18/43 = 42% (28-57%) |
| Tag precision | 44/54 = 81% (69-90%) | 26/32 = 81% (65-91%) |
| Abstention (no-interest) | 5/5 | 5/5 |

Paired comparison: the extractor matched 5 statements the baseline missed and the baseline matched none the extractor missed (exact McNemar p = 0.0625, not significant at 0.05).

| Statement type | n | Extractor hit rate | Baseline hit rate |
|---|---|---|---|
| Direct term | 12 | 12/12 | 12/12 |
| Paraphrase | 16 | 2/16 (12%) | 2/16 (12%) |
| Multi-interest / specialised | 8 | 6/8 (75%) | 3/8 (38%) |
| Project wording | 5 | 4/5 (80%) | 2/5 (40%) |
| Negation | 2 | 2/2 | 2/2 |

**Reading the results:** the taxonomy helps where students name specific tools, projects, or several interests, and gives no benefit on paraphrased interests. The direction favors the extractor, but the sample is small and the overall difference is not statistically significant.

## Failure analysis
| Cause | Statements | Count | Proposed fix |
|---|---|---|---|
| Paraphrase with no matching rule returns no tags | s13, s15-s21, s23, s25, s26, s33, s34, s48 | 14 | Add a paraphrase layer (more rules, or LLM-assisted extraction evaluated for reproducibility), then test on a held-out set |
| Generic vocabulary word matched alone ("systems", "software") | s14, s22, s24 | 3 | Require corroborating context for generic single words |
| "neural networks" also triggers "networks" / "wireless networks" | s01 | 1 | Let longer phrases suppress generic overlaps |
| Rule maps "operating systems" to "storage systems" | s07 | 1 | Correct the rule |
| Junk dataset keyword "file" matched | s46 | 1 | Remove "file" and "i/o" from the dataset (Sindhu) |
| Negation scope too narrow ("...but I don't enjoy it") | s38 | 1 | Extend negation handling |
| Label-dependent (arguably acceptable) | s10 ("applied cryptography"), s28 ("artificial intelligence") | 2 | Second labeler to settle |

## Limitations
- Statements and labels come from one author, who knew the taxonomy while writing them. This is a development set, not independent evidence. The mix of statement types was chosen by the author, so the overall percentages are not an estimate of accuracy on real students; the by-type rows are more informative.
- A single labeler; no inter-rater agreement has been measured.
- Small sample (n = 48), wide intervals.
- The baseline is keyword search over the faculty vocabulary, not a general search engine or an LLM.
- Tag-level only: retrieval ranking and faculty relevance were not evaluated.
- Next step before the poster: teammates write 15-20 statements blind to the taxonomy, a second person labels them, and the fixes above are evaluated on that held-out set.

## Claims
- **Supported now:** on this development set the extractor recovers an acceptable tag for 60% of statements versus 49% for plain keyword search, with the gains concentrated in multi-interest and project wording.
- **Not yet supported:** that the extractor generalizes to real students' own wording, or that it beats keyword search in a statistically reliable way. It currently returns no tags for about one in three interests, mostly paraphrases.
