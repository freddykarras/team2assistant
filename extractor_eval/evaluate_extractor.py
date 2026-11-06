"""
evaluate_extractor.py -- Team 2 Stage 3 (keyword extractor) evaluation.
Owner: Mrithika.

Run from the repository root (this file lives in extractor_eval/):
    python extractor_eval/evaluate_extractor.py extractor_eval/eval_set.json extractor_eval/results

What it compares (same preprocessing, same vocabulary, same statements):
  EXTRACTOR  = keyword_extractor.extract_keywords as shipped
  BASELINE   = the same function with the taxonomy switched off, i.e. plain
               keyword search that only finds faculty-vocabulary phrases
               verbatim in the student's text

Gold labels: each statement lists the vocabulary phrases a human would accept
as reflecting the stated interest (an "acceptable set"), or [] when the
statement states no research interest (correct answer = return no tags).

Metrics (positives = statements with a non-empty acceptable set):
  hit rate       share of positives where >= 1 returned tag is acceptable
  tag precision  returned tags that are acceptable / all returned tags
  zero-tag rate  share of positives where nothing was returned
  abstention     share of no-interest statements where nothing was returned
"""
import csv
import json
import math
import os
import subprocess
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root
import keyword_extractor as k


def wilson(successes, n, z=1.96):
    """95% Wilson score interval for a proportion."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = successes / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def mcnemar_exact(b, c):
    """Two-sided exact McNemar p-value from the discordant pairs b and c."""
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(0, min(b, c) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def run(system, text):
    if system == "BASELINE":
        saved = k.TAXONOMY
        k.TAXONOMY = {}
        try:
            return k.extract_keywords(text)
        finally:
            k.TAXONOMY = saved
    return k.extract_keywords(text)


def fmt(successes, n):
    lo, hi = wilson(successes, n)
    return f"{successes}/{n} = {100*successes/n:.0f}%  (95% CI {100*lo:.0f}-{100*hi:.0f}%)" if n else "n/a"


def main():
    eval_path = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "extractor_eval_out"
    os.makedirs(out_dir, exist_ok=True)
    items = json.load(open(eval_path, encoding="utf-8"))
    vocab = set(k.load_vocab())

    bad = sorted({g for it in items for g in it["gold"] if g not in vocab})
    if bad:
        sys.exit(f"Gold labels not in faculty vocabulary: {bad}")

    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        commit = "unknown"

    rows, stats = [], {s: defaultdict(lambda: [0, 0]) for s in ("EXTRACTOR", "BASELINE")}
    hits = {"EXTRACTOR": {}, "BASELINE": {}}
    tag_total = {s: [0, 0] for s in stats}          # [acceptable, returned]
    for it in items:
        gold = set(it["gold"])
        row = {"id": it["id"], "type": it["type"], "text": it["text"], "gold": "; ".join(it["gold"])}
        for s in ("EXTRACTOR", "BASELINE"):
            tags = run(s, it["text"])
            row[f"{s.lower()}_tags"] = "; ".join(tags)
            if gold:
                hit = bool(gold & set(tags))
                hits[s][it["id"]] = hit
                stats[s][it["type"]][0] += hit
                stats[s][it["type"]][1] += 1
                stats[s]["ALL"][0] += hit
                stats[s]["ALL"][1] += 1
                stats[s]["ZERO"][0] += (not tags)
                stats[s]["ZERO"][1] += 1
                tag_total[s][0] += sum(t in gold for t in tags)
                tag_total[s][1] += len(tags)
                row[f"{s.lower()}_hit"] = int(hit)
            else:
                ok = not tags
                stats[s]["ABSTAIN"][0] += ok
                stats[s]["ABSTAIN"][1] += 1
                row[f"{s.lower()}_hit"] = ""
                row[f"{s.lower()}_abstained_correctly"] = int(ok)
        rows.append(row)

    fields = ["id", "type", "text", "gold", "extractor_tags", "extractor_hit",
              "baseline_tags", "baseline_hit", "extractor_abstained_correctly",
              "baseline_abstained_correctly"]
    with open(os.path.join(out_dir, "per_statement_results.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    n_pos = stats["EXTRACTOR"]["ALL"][1]
    lines = [f"Commit: {commit}   Statements: {len(items)} ({n_pos} with an interest, "
             f"{stats['EXTRACTOR']['ABSTAIN'][1]} with none)", ""]
    lines.append(f"{'Metric':34} {'EXTRACTOR':44} BASELINE (keyword search)")
    for label, key in (("Hit rate (>=1 acceptable tag)", "ALL"), ("Zero-tag rate (positives)", "ZERO"),
                       ("Abstention (no-interest stmts)", "ABSTAIN")):
        lines.append(f"{label:34} {fmt(*stats['EXTRACTOR'][key]):44} {fmt(*stats['BASELINE'][key])}")
    pe = tag_total["EXTRACTOR"]; pb = tag_total["BASELINE"]
    lines.append(f"{'Tag precision':34} {fmt(*pe):44} {fmt(*pb)}")

    b = sum(hits["EXTRACTOR"][i] and not hits["BASELINE"][i] for i in hits["EXTRACTOR"])
    c = sum(hits["BASELINE"][i] and not hits["EXTRACTOR"][i] for i in hits["EXTRACTOR"])
    lines += ["", f"Paired hit comparison: extractor-only hits = {b}, baseline-only hits = {c}, "
                  f"exact McNemar p = {mcnemar_exact(b, c):.4f}", "", "Hit rate by statement type:"]
    for t in sorted(t for t in stats["EXTRACTOR"] if t not in ("ALL", "ZERO", "ABSTAIN")):
        lines.append(f"  {t:11} extractor {fmt(*stats['EXTRACTOR'][t]):44} baseline {fmt(*stats['BASELINE'][t])}")

    lines += ["", "Extractor failures (positives with no acceptable tag, plus unacceptable tags returned):"]
    for r, it in zip(rows, items):
        gold = set(it["gold"])
        tags = [t for t in r["extractor_tags"].split("; ") if t]
        wrong = [t for t in tags if gold and t not in gold]
        if (gold and not r["extractor_hit"]) or wrong or (not gold and tags):
            lines.append(f"  {r['id']} [{r['type']}] {r['text']}\n      returned: {tags or '[]'}   unacceptable: {wrong or ('all' if (not gold and tags) else '-')}")
    report = "\n".join(lines)
    open(os.path.join(out_dir, "summary.txt"), "w", encoding="utf-8").write(report + "\n")
    print(report)


if __name__ == "__main__":
    main()
