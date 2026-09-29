import argparse
import hashlib
import html
import json
import math
import re
import statistics
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
METRICS = {
    "accuracy": {"label": "Forced accuracy", "unit": "%", "definition": "Correct highest-scoring ordinary candidates / all questions, including questions on which the controller abstains.", "numerator": "forced_correct", "denominator": "examples_per_summary", "formula": "100 * forced_correct[seed_index] / examples_per_summary"},
    "coverage": {"label": "Mapped-label coverage", "unit": "%", "definition": "Mapped true labels retained in the prediction set / all questions. A missing true answer maps to Other; covering Other does not recover that answer string.", "numerator": "covered", "denominator": "examples_per_summary", "formula": "100 * covered[seed_index] / examples_per_summary"},
    "size": {"label": "Mean set size", "unit": "labels", "definition": "Total retained labels, including Other when present, / all questions.", "numerator": "set_size_total", "denominator": "examples_per_summary", "formula": "set_size_total[seed_index] / examples_per_summary"},
    "answer": {"label": "Answer rate", "unit": "%", "definition": "Accepted ordinary singleton answers / all questions. Point baselines always output an ordinary singleton.", "numerator": "answered", "denominator": "examples_per_summary", "formula": "100 * answered[seed_index] / examples_per_summary"},
    "selective": {"label": "Selective accuracy", "unit": "%", "definition": "Correct accepted answers / accepted answers; this conditional empirical rate is not the conformal coverage guarantee.", "numerator": "accepted_correct", "denominator": "answered", "formula": "100 * accepted_correct[seed_index] / answered[seed_index]"},
    "joint_error": {"label": "Joint error", "unit": "%", "definition": "Wrong accepted answers / all questions. Abstentions remain in the denominator. Computed from counts within each seed before averaging.", "numerator": "answered - accepted_correct", "denominator": "examples_per_summary", "formula": "100 * (answered[seed_index] - accepted_correct[seed_index]) / examples_per_summary"},
    "views": {"label": "Additional acquisitions", "unit": "observations per question", "definition": "Additional acquisition rounds / all questions. Each acquisition supplies one observation to each of the two experts; the initial observation is excluded. This is not the sum of separate expert calls, latency, or token cost.", "numerator": "acquisition_total", "denominator": "examples_per_summary", "formula": "acquisition_total[seed_index] / examples_per_summary"},
    "candidate_recall": {"label": "Candidate recall", "unit": "%", "definition": "Questions whose ordinary candidate list contains the true answer / all questions. The candidate mask is shared by methods and fixed across rounds.", "numerator": "candidate_present", "denominator": "examples_per_summary", "formula": "100 * candidate_present[seed_index] / examples_per_summary"},
    "simultaneous": {"label": "All-round mapped coverage", "unit": "%", "definition": "Questions whose mapped label is covered at every potential round / all questions; distinct from coverage at the selected adaptive round.", "numerator": "simultaneous_covered", "denominator": "examples_per_summary", "formula": "100 * simultaneous_covered[seed_index] / examples_per_summary"},
    "count": {"label": "Count-query forced accuracy", "unit": "%", "definition": "Correct forced answers to count queries / count queries, calculated per seed before averaging.", "numerator": "type_correct[seed_index][0]", "denominator": "question_counts[seed_index][0]", "formula": "100 * type_correct[seed_index][0] / question_counts[seed_index][0]"},
    "direction": {"label": "Direction-query forced accuracy", "unit": "%", "definition": "Correct forced answers to relative-direction queries / relative-direction queries, calculated per seed before averaging.", "numerator": "type_correct[seed_index][1]", "denominator": "question_counts[seed_index][1]", "formula": "100 * type_correct[seed_index][1] / question_counts[seed_index][1]"},
    "nearest": {"label": "Nearest-category forced accuracy", "unit": "%", "definition": "Correct forced answers to nearest-category queries / nearest-category queries, calculated per seed before averaging.", "numerator": "type_correct[seed_index][2]", "denominator": "question_counts[seed_index][2]", "formula": "100 * type_correct[seed_index][2] / question_counts[seed_index][2]"},
}
METHODS = ["Conformal fixed (0)", "Conformal fixed (2)", "Adaptive aligned"]
DISPLAY_NAMES = {"Embodied": "Egocentric", "Conformal fixed (0)": "Fixed (0)", "Conformal fixed (2)": "Fixed (2)", "Adaptive aligned": "Adaptive"}
AGGREGATION = {"mean": "sum(per_seed_values) / number_of_seeds", "std": "sqrt(sum((value - mean) ** 2) / (number_of_seeds - 1))", "std_ddof": 1, "uncertainty": "Sample standard deviation across seeds, not a confidence interval.", "seed_index": "Array index in seeds; no pooling across seeds before calculating a metric."}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def summarize(raw):
    total = raw["examples_per_summary"]
    repeats = len(raw["seeds"])
    require(repeats >= 2 and len(set(raw["seeds"])) == repeats, "Invalid seed identifiers")
    require(isinstance(total, int) and total > 0, "Invalid example count")
    conditions = {}
    for condition, dataset in raw["conditions"].items():
        require(len(dataset["candidate_present"]) == repeats, f"{condition}: candidate count length")
        require(len(dataset["question_counts"]) == repeats, f"{condition}: question count length")
        conditions[condition] = {}
        for method, counts in dataset["methods"].items():
            require(all(len(values) == repeats for values in counts.values()), f"{condition}/{method}: count length")
            seed_metrics = []
            for index, seed in enumerate(raw["seeds"]):
                context = f"{condition}/{method}/seed={seed}"
                forced = counts["forced_correct"][index]
                answered = counts.get("answered", [total] * repeats)[index]
                correct = counts.get("accepted_correct", counts["forced_correct"])[index]
                covered = counts.get("covered", counts["forced_correct"])[index]
                candidates = dataset["candidate_present"][index]
                set_size = counts.get("set_size_total", [total] * repeats)[index]
                acquisitions = counts.get("acquisition_total", [0] * repeats)[index]
                require(all(isinstance(value, int) for value in [forced, answered, correct, covered, candidates, set_size, acquisitions]), context + ": integer counts")
                require(0 <= correct <= forced <= candidates <= total, context + ": correctness bounds")
                require(0 < answered <= total and correct <= answered, context + ": acceptance bounds")
                require(correct <= covered <= total - (answered - correct), context + ": coverage/error bounds")
                require(forced - correct <= total - answered, context + ": forced correctness outside acceptance")
                require(answered <= set_size <= answered + 8 * (total - answered), context + ": set size bounds")
                require(0 <= acquisitions <= 2 * total, context + ": acquisition budget")
                if method == "Adaptive aligned":
                    require(acquisitions >= 2 * (total - answered), context + ": abstention requires the full budget")
                if method.startswith("Conformal fixed"):
                    require(acquisitions == (0 if method.endswith("(0)") else 2 * total), context + ": fixed acquisition budget")
                type_counts = dataset["question_counts"][index]
                require(len(type_counts) == 3 and all(isinstance(value, int) and value > 0 for value in type_counts) and sum(type_counts) == total, context + ": question type counts")
                values = {
                    "accuracy": 100 * forced / total,
                    "coverage": 100 * covered / total,
                    "size": set_size / total,
                    "answer": 100 * answered / total,
                    "selective": 100 * correct / answered,
                    "joint_error": 100 * (answered - correct) / total,
                    "views": acquisitions / total,
                    "candidate_recall": 100 * candidates / total,
                }
                require(math.isclose(values["joint_error"], values["answer"] * (1 - values["selective"] / 100), abs_tol=1e-10), context + ": per-seed joint error identity")
                if "simultaneous_covered" in counts:
                    simultaneous = counts["simultaneous_covered"][index]
                    require(isinstance(simultaneous, int) and 0 <= simultaneous <= covered, context + ": all-round coverage bounds")
                    values["simultaneous"] = 100 * simultaneous / total
                if "type_correct" in counts:
                    correct_by_type = counts["type_correct"][index]
                    require(len(correct_by_type) == 3 and sum(correct_by_type) == forced, context + ": query-type correctness total")
                    for label, successes, denominator in zip(["count", "direction", "nearest"], correct_by_type, type_counts):
                        require(isinstance(successes, int) and 0 <= successes <= denominator, context + ": query-type correctness bounds")
                        values[label] = 100 * successes / denominator
                seed_metrics.append({"seed": seed, **values})
            conditions[condition][method] = {
                "display_name": DISPLAY_NAMES.get(method, method),
                "metrics": {metric: {"mean": statistics.mean(row[metric] for row in seed_metrics), "std": statistics.stdev(row[metric] for row in seed_metrics)} for metric in values},
                "per_seed": seed_metrics,
            }
        require(dataset["methods"]["Aligned fusion"]["forced_correct"] == dataset["methods"]["Conformal fixed (0)"]["forced_correct"], f"{condition}: alignment/fixed ranking mismatch")
    return conditions


def number(conditions, condition, method, metric):
    return conditions[condition][method]["metrics"][metric]["mean"]


def table(conditions, condition):
    labels = ["Method", "Forced acc. (%)", "Mapped cov. (%)", "Set size", "Answered (%)", "Selective acc. (%)", "Joint error (%)", "Extra acq."]
    columns = ["accuracy", "coverage", "size", "answer", "selective", "joint_error", "views"]
    rows = []
    for method, result in conditions[condition].items():
        highlight = ' class="highlight-row"' if method == "Adaptive aligned" else ""
        cells = []
        for metric in columns:
            values = result["metrics"][metric]
            digits = 2 if metric in ["size", "joint_error", "views"] else 1
            cells.append(f'<td data-cell="{condition}|{method}|{metric}">{values["mean"]:.{digits}f} <span class="uncertainty">± {values["std"]:.{digits}f}</span></td>')
        rows.append(f'<tr{highlight}><th scope="row">{html.escape(DISPLAY_NAMES.get(method, method))}</th>{"".join(cells)}</tr>')
    caption = "Clean observations" if condition == "test" else "Shifted observations; clean-data temperatures and thresholds retained"
    return f'<div class="table-scroll" tabindex="0" role="region" aria-label="{caption} results"><table><caption>{caption}. Mean ± sample SD across five seeds; 1,000 scenes per condition per seed.</caption><thead><tr>{"".join(f"<th scope=\"col\">{label}</th>" for label in labels)}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def result_board(conditions):
    values = conditions["test"]["Adaptive aligned"]["metrics"]
    rows = []
    for metric in ["answer", "selective", "coverage", "joint_error"]:
        entry = values[metric]
        color = " amber" if metric == "joint_error" else ""
        rows.append(f'<div class="metric-row" data-metric="{metric}"><div class="metric-label"><span>{METRICS[metric]["label"]}</span><span><strong class="metric-number">{entry["mean"]:.2f}%</strong> <small class="metric-sd">± {entry["std"]:.2f}</small></span></div><div class="metric-track{color}"><span class="metric-fill" style="width:{entry["mean"]:.6f}%"></span>{"<i class=\"target-marker\" title=\"Nominal clean-distribution target: 90%\"></i>" if metric == "coverage" else ""}</div></div>')
    return "\n".join(rows)


def alignment_chart(conditions):
    rows = []
    for method in ["Embodied", "Global", "Unscaled fusion", "Aligned fusion"]:
        values = conditions["test"][method]["metrics"]["accuracy"]
        rows.append(f'<div class="alignment-row"><span>{html.escape(DISPLAY_NAMES.get(method, method))}</span><div class="alignment-track"><span style="width:{values["mean"]}%" class="{"is-aligned" if method == "Aligned fusion" else ""}"></span></div><strong>{values["mean"]:.1f}% <small>± {values["std"]:.1f}</small></strong></div>')
    return "\n".join(rows)


def source_mapping(condition, method, metric):
    method_path = f"/conditions/{condition}/methods/{method}"
    dataset_path = f"/conditions/{condition}"
    point_baseline = method not in METHODS
    formula = METRICS[metric]["formula"]
    fields = {
        "accuracy": [method_path + "/forced_correct", "/examples_per_summary"],
        "coverage": [method_path + "/covered", "/examples_per_summary"],
        "size": [method_path + "/set_size_total", "/examples_per_summary"],
        "answer": [method_path + "/answered", "/examples_per_summary"],
        "selective": [method_path + "/accepted_correct", method_path + "/answered"],
        "joint_error": [method_path + "/answered", method_path + "/accepted_correct", "/examples_per_summary"],
        "views": [method_path + "/acquisition_total", "/examples_per_summary"],
        "candidate_recall": [dataset_path + "/candidate_present", "/examples_per_summary"],
        "simultaneous": [method_path + "/simultaneous_covered", "/examples_per_summary"],
        "count": [method_path + "/type_correct", dataset_path + "/question_counts"],
        "direction": [method_path + "/type_correct", dataset_path + "/question_counts"],
        "nearest": [method_path + "/type_correct", dataset_path + "/question_counts"],
    }[metric]
    table_number = 1 if condition == "test" else 2
    locations = [{"label": f"Table {table_number}", "page": 6, "source": "sections/experiments.tex"}]
    reporting = "Reported in the manuscript table."
    if metric in ["views", "joint_error"]:
        if point_baseline:
            locations.append({"label": "Section 4.1, Compared methods and Metrics", "page": 5, "source": "sections/experiments.tex"})
            reporting = "Derived from the initial-observation point-baseline protocol and forced-answer counts; not a row of Table 4."
        else:
            locations = [{"label": "Appendix C, Table 4", "page": 11, "source": "sections/appendix.tex"}]
    elif metric == "candidate_recall":
        locations = [{"label": "Section 4.1, candidate-generation protocol", "page": 5, "source": "sections/experiments.tex"}, {"label": "Appendix C, Geometry and randomness", "page": 10, "source": "sections/appendix.tex"}]
        reporting = "The clean mean and sample SD are reported in Section 4.1; the shifted value is derived from the accompanying candidate_present counts. Candidate recall is shared by all methods."
    elif metric in ["simultaneous", "count", "direction", "nearest"]:
        locations = [{"label": "Appendix C, Additional results after Table 4", "page": 11, "source": "sections/appendix.tex"}]
        reporting = "The mean is reported in Appendix C; the sample SD is derived from the accompanying per-seed counts."
    representation = "Adaptive values use the first accepted round, or round 2 after abstention." if method == "Adaptive aligned" else "Fixed-round values use the declared round."
    if point_baseline:
        representation = "Section 4.1 represents every point prediction as an ordinary singleton: covered = accepted_correct = forced_correct; answered = set_size_total = examples_per_summary; acquisition_total = 0. These defaults are protocol-derived, not missing raw measurements."
        if metric in ["coverage", "selective"]:
            formula = "100 * forced_correct[seed_index] / examples_per_summary"
            fields = [method_path + "/forced_correct", "/examples_per_summary"]
        elif metric == "joint_error":
            formula = "100 * (examples_per_summary - forced_correct[seed_index]) / examples_per_summary"
            fields = [method_path + "/forced_correct", "/examples_per_summary"]
        elif metric in ["answer", "size", "views"]:
            formula = {"answer": "100 * examples_per_summary / examples_per_summary", "size": "examples_per_summary / examples_per_summary", "views": "0 / examples_per_summary"}[metric]
            fields = ["/examples_per_summary"]
    return {
        "counts": f"conditions.{condition}.methods.{method}",
        "raw_file": "private manuscript aggregate counts",
        "raw_fields": fields,
        "metric_definition": f"results.json:metrics.{metric}",
        "seed_formula": formula,
        "unit": METRICS[metric]["unit"],
        "aggregation": AGGREGATION,
        "paper_location": "; ".join(f'{location["label"]}, p. {location["page"]}' for location in locations),
        "paper_locations": locations,
        "reporting": reporting,
        "evaluation_protocol": representation,
    }


def verify_source_resources(raw, conditions):
    with zipfile.ZipFile(ROOT / "paper" / "Tame3D_source.zip") as archive:
        require(archive.read("data/table_data.json") == (ROOT / "paper" / "source" / "data" / "table_data.json").read_bytes(), "Summary counts differ from the unchanged source archive")
        require(archive.read("iclr2025_conference.tex") == (ROOT / "paper" / "source" / "iclr2025_conference.tex").read_bytes(), "Main LaTeX file differs from the source archive")
        manuscript_summary = json.loads(archive.read("generated/table_summary.json"))
        for condition, methods in conditions.items():
            for method, result in methods.items():
                for metric, statistics_values in result["metrics"].items():
                    for statistic, value in statistics_values.items():
                        require(math.isclose(value, manuscript_summary[condition][method][metric][statistic], abs_tol=1e-12), f"Manuscript statistic mismatch: {condition}/{method}/{metric}/{statistic}")
    require(raw["seeds"] == [17, 29, 43, 71, 101] and raw["examples_per_summary"] == 1000, "Published manuscript seed or split configuration changed; update source mappings and study metadata")


def main():
    parser = argparse.ArgumentParser(description="Build or verify the static page and browser data from manuscript summary counts.")
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    raw = json.loads((ROOT / "paper" / "source" / "data" / "table_data.json").read_text(encoding="utf-8"))
    conditions = summarize(raw)
    verify_source_resources(raw, conditions)
    clean = lambda method, metric: number(conditions, "test", method, metric)
    derived = {
        "alignment_gain_pp": clean("Aligned fusion", "accuracy") - clean("Unscaled fusion", "accuracy"),
        "acquisition_saving_percent": 100 * (1 - clean("Adaptive aligned", "views") / clean("Conformal fixed (2)", "views")),
        "coverage_drop_pp": clean("Adaptive aligned", "coverage") - number(conditions, "shift", "Adaptive aligned", "coverage"),
    }
    results = {
        "schema_version": 1,
        "source": "Accompanying Tame3D manuscript and its per-seed aggregate counts",
        "seeds": raw["seeds"],
        "split_sizes_per_seed": {"development": 400, "calibration": 600, "test": 1000, "shift": 1000},
        "questions_per_scene": 1,
        "aggregation": "Calculate each seed's metric, then arithmetic mean and sample standard deviation (ddof=1).",
        "aggregation_formulas": AGGREGATION,
        "evaluation_protocol": {
            "point_baselines": "Initial-observation ordinary singleton predictions. Coverage and selective accuracy equal forced accuracy; answer rate is 100%, set size is 1, and additional acquisitions are 0.",
            "fixed": "Evaluate at the declared round; Fixed (2) always uses two additional observations per expert.",
            "adaptive": "Evaluate at the first accepted round, or at round 2 after abstention.",
            "risk_allocation": "Total alpha = 0.10. Each fixed rule uses alpha at one round; Adaptive uses alpha / 3 at each of rounds 0, 1, 2.",
            "shift": "Retention probabilities decrease by 0.20; position-noise SDs multiply by 1.7; yaw-noise SDs multiply by 2.5. Predictive draws use shifted noise scales, while clean-data temperatures and thresholds remain fixed.",
        },
        "metrics": METRICS,
        "conditions": {condition: {method: {key: value for key, value in result.items() if key != "per_seed"} for method, result in methods.items()} for condition, methods in conditions.items()},
        "derived": derived,
    }
    mappings = {}
    for condition, methods in conditions.items():
        for method, result in methods.items():
            for metric in result["metrics"]:
                mappings[f"{condition}/{method}/{metric}"] = source_mapping(condition, method, metric)
    evidence = {
        "schema_version": 1,
        "authoritative_version": "Local published-format Tame3D manuscript, 11 pages, and matching source archive; selected by the authors for this website.",
        "artifacts": {"tame3d-paper.pdf": {"sha256": hashlib.sha256((ASSETS / "tame3d-paper.pdf").read_bytes()).hexdigest()}},
        "counts_origin": "Private manuscript aggregate counts, retained locally by the authors and not published on this site.",
        "source_notation": "raw_fields are JSON Pointers into the private manuscript aggregate counts. seed_index refers to the matching position in seeds. paper_locations.source paths identify private manuscript source files. Page numbers refer to the unchanged 11-page PDF.",
        "numerical_sources": mappings,
        "derived_formulas": {
            "alignment_gain_pp": "test.Aligned fusion.accuracy.mean - test.Unscaled fusion.accuracy.mean",
            "acquisition_saving_percent": "100 * (1 - test.Adaptive aligned.views.mean / test.Conformal fixed (2).views.mean)",
            "coverage_drop_pp": "test.Adaptive aligned.coverage.mean - shift.Adaptive aligned.coverage.mean",
        },
        "derived_sources": {
            "alignment_gain_pp": {"unit": "percentage points", "inputs": ["test/Aligned fusion/accuracy", "test/Unscaled fusion/accuracy"], "paper_locations": [{"label": "Abstract", "page": 1, "source": "iclr2025_conference.tex"}, {"label": "Section 4.2", "page": 5, "source": "sections/experiments.tex"}, {"label": "Table 1", "page": 6, "source": "sections/experiments.tex"}]},
            "acquisition_saving_percent": {"unit": "%", "inputs": ["test/Adaptive aligned/views", "test/Conformal fixed (2)/views"], "paper_locations": [{"label": "Abstract", "page": 1, "source": "iclr2025_conference.tex"}, {"label": "Appendix C, Table 4 and Metric aggregation", "page": 11, "source": "sections/appendix.tex"}]},
            "coverage_drop_pp": {"unit": "percentage points", "inputs": ["test/Adaptive aligned/coverage", "shift/Adaptive aligned/coverage"], "paper_locations": [{"label": "Section 4.3 and Tables 1 and 2", "page": 6, "source": "sections/experiments.tex"}]},
        },
        "derived_aggregation": "All differences and savings use unrounded means. Joint error is computed within each seed directly from counts; multiplying separately averaged answer rate and error among answered questions is not used.",
        "study_metadata": {"seeds": {"value": raw["seeds"], "raw_fields": ["/seeds"], "paper_location": "Appendix C, Geometry and randomness, p. 10"}, "split_sizes_per_seed": {"value": results["split_sizes_per_seed"], "paper_location": "Section 4.1, p. 5"}, "questions_per_scene": {"value": 1, "paper_location": "Section 4.1, p. 5; Appendix C, p. 10"}, "sample_sd": {"formula": AGGREGATION["std"], "ddof": 1, "paper_location": "Appendix C, Metric aggregation, p. 11"}},
        "non_results": {"scene": "Constructed illustration of Appendix B: chair (-1,2,0), table (1,2,0), observer at origin and R=I.", "controller": "Constructed set-membership examples implementing Section 3.4, not recorded model outputs or measured confidence scores."},
        "limits": ["Aggregate-statistic verification does not reproduce the simulation.", "The source archive does not include simulator or per-scene predictions.", "The experiments evaluate synthetic geometric estimators, not a complete foundation-model system or SQA3D benchmark.", "Risk guarantee requires exchangeable scene blocks and all development choices frozen before calibration.", "Adaptive versus final fixed-round results differ in both stopping and risk allocation."],
    }
    values = {
        "hero_selective": f'{clean("Adaptive aligned", "selective"):.2f}',
        "hero_answer": f'{clean("Adaptive aligned", "answer"):.2f}',
        "hero_saving": f'{derived["acquisition_saving_percent"]:.2f}',
        "alignment_gain": f'{derived["alignment_gain_pp"]:.2f}',
        "clean_coverage": f'{clean("Adaptive aligned", "coverage"):.2f}',
        "shift_coverage": f'{number(conditions, "shift", "Adaptive aligned", "coverage"):.2f}',
        "coverage_drop": f'{derived["coverage_drop_pp"]:.2f}',
        "clean_cost": f'{clean("Adaptive aligned", "views"):.2f}',
        "clean_cost_sd": f'{conditions["test"]["Adaptive aligned"]["metrics"]["views"]["std"]:.2f}',
        "clean_cost_width": f'{50 * clean("Adaptive aligned", "views"):.6f}',
        "fixed_answer": f'{clean("Conformal fixed (2)", "answer"):.2f}',
        "fixed_selective": f'{clean("Conformal fixed (2)", "selective"):.2f}',
        "clean_table": table(conditions, "test"),
        "shift_table": table(conditions, "shift"),
        "result_board": result_board(conditions),
        "alignment_chart": alignment_chart(conditions),
        "citation": html.escape((ASSETS / "citation.bib").read_text(encoding="utf-8").strip()),
    }
    template = (ROOT / "scripts" / "page.html").read_text(encoding="utf-8")
    page = re.sub(r"\{\{([a-z_]+)\}\}", lambda match: values[match.group(1)], template)
    assert not re.search(r"\{\{[a-z_]+\}\}", page)
    serialized = json.dumps(results, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    outputs = {
        ROOT / "index.html": page,
        ASSETS / "results.json": serialized,
        ASSETS / "results.js": "window.TAME3D_RESULTS = " + serialized.rstrip() + ";\n",
        ASSETS / "evidence.json": json.dumps(evidence, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
    }
    for path, content in outputs.items():
        if arguments.check:
            if path.read_text(encoding="utf-8") != content:
                raise SystemExit(f"Stale generated file: {path.relative_to(ROOT)}")
        else:
            path.write_text(content, encoding="utf-8", newline="\n")
    print(f"PASS: {len(outputs)} synchronized outputs; {len(mappings)} source mappings; five-seed arithmetic means and sample SDs.")


if __name__ == "__main__":
    main()
