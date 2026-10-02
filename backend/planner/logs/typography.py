from functools import lru_cache
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from planner.errors import PlanningProblem


@lru_cache(maxsize=1)
def fonts():
    directory = Path(__file__).with_name("fonts")
    names = ("HaulHoursSans", "HaulHoursCJK")
    for name, filename in zip(names, ("DroidSans.ttf", "DroidSansFallbackFull.ttf")):
        pdfmetrics.registerFont(TTFont(name, str(directory / filename)))
    return tuple(pdfmetrics.getFont(name) for name in names)


def text_runs(value: str):
    available = fonts()
    runs = []
    for char in value:
        font = next((font for font in available if ord(char) in font.face.charToGlyph), None)
        if font is None:
            raise PlanningProblem("EXPORT_UNSUPPORTED_TEXT",
                                  "A character in the log details cannot be rendered in the PDF. "
                                  "Use browser Print to preserve the entered text.", 400)
        if runs and runs[-1][0] == font.fontName:
            runs[-1] = font.fontName, runs[-1][1] + char
        else:
            runs.append((font.fontName, char))
    return runs


def text_width(value: str, size: float) -> float:
    return sum(pdfmetrics.stringWidth(text, font, size) for font, text in text_runs(value))


def wrap_text(value: str, size: float, max_width: float) -> list[str]:
    # Measure actual glyphs: equal character counts can have very different widths.
    value = " ".join(value.split())
    lines = []
    current = ""
    for char in value:
        if current and text_width(current + char, size) > max_width:
            split = current.rfind(" ")
            if split > 0:
                lines.append(current[:split])
                current = current[split + 1:] + char
            else:
                lines.append(current)
                current = char
        else:
            current += char
    if current:
        lines.append(current)
    return lines


def draw_text(canvas, x: float, y: float, value: str, size: float):
    text = canvas.beginText(x, y)
    for font, run in text_runs(value):
        text.setFont(font, size)
        text.textOut(run)
    canvas.drawText(text)
