# PDF fonts

`DroidSans.ttf` renders Latin, Greek, and Cyrillic text. `DroidSansFallbackFull.ttf`
provides Chinese and Japanese glyphs. ReportLab embeds only the glyph subsets used
by an export; these files are backend assets and do not enter the web bundle.

The unmodified files and accompanying `NOTICE` were copied from Fedora's
`google-droid-sans-fonts-20200215-24.fc44.noarch` package. They originate from the
Android Open Source Project and are distributed under Apache License 2.0, retained
in `NOTICE`. These are PDF fonts; the application's supplied UI font stacks remain
the source of truth for the website.

Coverage is finite. Exports fail explicitly when text uses an unavailable glyph,
instead of silently replacing entered names. Browser printing remains available.
