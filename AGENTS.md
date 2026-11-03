# Repository Guidelines

## Project Structure & Module Organization

This workspace contains research documentation about hand tracking, gesture recognition, and augmented reality, with an emphasis on macOS Apple Silicon.

- `reports/`: consolidated reports, currently including `Ferramentas de hand tracking e AR.md`, written in Portuguese.
- `research_notes/Ferramentas de hand tracking e AR/`: supporting English notes in `python_stack.md`, `web_js_stack.md`, `native_stacks.md`, and `viral_effect_techniques.md`.

Keep detailed evidence in the relevant research note and incorporate conclusions into the report. No application source, dedicated tests, or asset directories are currently present.

## Development & Review Commands

There is no configured build system, package manifest, local server, or automated test command. Useful inspection commands include:

- `rg --files`: list the workspace files.
- `rg -n 'MediaPipe|benchmark|teste local' reports research_notes`: locate related claims and measurements.
- `sed -n '1,120p' "reports/Ferramentas de hand tracking e AR.md"`: inspect the report from the terminal.

Preview changed Markdown in your editor to check headings, tables, links, and fenced examples.

## Writing Style & Naming Conventions

Use Markdown with one top-level heading and descriptive section headings. Preserve the existing language of each document. Use short paragraphs, bullets for parallel findings, and tables for stack or performance comparisons. Label fenced code blocks with their language.

Follow the existing lowercase `snake_case.md` naming pattern for supporting notes. Quote paths containing spaces in shell commands. No formatter or linter is configured.

## Research Validation Guidelines

For new or revised claims, cite primary documentation, release notes, or source repositories and record the verification date. Distinguish local measurements from published benchmarks and untested examples. Record hardware, software versions, input size, execution mode, and measurement scope for benchmarks. Keep inference latency distinct from end-to-end webcam performance.

Check changed links and reconcile overlapping claims between notes and the report before submitting.

## Commit & Pull Request Guidelines

This directory currently has no Git metadata, so no historical commit convention can be established. If tracked in Git, use concise, imperative subjects such as `docs: clarify GPU benchmark methodology`.

Pull requests should identify changed documents, explain the research update, cite supporting sources, and describe validation performed. Include rendered screenshots only when they help reviewers assess formatting changes.
