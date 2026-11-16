"""Stage 6: assemble the methodology report as HTML and print it to PDF with a headless browser."""
import subprocess
from pathlib import Path

from pipelineConfig import ANALYSIS_DIR, OUTPUT_DIR
from reportEvidenceSections import evidenceSection, reliabilitySection, reproduceSection
from reportFacts import gatherFacts
from reportMethodSections import (
    dataSection,
    fairnessSection,
    performanceSection,
    pressureSection,
    ratingSection,
    summarySection,
)
from reportRoyalsSection import royalsSection

REPORT_HTML = OUTPUT_DIR / "pressureReport.html"
REPORT_PDF = ANALYSIS_DIR.parent / "submission" / "superrSelectorRound1Report.pdf"
STYLE_FILE = ANALYSIS_DIR / "reportStyle.css"
BROWSER_CANDIDATES = (Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
                      Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"))
REPORT_TITLE = "Who delivers when it matters?"
REPORT_SUBTITLE = "A leverage-based pressure rating for T20 batters and bowlers"
REPORT_EYEBROW = "SupeRR Selector Season 2 &middot; Round 1 methodology report"


def main():
    facts = gatherFacts()
    REPORT_HTML.write_text(renderReport(facts), encoding="utf-8")
    REPORT_PDF.parent.mkdir(parents=True, exist_ok=True)
    printToPdf(REPORT_HTML, REPORT_PDF)
    print(f"report written to {REPORT_PDF}")


def renderReport(facts):
    sections = [summarySection(facts), dataSection(facts), pressureSection(facts), performanceSection(),
                ratingSection(facts), fairnessSection(facts), evidenceSection(facts), reliabilitySection(facts),
                royalsSection(facts), reproduceSection()]
    cover = (f'<header class="cover"><div class="eyebrow">{REPORT_EYEBROW}</div><h1>{REPORT_TITLE}</h1>'
             f'<div class="subtitle">{REPORT_SUBTITLE}</div></header>')
    style = STYLE_FILE.read_text(encoding="utf-8")
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{REPORT_TITLE}</title>'
            f"<style>{style}</style></head><body>{cover}{''.join(sections)}</body></html>")


def printToPdf(htmlFile, pdfFile):
    browser = next(candidate for candidate in BROWSER_CANDIDATES if candidate.exists())
    subprocess.run([str(browser), "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdfFile}", htmlFile.as_uri()], check=True, capture_output=True)


if __name__ == "__main__":
    main()
