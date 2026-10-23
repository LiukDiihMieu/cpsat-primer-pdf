# The CP-SAT Primer - Letter PDF

An unofficial PDF edition of [The CP-SAT Primer](https://github.com/d-krupke/cpsat-primer), by Dominik Krupke and contributors.

**[Download the latest PDF](https://github.com/LiukDiihMieu/cpsat-primer-pdf/releases/latest/download/cpsat-primer-letter.pdf)** · [Releases](https://github.com/LiukDiihMieu/cpsat-primer-pdf/releases) · [Build workflow](.github/workflows/pdf.yml)

## Design

- US Letter pages with book-style margins and reading density.
- Original typography, illustrations, syntax colors and callouts retained.
- Vector formulas slightly reduced to balance with the body text.
- Linked contents organized by part, chapter and section; complete heading
  hierarchy preserved in PDF bookmarks.
- Running heads, page numbers, and adjustments to code, tables and figure pagination.
- Repeated titles and website attribution footers consolidated. Companion
  manuscripts remain linked rather than appended.

## How it works

A fixed upstream commit is built through the author's scripts and mdBook.
Local MathJax and Chromium render the formulas, then WeasyPrint applies the
print styles. Chapter order comes from upstream `SUMMARY.md`. Book images are
read from the same commit, with three originally external images preserved as
checksum-verified local assets.

Before release, automated checks verify content retention, links, printed
contents page numbers, page numbering and text/figure bounds. PDF properties
and XMP contain bibliographic metadata; `build-info.json` records the exact
source revision and tool versions. Review contact sheets are available as a
CI artifact.

The manual workflow checks upstream `main` and publishes only when the book
or PDF pipeline changed. Pushes and pull requests validate the revision in
`upstream.json` without publishing. No scheduled trigger is configured.

For local builds, `./build.sh` uses the pinned source; `./build.sh --ref main`
updates to upstream `main`. The supported baseline is Ubuntu 24.04, Python 3.12
and x86-64 Linux. Build dependencies and tools are pinned.

## Licenses

Build scripts and print-specific styles: [MIT](LICENSE). Book content:
[CC BY 4.0](LICENSES/CC-BY-4.0.txt), subject to existing third-party exceptions,
including the XKCD comic's CC BY-NC 2.5 terms. See [NOTICE.md](NOTICE.md) and
[LICENSES/](LICENSES/) for attribution and other licenses.

Not endorsed by the original author, Google or the OR-Tools team. Corrections
to the book itself belong in the upstream repository.
