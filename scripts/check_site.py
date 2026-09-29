import hashlib
import json
import math
import re
import statistics
import subprocess
import sys
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
TABLE_METRICS = {"accuracy", "coverage", "size", "answer", "selective", "joint_error", "views"}
AUTHORS = ["Yirong Qiang", "Xi Hong", "Zhewei Li", "Yuling Zheng", "Yi Lu", "Yilun Chen"]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def close(actual, expected, context):
    require(isinstance(actual, (int, float)) and math.isfinite(actual), f"{context}: nonfinite value")
    require(math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), f"{context}: {actual} != {expected}")


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.links = []
        self.references = []
        self.images = []
        self.cells = {}
        self.cell = None
        self.authors = []
        self.language = None
        self.feed(text)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == "html":
            self.language = attrs.get("lang")
        if "id" in attrs:
            require(attrs["id"] not in self.ids, f"Duplicate HTML id: {attrs['id']}")
            self.ids.add(attrs["id"])
        if tag == "meta" and attrs.get("name") == "citation_author":
            self.authors.append(attrs.get("content"))
        for key in ("href", "src", "poster"):
            if key in attrs:
                self.links.append((tag, key, attrs[key], attrs))
        if "srcset" in attrs:
            self.links.extend((tag, "srcset", entry.strip().split()[0], attrs) for entry in attrs["srcset"].split(","))
        for key in ("aria-controls", "aria-labelledby", "aria-describedby"):
            self.references.extend(attrs.get(key, "").split())
        if tag == "img":
            self.images.append(attrs)
        if "data-cell" in attrs:
            require(tag == "td", "A generated table data-cell must be on a td element")
            self.cell = attrs["data-cell"]
            require(self.cell not in self.cells, f"Duplicate table data-cell: {self.cell}")
            self.cells[self.cell] = ""

    def handle_endtag(self, tag):
        if tag == "td":
            self.cell = None

    def handle_data(self, data):
        if self.cell is not None:
            self.cells[self.cell] += data


def check_links(page):
    for tag, attribute, value, attrs in page.links:
        require(value.strip() == value and value, f"Empty or padded {attribute}")
        target = urlsplit(value)
        if target.scheme or target.netloc:
            require(target.scheme == "https", f"Unexpected URL scheme: {value}")
            require(tag not in {"script", "img", "source"}, f"External runtime asset: {value}")
            require(not (tag == "link" and attrs.get("rel") == "stylesheet"), f"External stylesheet: {value}")
            continue
        require(not target.path.startswith("/"), f"Root-relative URL breaks project Pages: {value}")
        file_path = (ROOT / unquote(target.path or "index.html")).resolve()
        require(file_path.is_relative_to(ROOT), f"Link escapes website directory: {value}")
        require(file_path.is_file(), f"Missing local resource: {value}")
        if target.fragment and file_path.suffix == ".html":
            linked_page = page if file_path == ROOT / "index.html" else Page(file_path.read_text(encoding="utf-8"))
            require(unquote(target.fragment) in linked_page.ids, f"Missing local fragment: {value}")
        if "download" in attrs:
            require(file_path.stat().st_size > 0, f"Empty download: {value}")
        if "resource" in attrs.get("class", "").split():
            require(target.path, f"Placeholder resource link: {value}")
    for reference in page.references:
        require(reference in page.ids, f"Missing ARIA target: {reference}")
    for image in page.images:
        require("alt" in image, f"Image missing alt text: {image.get('src')}")
        if image.get("id") != "dialog-image":
            require(all(image.get(key, "").isdigit() for key in ("width", "height")), f"Image dimensions missing: {image.get('src')}")
        if image.get("src", "").endswith(("framework.png", "observation-shift.webp")) and image.get("id") != "dialog-image":
            require(image.get("loading") == "lazy", f"Non-hero figure must load lazily: {image.get('src')}")
    css = (ROOT / "styles.css").read_text(encoding="utf-8")
    require(not re.search(r"@import\b|https?://", css), "Stylesheet has an external runtime dependency")
    for reference in re.findall(r"url\(\s*['\"]?([^)'\"]+)", css):
        if not reference.startswith(("#", "data:")):
            require((ROOT / reference).is_file(), f"Missing CSS asset: {reference}")


def expected_seed_metrics(raw, dataset, counts, index):
    total = raw["examples_per_summary"]
    repeats = len(raw["seeds"])
    forced = counts["forced_correct"][index]
    answered = counts.get("answered", [total] * repeats)[index]
    accepted = counts.get("accepted_correct", counts["forced_correct"])[index]
    values = {
        "accuracy": 100 * forced / total,
        "coverage": 100 * counts.get("covered", counts["forced_correct"])[index] / total,
        "size": counts.get("set_size_total", [total] * repeats)[index] / total,
        "answer": 100 * answered / total,
        "selective": 100 * accepted / answered,
        "joint_error": 100 * (answered - accepted) / total,
        "views": counts.get("acquisition_total", [0] * repeats)[index] / total,
        "candidate_recall": 100 * dataset["candidate_present"][index] / total,
    }
    if "simultaneous_covered" in counts:
        values["simultaneous"] = 100 * counts["simultaneous_covered"][index] / total
    if "type_correct" in counts:
        for question_index, metric in enumerate(("count", "direction", "nearest")):
            values[metric] = 100 * counts["type_correct"][index][question_index] / dataset["question_counts"][index][question_index]
    return values


def check_statistics(raw, results, page):
    require(raw["seeds"] == results["seeds"] == [17, 29, 43, 71, 101], "Incorrect seed identities")
    require(raw["examples_per_summary"] == 1000, "Incorrect evaluation split size")
    require(results["split_sizes_per_seed"] == {"development": 400, "calibration": 600, "test": 1000, "shift": 1000}, "Incorrect scene splits")
    require(results["questions_per_scene"] == 1, "Incorrect questions per scene")
    expected_cells = set()
    expected_sources = set()
    require(results["conditions"].keys() == raw["conditions"].keys(), "Condition mismatch")
    for condition, dataset in raw["conditions"].items():
        require(results["conditions"][condition].keys() == dataset["methods"].keys(), f"{condition}: method mismatch")
        for method, counts in dataset["methods"].items():
            result = results["conditions"][condition][method]
            rows = [expected_seed_metrics(raw, dataset, counts, index) for index in range(len(raw["seeds"]))]
            require("per_seed" not in result, f"{condition}/{method}: per-seed data must not be published")
            require(set(result["metrics"]) == set(rows[0]), f"{condition}/{method}: metric keys")
            for metric in rows[0]:
                context = f"{condition}/{method}/{metric}"
                expected_sources.add(context)
                definition = results["metrics"][metric]
                require(all(definition.get(field) for field in ("label", "unit", "definition", "formula")), f"{context}: incomplete definition")
                values = [row[metric] for row in rows]
                close(result["metrics"][metric]["mean"], statistics.mean(values), context + "/mean")
                close(result["metrics"][metric]["std"], statistics.stdev(values), context + "/sample SD")
                if metric in TABLE_METRICS:
                    key = f"{condition}|{method}|{metric}"
                    expected_cells.add(key)
                    require(key in page.cells, f"Missing static table cell: {key}")
                    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*±\s*(\d+(?:\.\d+)?)\s*", page.cells[key])
                    require(match is not None, f"Invalid static table number: {key}")
                    for field, displayed in zip(("mean", "std"), match.groups()):
                        precision = len(displayed.split(".")[1]) if "." in displayed else 0
                        require(displayed == f"{result['metrics'][metric][field]:.{precision}f}", f"Stale static table number: {key}/{field}")
    require(set(page.cells) == expected_cells, "Unexpected or incomplete static data table cells")
    clean = results["conditions"]["test"]
    derived = {
        "alignment_gain_pp": clean["Aligned fusion"]["metrics"]["accuracy"]["mean"] - clean["Unscaled fusion"]["metrics"]["accuracy"]["mean"],
        "acquisition_saving_percent": 100 * (1 - clean["Adaptive aligned"]["metrics"]["views"]["mean"] / clean["Conformal fixed (2)"]["metrics"]["views"]["mean"]),
        "coverage_drop_pp": clean["Adaptive aligned"]["metrics"]["coverage"]["mean"] - results["conditions"]["shift"]["Adaptive aligned"]["metrics"]["coverage"]["mean"],
    }
    require(derived.keys() == results["derived"].keys(), "Derived metric mismatch")
    for metric, value in derived.items():
        close(results["derived"][metric], value, "derived/" + metric)
    return expected_sources


def resolve_pointer(document, pointer):
    require(pointer.startswith("/"), f"Invalid source JSON Pointer: {pointer}")
    value = document
    for component in pointer[1:].split("/"):
        key = component.replace("~1", "/").replace("~0", "~")
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def check_evidence(raw, results, evidence, sources):
    require(set(evidence["numerical_sources"]) == sources, "Incomplete numerical source mappings")
    require("code_version_difference" not in evidence, "Historical code values must not be included")
    require(set(evidence["artifacts"]) == {"tame3d-paper.pdf"}, "Only the paper PDF may have a public artifact hash")
    for name, entry in evidence["artifacts"].items():
        source_path = (ASSETS / name).resolve()
        require(source_path.is_relative_to(ASSETS) and source_path.is_file(), f"Invalid artifact path: {name}")
        require(hashlib.sha256(source_path.read_bytes()).hexdigest() == entry["sha256"], f"Artifact hash mismatch: {name}")
    require(results["derived"].keys() == evidence["derived_formulas"].keys(), "Derived formulas are incomplete")
    with zipfile.ZipFile(ROOT / "paper" / "Tame3D_source.zip") as archive:
        require(archive.testzip() is None, "Corrupt source ZIP")
        require(archive.read("data/table_data.json") == (ROOT / "paper" / "source" / "data" / "table_data.json").read_bytes(), "Counts differ from source ZIP")
        require(archive.read("iclr2025_conference.tex") == (ROOT / "paper" / "source" / "iclr2025_conference.tex").read_bytes(), "Main source differs from source ZIP")
        names = set(archive.namelist())
        for key, mapping in evidence["numerical_sources"].items():
            require(mapping.get("seed_formula") and mapping.get("aggregation"), f"Missing calculation mapping: {key}")
            require(mapping.get("raw_fields"), f"Missing raw field mapping: {key}")
            for pointer in mapping["raw_fields"]:
                resolve_pointer(raw, pointer)
            require(mapping.get("paper_locations"), f"Missing manuscript location: {key}")
            for location in mapping["paper_locations"]:
                require(location.get("label") and 1 <= location.get("page", 0) <= 11, f"Invalid paper location: {key}")
                require(location.get("source") in names, f"Missing manuscript source: {key}")
    require((ASSETS / "tame3d-paper.pdf").read_bytes() == (ROOT / "paper" / "Tame3D.pdf").read_bytes(), "Publication PDF differs from preserved local original")
    for name in ("tame3d-source.zip", "main.tex", "summary-counts.json"):
        require(not (ASSETS / name).exists(), f"Private source file is still in public assets: {name}")
    print("PASS: public PDF matches the local original; manuscript source and raw counts remain private.")


def main():
    require((ROOT / "index.html").exists(), "Run python scripts/build.py before checking the site")
    subprocess.run([sys.executable, str(ROOT / "scripts/build.py"), "--check"], cwd=ROOT, check=True)
    text = (ROOT / "index.html").read_text(encoding="utf-8")
    require(not re.search(r"\{\{[^}]+\}\}|\bTODO\b|\bFIXME\b|example\.com|lorem ipsum", text, re.IGNORECASE), "Unresolved page placeholder")
    require("historical reference results" not in text.lower(), "Historical code values must not appear on the page")
    page = Page(text)
    require(page.language == "en", "The page must declare English")
    require(page.authors == AUTHORS, "Author order differs from the supplied paper")
    require({"main", "motivation", "method", "explore", "results", "evidence", "resources"} <= page.ids, "Required page section missing")
    require("<noscript>" in text and len(page.cells) > 0, "No-JavaScript explanations and data are required")
    check_links(page)
    raw = json.loads((ROOT / "paper" / "source" / "data" / "table_data.json").read_text(encoding="utf-8"))
    results = json.loads((ASSETS / "results.json").read_text(encoding="utf-8"))
    evidence = json.loads((ASSETS / "evidence.json").read_text(encoding="utf-8"))
    browser_data = (ASSETS / "results.js").read_text(encoding="utf-8")
    require(browser_data.startswith("window.TAME3D_RESULTS = ") and browser_data.rstrip().endswith(";"), "Unexpected browser-data wrapper")
    require(json.loads(browser_data[len("window.TAME3D_RESULTS = "):].rstrip().removesuffix(";")) == results, "Browser data differs from JSON")
    sources = check_statistics(raw, results, page)
    check_evidence(raw, results, evidence, sources)
    citation = (ASSETS / "citation.bib").read_text(encoding="utf-8")
    require("booktitle={ICLR 2025 Workshop on Foundation Models in the Wild}" in citation and "year={2025}" in citation, "Incorrect workshop citation")
    require("https://apromisedland.github.io/tame3d-paper-page/" in citation, "Incorrect citation URL")
    require((ROOT / ".nojekyll").is_file(), "Missing static Pages configuration")
    print(f"PASS: {len(page.links)} links, {len(page.cells)} static table cells, {len(sources)} statistical mappings, resource hashes, and browser data.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError, zipfile.BadZipFile) as error:
        raise SystemExit(f"FAIL: {error}") from error
