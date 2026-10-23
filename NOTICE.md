# Attribution and third-party notices

The build scripts and print-specific styles in this repository are MIT licensed.
The book, its illustrations and any separately licensed upstream material are
not relicensed by this repository's MIT license.

## Book

*The CP-SAT Primer: Using and Understanding Google OR-Tools' CP-SAT Solver*, by
Dominik Krupke, with contributions from Leon Lan, Michael Perk and the
[upstream contributors](https://github.com/d-krupke/cpsat-primer/graphs/contributors).

- Source: <https://github.com/d-krupke/cpsat-primer>
- Original website: <https://d-krupke.github.io/cpsat-primer/>
- License: CC BY 4.0; see `LICENSES/CC-BY-4.0.txt`.
- Each release records the exact upstream commit in `build-info.json`.

This unofficial edition adjusts print presentation: Letter pages, a linked
three-level table of contents, PDF bookmarks, running heads, page numbers,
formula sizing, and code/table/figure pagination. Repeated titles and website
attribution footers are consolidated. Companion manuscripts remain linked.
This project is not endorsed by the author, Google or the OR-Tools team.
Existing upstream third-party credits and any specific license notices remain
applicable, including notices on individual code examples.

The included XKCD comic "Fuck Grapefruit", by Randall Munroe, is separately
licensed under CC BY-NC 2.5: <https://xkcd.com/license.html>. Its original source
link and attribution remain in the book. The book's CC BY 4.0 license does not
override this noncommercial restriction on the comic.

Three images linked from external hosts by the upstream book (two Shields.io
badges and this XKCD comic) are preserved in `assets/external/`. Their original
URLs and checksums are recorded in `external-assets.json`; all other book images
are read from the recorded upstream commit. No external image requests are
made while rendering the book.
Shields.io is dual MIT/Apache 2.0 licensed; both license texts are included in
`LICENSES/SHIELDS-MIT.txt` and `LICENSES/SHIELDS-APACHE-2.0.txt`.

## Typography and rendering

- Open Sans, bundled by mdBook: Apache 2.0. See `LICENSES/OPEN-SANS-LICENSE.txt`.
- Source Code Pro, bundled by mdBook: SIL OFL 1.1. See
  `LICENSES/SOURCE-CODE-PRO-LICENSE.txt`.
- MathJax 2.7.9, used to render mathematical glyphs: Apache 2.0. See
  `LICENSES/MATHJAX-LICENSE.txt`; source at
  <https://github.com/mathjax/MathJax/tree/2.7.9>.
- Original mdBook theme/styles, used in generated intermediate HTML: MPL 2.0.
  See `LICENSES/MPL-2.0.txt`; unmodified source is available at
  <https://github.com/rust-lang/mdBook/tree/v0.5.4/src/theme>.

Generated HTML, downloaded source and font files are not committed to this
repository. Release downloads include this notice and a copy of these license
texts alongside the PDF.
