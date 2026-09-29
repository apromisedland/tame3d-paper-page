# Tame3D paper page

English project page for **Taming Multi-Agent Collaboration for 3D Situated Reasoning via Uncertainty Alignment**, published at the **ICLR 2025 Workshop on Foundation Models in the Wild**.

- Website: <https://apromisedland.github.io/tame3d-paper-page/>
- Website repository: <https://github.com/apromisedland/tame3d-paper-page>
- Research implementation: <https://github.com/apromisedland/Tame_3D/tree/master>
- Workshop: <https://iclr.cc/virtual/2025/workshop/23989>

The page is native HTML, CSS, and JavaScript. It has no backend, API key, CDN, external font, package manager, or deployment build requirement. `index.html` is the root entry point. The main content, explanations, resource links, and both complete data tables remain available without JavaScript. The browser reads the generated `assets/results.js` so local file previews also work. Public data files contain summary statistics, not per-seed records.

## Maintain the page

Use a verified Python 3 interpreter; all normal build and validation commands use only its standard library. On Windows, invoke a known interpreter by its absolute path if command lookup fails. Do not install project packages into a shared bundled runtime. Regeneration and full statistical validation require the private, ignored local `paper/` directory; a public checkout alone can serve the committed static page but cannot recompute it.

```text
python scripts/build.py
python scripts/build.py --check
python scripts/check_site.py
python -m http.server 8000 --bind 127.0.0.1
```

Open <http://127.0.0.1:8000/>. For a GitHub Pages subpath preview, serve the directory containing this checkout and open its directory name, or expose this checkout as `tame3d-paper-page` in a local preview directory. Keep all website asset URLs relative to the page; root-relative URLs break project Pages sites.

Edit `scripts/page.html` for page content, `styles.css` for presentation, and `script.js` for browser interactions. Do not edit `index.html`, `assets/results.json`, `assets/results.js`, or `assets/evidence.json` directly. `scripts/build.py` writes all four from the same source; `--check` fails when any output is stale. Citation edits belong in `assets/citation.bib` and require rebuilding.

The generator reads `paper/source/data/table_data.json` from the ignored private manuscript directory. It calculates each seed's metric before taking the arithmetic mean and sample standard deviation (`ddof=1`), but publishes only those summaries. It derives gains from unrounded means and joint error from each seed's wrong-and-answered count. These checks verify the reported aggregate statistics; they do not rerun the synthetic experiment or validate a model.

`assets/evidence.json` connects the metrics to formulas and manuscript tables and appendices, without publishing the private counts or source archive. Website values follow this manuscript. Research implementation maintenance is a separate workflow.

## Publication resources

The local `paper/` directory and its historical archive are preserved but excluded from Git. Publish only the selected PDF and figure copies in `assets/`. The PDF is a byte-for-byte copy of the supplied publication artifact; do not rebuild or modify it during website maintenance. The manuscript source archive, main TeX file, and per-seed aggregate counts are not published.

| Resource | Purpose |
| --- | --- |
| `assets/tame3d-paper.pdf` | Original 11-page publication PDF |
| `assets/results.json` | Computed summary statistics, definitions, units, and derived values; no per-seed records |
| `assets/evidence.json` | Provenance, formulas, limitations, and artifact hashes |
| `assets/framework.*` | Original Figure 1, cropped from PDF page 3 |
| `assets/observation-shift.*` | Original Figure 2, cropped from PDF page 7 |
| `assets/citation.bib` | Workshop citation |

Only when intentionally preparing PDF or figure copies, run `python scripts/prepare_assets.py` with the preserved local `paper/` directory present. This optional tool needs `pypdfium2` and Pillow. Use a dedicated project environment, for example `python -m venv .venv-assets`, then invoke that environment's interpreter with `-m pip install pypdfium2 Pillow`. Run the preparation script with the same interpreter. Normal website builds need neither package and do not regenerate the PDF. After preparing assets, rebuild and rerun the checks.

When local manuscript sources are present, also run:

```text
python paper/source/tools/render_results.py --check
```

## Validation

`scripts/check_site.py` independently recalculates each seed's statistics from the private local `paper/` directory and checks means, sample SDs, derived values, all generated table cells, local links and fragments, source mappings, the PDF hash, the JavaScript data copy, citation identity, and resource consistency with the archive. It fails if manuscript source files or raw counts reappear in public `assets/`.

Before publishing, run the checks, then use a local server to inspect 1440×900, 1024×768, 768×1024, 390×844, and 320×740 layouts, including a repository-subpath preview. Check the first screen, original figures, all three walkthrough cases, all six result selections, navigation, table scrolling, citation copy and downloads, keyboard focus and dialog focus restoration. Check no-JavaScript and reduced-motion modes, paused/offscreen/background animation behavior, console errors, network failures, contrast, and image sizing. Keep screenshots and validation records in ignored `.qa/`; do not publish them.

## GitHub Pages

Deployment target: public repository `apromisedland/tame3d-paper-page`, **Deploy from a branch**, `main`, `/ (root)`, with HTTPS enforced. The live URL and repository URL above are the configured targets; confirm the deployment and live resources before recording a successful release.

Initial publication was verified on 2026-09-29. GitHub Pages reported a successful build from `main` at the repository root, with HTTPS enforced. The live homepage, stylesheet, JavaScript, PDF, results, evidence, and figure returned HTTP 200. Chrome checks covered desktop and phone layouts, the project subpath, all three controller examples, all six result selections, scene switching, figure-dialog focus restoration, navigation, keyboard focus, reduced motion, animation pause, no-JavaScript content, and console and network errors. Local and live screenshots and validation notes are kept in ignored `.qa/`. A later update withdrew the manuscript source files and raw per-seed counts from the current publication.

For the initial authorized publication:

1. Verify `gh auth status`, `gh api user`, the remote repository's actual state, and `git status`. Set only this repository's `user.name` and GitHub noreply `user.email`.
2. Review staged paths and the complete staged diff. Include website sources, selected assets, scripts, `.nojekyll`, and these maintenance documents. Exclude `paper/`, `.qa/`, caches, logs, environments, old drafts, and credentials.
3. Create the public repository if it does not already exist, commit on `main`, and push without force. Repository creation, commit, push, and publication are already authorized for this project.
4. Configure Pages from `main` at the root, enforce HTTPS, and set the repository description and homepage to the website URL. `.nojekyll` preserves the plain static publication.
5. Wait for the Pages build/deployment to finish. Independently verify repository creation, successful deployment, and actual live access to the homepage, PDF, ZIP, data, and key interactions. After a remote timeout, query the actual server state before retrying.

Subsequent updates use `python scripts/build.py`, both checks, a reviewed commit, and a normal push to `main`. Update this document with verified deployment details after publication. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for material ownership and third-party terms; the research repository's Apache-2.0 license is not applied to the paper or this site by implication.
