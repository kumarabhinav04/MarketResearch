from __future__ import annotations

import json
import math
import re
import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Sequence

from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    Image,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "pdf"
TMP_DIR = ROOT / "tmp" / "pdfs"
REFERENCE_IMAGE = Path(
    "/var/folders/8j/3gx56vx90_d154rt_0v78mh00000gn/T/"
    "codex-clipboard-484220b7-bef3-4e53-8cb0-ead4e91c63b3.png"
)

NAVY = HexColor("#071018")
NAVY_2 = HexColor("#0D1B26")
NAVY_3 = HexColor("#142833")
MINT = HexColor("#55E6B6")
MINT_DARK = HexColor("#176A58")
CYAN = HexColor("#75C7E8")
INK = HexColor("#16242D")
SLATE = HexColor("#536671")
PALE = HexColor("#EAF1F4")
PALE_MINT = HexColor("#E7F8F2")
WHITE = colors.white
RED = HexColor("#B93A43")
AMBER = HexColor("#A66A12")
LIGHT_AMBER = HexColor("#FFF5DE")
LIGHT_RED = HexColor("#FDEBED")


def esc(value: Any) -> str:
    text = str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def ascii_text(value: str) -> str:
    replacements = {
        "\u2013": "-",
        "\u2014": "-",
        "\u2011": "-",
        "\u2212": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2265": ">=",
        "\u2264": "<=",
        "\u2192": "->",
        "\u00d7": "x",
        "\u00b7": "-",
        "\u2212": "-",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    return value


BASE = getSampleStyleSheet()
STYLES = {
    "body": ParagraphStyle(
        "Body",
        parent=BASE["BodyText"],
        fontName="Helvetica",
        fontSize=9.25,
        leading=13.1,
        textColor=INK,
        spaceAfter=6,
        allowWidows=0,
        allowOrphans=0,
    ),
    "small": ParagraphStyle(
        "Small",
        parent=BASE["BodyText"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10.2,
        textColor=SLATE,
        spaceAfter=4,
    ),
    "h1": ParagraphStyle(
        "Heading1",
        parent=BASE["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=27,
        textColor=NAVY,
        spaceAfter=8,
        keepWithNext=True,
    ),
    "h2": ParagraphStyle(
        "Heading2",
        parent=BASE["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=NAVY,
        spaceBefore=6,
        spaceAfter=7,
        keepWithNext=True,
    ),
    "h3": ParagraphStyle(
        "Heading3",
        parent=BASE["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=13,
        textColor=MINT_DARK,
        spaceBefore=6,
        spaceAfter=4,
        keepWithNext=True,
    ),
    "lead": ParagraphStyle(
        "Lead",
        parent=BASE["BodyText"],
        fontName="Helvetica",
        fontSize=11.2,
        leading=15.5,
        textColor=SLATE,
        spaceAfter=11,
    ),
    "bullet": ParagraphStyle(
        "Bullet",
        parent=BASE["BodyText"],
        fontName="Helvetica",
        fontSize=8.8,
        leading=12.2,
        textColor=INK,
        leftIndent=12,
        firstLineIndent=-8,
        bulletIndent=0,
        spaceAfter=3,
    ),
    "code": ParagraphStyle(
        "Code",
        parent=BASE["Code"],
        fontName="Courier",
        fontSize=7.2,
        leading=9.4,
        textColor=PALE,
        backColor=NAVY_2,
        borderPadding=7,
        spaceBefore=4,
        spaceAfter=8,
    ),
    "table_header": ParagraphStyle(
        "TableHeader",
        parent=BASE["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=7.2,
        leading=9,
        textColor=WHITE,
    ),
    "table_cell": ParagraphStyle(
        "TableCell",
        parent=BASE["BodyText"],
        fontName="Helvetica",
        fontSize=7.1,
        leading=9.2,
        textColor=INK,
    ),
    "toc_h1": ParagraphStyle(
        "TOC1",
        parent=BASE["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        leftIndent=0,
        firstLineIndent=0,
        textColor=INK,
    ),
    "toc_h2": ParagraphStyle(
        "TOC2",
        parent=BASE["BodyText"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        leftIndent=12,
        firstLineIndent=0,
        textColor=SLATE,
    ),
}


class Rule(Flowable):
    def __init__(self, width: float = 25 * mm, color=MINT, thickness: float = 3):
        super().__init__()
        self.width = width
        self.height = thickness + 3
        self.color = color
        self.thickness = thickness

    def draw(self) -> None:
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, self.height / 2, self.width, self.height / 2)


class TechnicalDocTemplate(BaseDocTemplate):
    def __init__(self, filename: str, *, title: str, volume_label: str):
        self.document_title = title
        self.volume_label = volume_label
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=19 * mm,
            rightMargin=17 * mm,
            topMargin=19 * mm,
            bottomMargin=17 * mm,
            title=title,
            author="AI Factory Research Platform",
            subject="Detailed implementation handbook",
            creator="Codex / ReportLab",
        )
        page_frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="body",
        )
        self.addPageTemplates(
            [
                PageTemplate(id="cover", frames=[page_frame], onPage=self._cover_page),
                PageTemplate(id="body", frames=[page_frame], onPage=self._body_page),
            ]
        )
        self._bookmark_counter = 0

    def beforeDocument(self) -> None:
        # multiBuild performs several layout passes for the table of contents.
        # Bookmark names must remain stable across those passes.
        self._bookmark_counter = 0

    def _cover_page(self, canvas, doc) -> None:
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.rect(0, 0, A4[0], A4[1], stroke=0, fill=1)
        canvas.setFillColor(MINT_DARK)
        canvas.circle(A4[0] - 30 * mm, A4[1] - 24 * mm, 56 * mm, stroke=0, fill=1)
        canvas.setFillColor(NAVY_3)
        canvas.circle(A4[0] - 8 * mm, 26 * mm, 43 * mm, stroke=0, fill=1)
        canvas.restoreState()

    def _body_page(self, canvas, doc) -> None:
        canvas.saveState()
        canvas.setStrokeColor(HexColor("#C8D5DB"))
        canvas.setLineWidth(0.45)
        canvas.line(self.leftMargin, A4[1] - 14 * mm, A4[0] - self.rightMargin, A4[1] - 14 * mm)
        canvas.setFillColor(SLATE)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(self.leftMargin, A4[1] - 10.5 * mm, self.volume_label)
        canvas.drawRightString(A4[0] - self.rightMargin, A4[1] - 10.5 * mm, "IMPLEMENTATION HANDBOOK")
        canvas.setStrokeColor(HexColor("#D4DEE3"))
        canvas.line(self.leftMargin, 12 * mm, A4[0] - self.rightMargin, 12 * mm)
        canvas.setFillColor(SLATE)
        canvas.drawString(self.leftMargin, 8.5 * mm, "AI Factory Research Platform")
        canvas.drawRightString(A4[0] - self.rightMargin, 8.5 * mm, f"{canvas.getPageNumber():03d}")
        canvas.restoreState()

    def afterFlowable(self, flowable: Flowable) -> None:
        if isinstance(flowable, Paragraph):
            style = flowable.style.name
            if style in {"Heading1", "Heading2"}:
                level = 0 if style == "Heading1" else 1
                text = flowable.getPlainText()
                key = f"bookmark-{self.volume_label}-{self._bookmark_counter}"
                self._bookmark_counter += 1
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(text, key, level=level, closed=False)
                self.notify("TOCEntry", (level, text, self.page, key))


@dataclass(frozen=True)
class Topic:
    title: str
    lead: str
    paragraphs: tuple[str, ...] = ()
    bullets: tuple[str, ...] = ()
    table_headers: tuple[str, ...] = ()
    table_rows: tuple[tuple[Any, ...], ...] = ()
    code: str | None = None
    why: str | None = None
    status: str = "IMPLEMENTED"
    links: tuple[tuple[str, str], ...] = ()


def p(text: str, style: str = "body") -> Paragraph:
    return Paragraph(ascii_text(text), STYLES[style])


def h1(text: str) -> Paragraph:
    return Paragraph(ascii_text(text), STYLES["h1"])


def h2(text: str) -> Paragraph:
    return Paragraph(ascii_text(text), STYLES["h2"])


def h3(text: str) -> Paragraph:
    return Paragraph(ascii_text(text), STYLES["h3"])


def bullets(items: Iterable[str]) -> list[Flowable]:
    return [Paragraph(f"<b>-</b> {ascii_text(item)}", STYLES["bullet"]) for item in items]


def code_block(text: str) -> Paragraph:
    return Paragraph(esc(ascii_text(text)).replace("\n", "<br/>"), STYLES["code"])


def status_badge(value: str) -> Table:
    color = MINT_DARK if value == "IMPLEMENTED" else AMBER if value == "PLANNED" else RED
    background = PALE_MINT if value == "IMPLEMENTED" else LIGHT_AMBER if value == "PLANNED" else LIGHT_RED
    item = Table([[Paragraph(f"<b>{esc(value)}</b>", STYLES["small"])]], colWidths=[33 * mm])
    item.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), background),
                ("TEXTCOLOR", (0, 0), (-1, -1), color),
                ("BOX", (0, 0), (-1, -1), 0.5, color),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return item


def callout(title: str, text: str, *, color=MINT_DARK, background=PALE_MINT) -> Table:
    data = [[Paragraph(f"<b>{esc(ascii_text(title))}</b><br/>{ascii_text(text)}", STYLES["body"])]]
    box = Table(data, colWidths=[165 * mm])
    box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), background),
                ("BOX", (0, 0), (-1, -1), 0.8, color),
                ("LINEBEFORE", (0, 0), (0, -1), 4, color),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return box


def make_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
    *,
    widths: Sequence[float] | None = None,
    repeat_rows: int = 1,
) -> Table:
    wrapped = [[Paragraph(esc(ascii_text(v)), STYLES["table_header"]) for v in headers]]
    for row in rows:
        wrapped.append([Paragraph(ascii_text(str(v)), STYLES["table_cell"]) for v in row])
    if widths is None:
        widths = [165 * mm / max(1, len(headers))] * len(headers)
    table = Table(wrapped, colWidths=widths, repeatRows=repeat_rows, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY_2),
                ("GRID", (0, 0), (-1, -1), 0.35, HexColor("#BFCED5")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, HexColor("#F5F8F9")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def links_block(items: Sequence[tuple[str, str]]) -> list[Flowable]:
    if not items:
        return []
    output: list[Flowable] = [h3("Source and reference links")]
    for label, url in items:
        output.append(
            Paragraph(
                f'<link href="{esc(url)}" color="#176A58"><u>{esc(ascii_text(label))}</u></link><br/>'
                f'<font color="#536671">{esc(url)}</font>',
                STYLES["small"],
            )
        )
    return output


def topic_page(topic: Topic, number: int | None = None) -> list[Flowable]:
    output: list[Flowable] = []
    if number is not None:
        output.append(p(f"SECTION {number:02d}", "small"))
    output.extend([h1(topic.title), Rule(), Spacer(1, 3 * mm), status_badge(topic.status), Spacer(1, 4 * mm), p(topic.lead, "lead")])
    for paragraph in topic.paragraphs:
        output.append(p(paragraph))
    if topic.bullets:
        output.append(h3("Implementation details"))
        output.extend(bullets(topic.bullets))
    if topic.table_headers and topic.table_rows:
        output.append(Spacer(1, 2 * mm))
        output.append(make_table(topic.table_headers, topic.table_rows))
    if topic.code:
        output.append(h3("Concrete contract"))
        output.append(code_block(topic.code))
    if topic.why:
        output.append(Spacer(1, 2 * mm))
        output.append(callout("Why this design", topic.why))
    output.extend(links_block(topic.links))
    output.append(PageBreak())
    return output


def cover_story(volume: str, title: str, subtitle: str, focus: str) -> list[Flowable]:
    return [
        Spacer(1, 36 * mm),
        Paragraph(f'<font color="#55E6B6"><b>{esc(volume)}</b></font>', ParagraphStyle("cover-kicker", parent=STYLES["small"], fontSize=10, leading=12)),
        Spacer(1, 6 * mm),
        Paragraph(esc(title), ParagraphStyle("cover-title", parent=STYLES["h1"], fontSize=31, leading=34, textColor=WHITE, spaceAfter=12)),
        Paragraph(esc(subtitle), ParagraphStyle("cover-subtitle", parent=STYLES["lead"], fontSize=14, leading=19, textColor=PALE)),
        Spacer(1, 13 * mm),
        Table(
            [[Paragraph(f"<b>FOCUS</b><br/>{esc(focus)}", ParagraphStyle("cover-focus", parent=STYLES["body"], fontSize=10, leading=14, textColor=WHITE))]],
            colWidths=[150 * mm],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), NAVY_3),
                ("BOX", (0, 0), (-1, -1), 0.7, MINT),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]),
        ),
        Spacer(1, 70 * mm),
        Paragraph("Implementation snapshot: 02 September 2026", ParagraphStyle("cover-date", parent=STYLES["small"], textColor=PALE)),
        Paragraph("Implemented behavior is separated from planned production extensions on every page.", ParagraphStyle("cover-note", parent=STYLES["small"], textColor=PALE)),
        NextPageTemplate("body"),
        PageBreak(),
    ]


def toc_story(reading_note: str) -> list[Flowable]:
    toc = TableOfContents()
    toc.levelStyles = [STYLES["toc_h1"], STYLES["toc_h2"]]
    return [
        h1("Contents and reading guide"),
        Rule(),
        Spacer(1, 4 * mm),
        p(reading_note, "lead"),
        callout(
            "Status convention",
            "IMPLEMENTED means executable behavior in this repository. PLANNED means a designed production extension that is catalogued or declared but not wired. BOUNDARY means a deliberate non-goal or limitation.",
        ),
        Spacer(1, 6 * mm),
        toc,
        PageBreak(),
    ]


def flow_diagram(labels: Sequence[str], *, width: float = 165 * mm, height: float = 31 * mm) -> Drawing:
    drawing = Drawing(width, height)
    count = len(labels)
    gap = 3 * mm
    box_width = (width - gap * (count - 1)) / count
    y = 8 * mm
    for index, label in enumerate(labels):
        x = index * (box_width + gap)
        drawing.add(Rect(x, y, box_width, 15 * mm, rx=4, ry=4, fillColor=NAVY_2, strokeColor=MINT_DARK, strokeWidth=0.7))
        drawing.add(String(x + box_width / 2, y + 8 * mm, label, textAnchor="middle", fontName="Helvetica-Bold", fontSize=6.2, fillColor=WHITE))
        if index < count - 1:
            drawing.add(Line(x + box_width, y + 7.5 * mm, x + box_width + gap, y + 7.5 * mm, strokeColor=MINT_DARK, strokeWidth=1.2))
    return drawing


def load_json(name: str) -> dict[str, Any]:
    return json.loads((ROOT / "config" / name).read_text(encoding="utf-8"))


def source_links() -> dict[str, tuple[tuple[str, str], ...]]:
    return {
        "sec_edgar": (("SEC EDGAR APIs", "https://www.sec.gov/search-filings/edgar-application-programming-interfaces"), ("SEC fair-access resources", "https://www.sec.gov/about/developer-resources")),
        "gleif": (("GLEIF API", "https://www.gleif.org/en/lei-data/gleif-api"), ("GLEIF LEI data access", "https://www.gleif.org/en/lei-data/access-and-use-lei-data")),
        "gdelt": (("GDELT DOC 2.0 API", "https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/"),),
        "usaspending": (("USAspending API", "https://api.usaspending.gov/docs/endpoints"),),
        "openfigi": (("OpenFIGI API", "https://www.openfigi.com/api/documentation"),),
        "companies_house": (("Companies House API", "https://developer.company-information.service.gov.uk/"), ("Developer guidelines", "https://developer.company-information.service.gov.uk/developer-guidelines/")),
        "filings_xbrl_org": (("filings.xbrl.org API", "https://filings.xbrl.org/docs/api"), ("ESMA ESEF resources", "https://www.esma.europa.eu/issuer-disclosure/electronic-reporting")),
        "edinet": (("EDINET API registration", "https://disclosure2.edinet-fsa.go.jp/week0020.aspx"),),
        "eia": (("EIA API v2", "https://www.eia.gov/opendata/documentation.php"),),
        "patentsview": (("PatentsView Search API", "https://search.patentsview.org/docs/docs/Search%20API/SearchAPIReference/"),),
    }


def source_purpose(source_id: str) -> str:
    return {
        "sec_edgar": "Build the U.S. issuer universe, persist CIK/ticker identity, archive submissions and filings, and create authoritative revenue and operating-margin claims from XBRL.",
        "gleif": "Resolve a selected company legal name to an LEI and persist a scored identity mapping; it is not used to infer financial or investment facts.",
        "gdelt": "Discover topical news metadata and canonical article URLs. The adapter deliberately stores discovery records rather than treating article text as primary evidence.",
        "usaspending": "Discover government awards and recipients, then resolve each recipient to the correct public parent before any research use.",
        "openfigi": "Normalize securities and share classes with FIGI and related identifiers after legal-entity resolution.",
        "companies_house": "Add UK official company identity, profiles, filing histories, and document discovery.",
        "filings_xbrl_org": "Discover ESEF and UKSEF structured filings, with material facts checked against the national official record.",
        "edinet": "Add official Japanese filings and structured disclosure packages.",
        "eia": "Supply power-market context for generation, capacity, fuel, pricing, and infrastructure demand without pretending that market data proves a company award.",
        "patentsview": "Supply patent and assignee evidence as one input to the standards/IP moat component; raw patent counts do not determine the score.",
    }[source_id]


def source_parse_notes(source_id: str) -> tuple[str, ...]:
    return {
        "sec_edgar": (
            "Universe payload schema is checked for the exact CIK, name, ticker, and exchange field order before records are accepted.",
            "Company sync archives submissions JSON, Company Facts JSON, and selected filing HTML. Filing HTML is normalized after script/style/template removal.",
            "Annual revenue candidates are limited to 10-K, 20-F, or 40-F facts filed on or before the cutoff; operating income must match the selected revenue period.",
        ),
        "gleif": (
            "Exact legal-name filtering runs first; fuzzy completion is a fallback used only to locate a canonical record.",
            "Names are case-folded, punctuation-normalized, and stripped of configured legal suffixes before SequenceMatcher similarity.",
            "The LEI is persisted only at or above the configured 0.82 similarity threshold, together with match confidence and the matched legal name.",
        ),
        "gdelt": (
            "Query combines legal-name aliases, optional ticker, and configured AI-factory topic terms over a bounded 1-365 day window.",
            "Only HTTPS article URLs become discovery documents; metadata includes domain, language, country, tone, and discovery_only=true.",
            "GDELT result metadata is Tier 3 and cannot by itself support a material financial claim.",
        ),
        "usaspending": ("Parse award, recipient, amount, action date, and agency fields; normalize recipient identifiers and preserve modifications.", "Deduplicate award actions from award totals and preserve the public-parent resolution decision."),
        "openfigi": ("Batch mapping requests by identifier type and market sector, preserve all candidates, and require deterministic share-class selection rules.", "Record terms and redistribution limits before identifiers are shown in exported research."),
        "companies_house": ("Separate company profile, filing history, and document retrieval; preserve company number as the stable official key.", "Retain filing dates, category, document metadata, and raw content hashes."),
        "filings_xbrl_org": ("Use the index for discovery and taxonomy-aware parsing, but retain the national OAM link used to validate material facts.", "Handle withdrawn and corrected filings as new point-in-time versions."),
        "edinet": ("Persist document list metadata before downloading disclosure ZIP packages; preserve EDINET code, filer, form, and filing date.", "Use an XBRL-aware parser and Japanese taxonomy tests rather than generic tag matching."),
        "eia": ("Normalize series ID, geography, frequency, unit, period, and revision metadata.", "Keep market context separate from company evidence unless a project or contract source supplies the linkage."),
        "patentsview": ("Resolve assignees to the security master with confidence and ambiguity review.", "Classify relevant patent families and citations, avoiding duplicate grants and portfolio-size bias."),
    }[source_id]


def table_purpose(name: str) -> str:
    return {
        "companies": "Canonical issuer and selected-security universe, including eligibility, capital-stack placement, public-parent linkage, and source-derived metadata.",
        "market_segments": "Versioned AI-factory taxonomy with reference spend, seed weight, assumptions, and a validation flag.",
        "source_documents": "Immutable provenance catalog for every archived or normalized source document.",
        "evidence_claims": "Atomic accepted facts, calculations, assumptions, and narratives used by the research graph.",
        "entity_identifiers": "CIK, ticker, LEI, and future identifier mappings with source and confidence.",
        "source_cursors": "Incremental and conditional-fetch state per source and logical scope.",
        "source_sync_runs": "Operational history of every connector attempt, including before/after cursors, counters, status, and sanitized error.",
        "claim_proposals": "Model-proposed evidence awaiting explicit review, including validation failures and model/prompt versions.",
        "research_runs": "Frozen research clock and configuration manifest for a portfolio execution.",
        "company_assessments": "Complete structured per-company dossier and the rankability/review state used at portfolio fan-in.",
        "rankings": "Base rank plus bear and bull ranks, risk-adjusted score, and scenario-aware rank confidence.",
        "reviews": "Human dossier decisions, comments, and recorded override metadata.",
        "audit_events": "Append-only governance and operational events scoped to a run and/or company.",
    }.get(name, "Persistent platform record.")


def database_schema() -> dict[str, list[tuple[str, str, int, Any, int]]]:
    path = ROOT / "artifacts" / "aifactory.db"
    result: dict[str, list[tuple[str, str, int, Any, int]]] = {}
    with sqlite3.connect(path) as connection:
        names = [
            "companies", "market_segments", "source_documents", "evidence_claims",
            "entity_identifiers", "source_cursors", "source_sync_runs", "claim_proposals",
            "research_runs", "company_assessments", "rankings", "reviews", "audit_events",
        ]
        for name in names:
            result[name] = [
                (row[1], row[2], int(row[3]), row[4], int(row[5]))
                for row in connection.execute(f"PRAGMA table_info({name})")
            ]
    return result


def volume_one_topics() -> list[Topic]:
    topics: list[Topic] = [
        Topic(
            "The decision problem",
            "The platform answers a narrow investment-research question: which public companies have the strongest fundamental growth exposure to AI-factory and hyperscale data-center capital expenditure over a three-year horizon?",
            (
                "The problem is not a web-search problem and not a generic stock screener. It is an evidence-integration problem across different capital layers, issuers, reporting systems, time periods, units, and source rights. The system must convert that heterogeneous evidence into comparable company dossiers without allowing a language model to invent a missing input.",
                "The result is a ranked research output, not an expected-return forecast. Valuation, entry price, discount rates, financing timing, and market sentiment are intentionally absent. A high score means strong, defensible and material AI-factory-driven operating growth under the methodology; it does not mean the security is cheap or will outperform.",
                "The design therefore prioritizes identity, point-in-time evidence, lineage, deterministic arithmetic, uncertainty visibility, and human publication control. Those priorities explain nearly every architecture choice described in these volumes.",
            ),
            (
                "Freeze one research cutoff date for each run.",
                "Map every issuer to one defined capital-stack role and selected public security.",
                "Require cited evidence for exposure, margin, growth scenarios, moat, and risk.",
                "Rank only dossiers that clear identity, coverage, confidence, contradiction, and numeric-validation gates.",
            ),
            why="A narrower claim can be tested and governed. Mixing fundamental growth, valuation, macro timing, and trading signals into one autonomous agent would make errors harder to detect and outputs harder to reproduce.",
        ),
        Topic(
            "System objectives and non-goals",
            "The objective is repeatable quarterly equity-research automation with traceable evidence, not unconstrained autonomous investing.",
            (
                "The implemented platform maps the AI-factory capital stack, builds a source-derived public-company universe, stores immutable source lineage, converts documents into deterministic facts or review-only proposals, runs a bounded research graph, computes TAFGS in code, and applies human review before publication.",
                "Phase-one non-goals are equally important: no private companies, venture-stage suppliers, short-term trading signals, portfolio construction, valuation timing, order execution, macro-rate forecasts, autonomous external messages, or unreviewed model-authored claims. These boundaries keep the agent tool set read-only and the blast radius small.",
            ),
            table_headers=("In scope", "Explicitly out of scope"),
            table_rows=(
                ("Equity research automation", "Order execution or trading"),
                ("AI-factory capex attribution", "Valuation and entry price"),
                ("Moat, margin, growth and risk", "Macroeconomic prediction"),
                ("Top-20 fundamental ranking", "Guaranteed stock-price return"),
                ("Quarterly reproducible refresh", "Private-company coverage"),
            ),
            status="BOUNDARY",
        ),
        Topic(
            "Research questions the platform must prove",
            "Every rankable company dossier must answer five proof questions with dated evidence and explicit calculations.",
            (
                "First, the system must prove that the legal entity and selected public security are correct for the research date. Second, it must show how the issuer monetizes a defined AI-factory layer. Third, it must quantify the current revenue exposure rather than confusing total addressable market with company revenue. Fourth, it must assess differentiation, margin quality, growth drivers, and risks under versioned rubrics. Fifth, it must allow an analyst or auditor to reproduce the numeric result from the stored claims and configuration snapshot.",
                "No single source can answer all five. Regulatory filings are strong for identity and reported financials but weak for a standardized AI-revenue tag. Project records may show demand but not supplier revenue. Technical standards may show influence but not realized economics. The architecture uses a portfolio of sources and keeps discovery, evidence, judgment, and calculation as separate stages.",
            ),
            bullets=(
                "Who is the issuer and which security is eligible?",
                "Where in the capital stack does the issuer earn revenue?",
                "What share of company revenue is directly exposed today?",
                "What evidence supports moat, margin, scenarios, and risk?",
                "Can a reviewer reproduce the score and publication decision?",
            ),
        ),
        Topic(
            "Architecture principles",
            "Eight principles turn a potentially open-ended research agent into a governed evidence system.",
            table_headers=("Principle", "Concrete implication"),
            table_rows=(
                ("Point-in-time by construction", "Every run has an as_of_date; later filings and restatements are excluded."),
                ("Evidence before judgment", "Agents consume normalized claims and evidence IDs, not unrestricted browsing context."),
                ("Workflow before autonomy", "A typed graph fixes role order, state, tools, retry boundaries, and stopping conditions."),
                ("Code owns numbers", "Exposure conversion, margins, risk discount, TAFGS, ranking, and release gates are deterministic."),
                ("Confidence is separate", "Source confidence controls evidence fitness; it never becomes a business-quality score."),
                ("Retrieved text is untrusted", "Document instructions are scanned and quoted as data, never followed."),
                ("Humans authorize publication", "Model proposals and ranked dossiers require explicit review."),
                ("Reproducibility over mutation", "Runs, hashes, versions, and outputs remain traceable instead of being silently overwritten."),
            ),
            why="These principles are stronger than a prompt. They are encoded in schemas, database constraints, state transitions, security checks, deterministic functions, and publication gates.",
        ),
        Topic(
            "End-to-end component architecture",
            "The platform is arranged as six cooperating planes: sources, acquisition, knowledge, agent workflow, deterministic control, and human release.",
            (
                "The source plane contains regulatory, issuer, project, technical, and discovery providers. The acquisition plane validates a versioned source definition, performs bounded HTTPS retrieval, archives the original response, and normalizes content. The knowledge plane persists company identity, documents, atomic claims, and the capital-stack taxonomy.",
                "The company-research graph reads a frozen evidence bundle and passes a typed assessment through specialized roles. The control plane performs range checks, scoring, scenario ranking, evaluation, review, reporting, and publication. Telemetry crosses all planes through JSON logs, process metrics, and persistent audit events.",
            ),
            code="SOURCES -> SAFE FETCH -> RAW SNAPSHOT -> NORMALIZED DOCUMENT\n        -> CLAIM LEDGER -> COMPANY GRAPH -> DETERMINISTIC SCORE\n        -> PORTFOLIO RANK -> ANALYST REVIEW -> REPORT + MANIFEST",
            why="Each arrow is a contract boundary. Raw content cannot jump directly into ranking, and a model response cannot bypass the proposal ledger or deterministic scorer.",
        ),
        Topic(
            "Reference runtime topology",
            "The repository implements a real, reproducible single-node topology suitable for an assignment, developer workstation, or controlled pilot.",
            (
                "One Python process composes the FastAPI service, connector services, model gateway, LangGraph or local graph, deterministic scoring services, and report generator. SQLite runs in WAL mode. Raw responses and reports live in local artifact directories. A bounded ThreadPoolExecutor fans out independent company workflows; the steps within one company remain sequential.",
                "The topology minimizes setup cost and makes the complete workflow inspectable. It is intentionally not a multi-writer distributed system. The design documents the migration seams - repository interfaces, raw snapshot abstraction, model gateway, and outer workflow boundary - that should be implemented before horizontal scale.",
            ),
            table_headers=("Concern", "Reference implementation"),
            table_rows=(
                ("API and workbench", "FastAPI + dependency-free HTML"),
                ("Research graph", "LangGraph when installed; local sequential fallback"),
                ("Portfolio concurrency", "ThreadPoolExecutor, default four workers"),
                ("System of record", "SQLite with WAL and foreign keys"),
                ("Raw evidence", "Content-addressed local filesystem"),
                ("Reports", "Markdown plus SHA-256 manifest"),
            ),
        ),
        Topic(
            "Target production topology",
            "The intended institutional topology separates request handling, durable workflows, transactional data, immutable objects, and observability.",
            (
                "API replicas authenticate users and enqueue work. Temporal or an equivalent durable orchestrator owns long-running source and quarterly jobs. Worker pools execute source adapters and company graphs with provider-specific rate limits. PostgreSQL becomes the multi-writer system of record; S3 or MinIO stores immutable raw bytes, normalized pages, and report artifacts.",
                "Redis may coordinate distributed rate limits, locks, and short-lived caches, but it never becomes authoritative evidence. OpenTelemetry exports traces and metrics to an organization collector. SSO, RBAC, a secret manager, approved egress, signed images, and a private model gateway complete the production trust boundary.",
            ),
            bullets=(
                "Migrate repositories and schema before adding multiple writers.",
                "Keep the company graph bounded inside a durable outer workflow.",
                "Use object versioning and retention for raw evidence and manifests.",
                "Do not place n8n inside the scoring or research-decision path.",
                "Gate model and licensed-data processing through organizational approvals.",
            ),
            status="PLANNED",
        ),
        Topic(
            "Repository and module map",
            "Implementation ownership is explicit: configuration owns policy, modules own mechanisms, and persisted manifests bind versions together.",
            table_headers=("Path", "Responsibility"),
            table_rows=(
                ("config/", "Taxonomy, source, extraction, scoring, and prompt policies"),
                ("src/aifactory/sources/", "Catalog, HTTPS transport, raw storage, and live adapters"),
                ("src/aifactory/extraction.py", "Chunk retrieval, model proposals, deterministic validation, human conversion"),
                ("src/aifactory/agents/roles.py", "Nine bounded research roles"),
                ("src/aifactory/workflow.py", "LangGraph/local typed company graph"),
                ("src/aifactory/scoring.py", "Exposure-aware TAFGS and scenario ranking"),
                ("src/aifactory/database.py", "SQLite schema and repositories"),
                ("src/aifactory/service.py", "Composition root, portfolio fan-out, review, publication"),
                ("src/aifactory/api.py / cli.py", "Analyst and operator interfaces"),
                ("docs/ and tests/", "Operating specification and executable controls"),
            ),
        ),
        Topic(
            "Capital-stack model",
            "The taxonomy converts a data-center build into mutually understandable research layers and candidate-discovery hypotheses.",
            (
                "The seed model comes from the user-supplied Stargate reference image. The displayed amounts total USD 68.445 billion. Those amounts are normalized into five layer weights and persisted under taxonomy version 2026.09.01. They guide market mapping and candidate discovery; the database marks them unvalidated assumptions until supported by independent market evidence.",
                "The weights are not multiplied directly into TAFGS. The company growth forecast already reflects the addressable end market, product cycle, share, backlog, and execution assumptions. Multiplying the same capital distribution again would double-count opportunity size and mechanically favor compute companies.",
            ),
            table_headers=("Layer", "Reference spend", "Seed share"),
            table_rows=(
                ("Compute and servers", "$48.750B", "71.225%"),
                ("Networking", "$8.385B", "12.251%"),
                ("Power infrastructure", "$6.630B", "9.686%"),
                ("Cooling systems", "$2.145B", "3.134%"),
                ("Engineering and construction", "$2.535B", "3.703%"),
            ),
            status="BOUNDARY",
        ),
    ]

    segment_details = {
        "compute_servers": (
            "Compute and servers",
            "Accelerators, CPUs, high-bandwidth memory, AI servers, and storage",
            "Map chip, memory, system, and storage revenue without counting a complete server and each component as separate end-market dollars. Evidence must distinguish shipped products, backlog, capacity, and vendor-reported addressable market.",
            "Architectural software lock-in, accelerator supply, packaging, memory bandwidth, platform design wins, and hyperscaler concentration are typical moat and risk questions.",
        ),
        "networking": (
            "Networking",
            "Switches, NIC/DPU, InfiniBand, Ethernet, optics, and cabling",
            "Separate scale-up fabric from scale-out networking and front-end connectivity. Normalize port speeds, generation timing, attach rates, optical reach, and whether revenue is product, silicon, module, or system level.",
            "Reference architectures, protocol leadership, interoperability, qualification cycles, optical capacity, and transition risk from 400G to 800G and beyond are central evidence themes.",
        ),
        "power": (
            "Power infrastructure",
            "Generation, transformers, switchgear, UPS, PDU/busway, generators, and storage",
            "Trace monetization from utility/interconnection need to an issuer's actual order, equipment shipment, service agreement, or backlog. Do not convert regional load forecasts directly into supplier revenue.",
            "Lead times, installed-service networks, qualification, grid constraints, gas-turbine supply, transformer capacity, and customer/project concentration affect both scarcity moat and execution risk.",
        ),
        "cooling": (
            "Cooling systems",
            "Liquid cooling, CDUs, chillers, towers, CRAHs, and heat rejection",
            "Classify facility cooling and direct-to-chip liquid systems separately. Record rack-density assumptions, retrofit versus greenfield exposure, attachment rates, refrigerant/environmental constraints, and supplier content per MW only when supported.",
            "Thermal performance, validated reference designs, service coverage, manufacturing scale, and rapid architecture change determine whether current scarcity becomes durable differentiation.",
        ),
        "construction": (
            "Engineering and construction",
            "Design, general contracting, commissioning, and modular construction",
            "Use awarded backlog, scope, project phase, expected construction period, geographic mix, and fee/revenue recognition. Avoid treating an announced campus value as the contractor's revenue.",
            "Local labor, permitting, power readiness, fixed-price exposure, schedule penalties, customer concentration, and repeat relationships drive growth quality and risk.",
        ),
    }
    taxonomy = load_json("taxonomy.json")
    for segment in taxonomy["segments"]:
        name, subsegments, method, analysis = segment_details[segment["id"]]
        topics.append(
            Topic(
                f"Capital layer: {name}",
                f"Reference share {segment['reference_weight']:.3%}; configured subsegments: {', '.join(segment['subsegments'])}.",
                (
                    method,
                    analysis,
                    "Candidate selection is global and source-derived. A company is not eligible merely because its brand appears in a diagram; it needs a public security, a defined role, and accepted evidence for the scoring dimensions.",
                ),
                table_headers=("Taxonomy field", "Configured value"),
                table_rows=(
                    ("Segment ID", segment["id"]),
                    ("Reference spend", f"USD {segment['reference_spend_usd_billions']:.3f}B"),
                    ("Reference weight", f"{segment['reference_weight']:.5f}"),
                    ("Subsegments", subsegments),
                ),
                status="BOUNDARY",
            )
        )

    topics.extend(
        [
            Topic(
                "Evidence portfolio strategy",
                "Identity, reported financials, direct exposure, project demand, differentiation, and risk require different source families.",
                (
                    "The platform uses regulatory and government sources first for identity and reported numbers, issuer-primary sources for product and segment detail, project/utility records for independent demand evidence, standards and technical documents for defensibility, and licensed specialist sources where public coverage is insufficient.",
                    "Discovery sources identify what to investigate. They do not become material evidence merely because they are timely or easy to query. Each source definition declares its evidence tier, licence note, rate limit, timeout, response cap, authentication reference, and implementation status.",
                ),
                table_headers=("Research question", "Preferred evidence"),
                table_rows=(
                    ("Issuer/security identity", "Regulator universe + LEI/security master"),
                    ("Reported revenue/margin", "Official XBRL and audited filing"),
                    ("Direct AI exposure", "Segment notes, IR, backlog, product disclosures, licensed transcripts"),
                    ("Demand pipeline", "Hyperscaler filings, permits, utilities, procurement, project awards"),
                    ("Moat", "Technical docs, standards, certifications, design wins, competitor evidence"),
                    ("Risk", "Risk factors, concentration notes, export rules, supply agreements, cancellations"),
                ),
            ),
            Topic(
                "Source tiers and authority",
                "Tiering determines what a source may prove and how confidence is weighted; it does not turn weak evidence into a business-quality score.",
                (
                    "Tier 1 includes regulators, company-primary records, governments, and official project records. Tier 2 covers licensed transcripts, standards bodies, technical documents, and utility records. Tier 3 covers reputable news, industry publications, and analyst discovery.",
                    "Evidence confidence is calculated as the mean of claim confidence multiplied by the tier weight. Reported financials require Tier 1. Tier 3 cannot be the sole support for a material numeric claim. Contradictory evidence is retained and blocks rankability until adjudicated.",
                ),
                table_headers=("Tier", "Weight", "Permitted role"),
                table_rows=(("1", "1.00", "Authoritative identity, reported financials, official facts"), ("2", "0.80", "Specialist and near-primary evidence"), ("3", "0.45", "Discovery and corroboration only")),
                code="weighted_claim_confidence = claim.confidence * source_tier_weight\nevidence_confidence = mean(weighted_claim_confidence)",
            ),
            Topic(
                "Point-in-time evidence",
                "A research cutoff is an admissibility rule, not a display label.",
                (
                    "The service rejects a future as_of_date. Database claim queries include only as-of-eligible claims published on or before the cutoff. SEC filing selection excludes filings after the cutoff, and annual facts are ordered by period end, filing date, and accession. A later restatement must create a new run if it changes the historical view.",
                    "Point-in-time identity matters too. Tickers, names, listings, parents, and currency inputs can change. The reference schema captures the selected identity and configuration snapshot for a run; a production security master should add effective dating and corporate-action history before global backtesting.",
                ),
                bullets=("Never use database insertion time as the economic date.", "Keep original and corrected document hashes.", "Version currency and classification inputs.", "Recompute through a new immutable run rather than rewriting the old rank."),
            ),
            Topic(
                "Entity and security resolution",
                "The legal entity, public parent, and tradable security are related but not interchangeable.",
                (
                    "The implemented U.S. path uses CIK as the stable issuer key, persists all tickers and exchanges returned by the SEC, creates a selected security record, and optionally resolves a GLEIF LEI. Eligibility requires a public exchange and security identifier. Fuzzy matches may propose candidates but cannot silently merge issuers.",
                    "Production coverage must add effective-dated mappings for ADR versus primary listing, dual listings, share classes, mergers, spin-offs, ticker changes, subsidiaries, and public-parent relationships. Ambiguous matches require analyst review and must preserve every candidate and score.",
                ),
                code="company_id: sec-{zero_padded_CIK}\nsecurity_id: CIK{zero_padded_CIK}\nidentifier rows: (company_id, scheme, value, source_id, confidence)",
            ),
            Topic(
                "Data rights and legal controls",
                "Technical access is not permission to store, process with a model, display, or redistribute data.",
                (
                    "Every source catalog entry includes licence notes and an authentication reference. Public sources still have fair-access, attribution, retention, and acceptable-use requirements. Commercial data requires contract language covering machine processing, storage, derived values, user display, reports, and model-provider transfer.",
                    "The source-onboarding gate therefore includes a data-owner and legal review before enabled=true. The system does not bypass paywalls, CAPTCHAs, robots restrictions, authentication controls, or contractual prohibitions. Free model endpoints are restricted to public evidence and synthetic records unless the organization approves their data policy.",
                ),
                status="BOUNDARY",
            ),
        ]
    )

    catalog = load_json("sources.json")
    link_map = source_links()
    for source in catalog["sources"]:
        implemented = source["implementation_status"] == "implemented" and bool(source["enabled"])
        auth = source.get("auth", {})
        auth_description = "No credential" if auth.get("type", "none") == "none" else f"{auth.get('type')} via environment variable {auth.get('env')}"
        topics.append(
            Topic(
                f"Data source: {source['name']}",
                source_purpose(source["id"]),
                (
                    f"Catalog ID {source['id']} selects the code-owned connector {source['connector']}. The catalog cannot dynamically import arbitrary code. Base URL {source['base_url']} is HTTPS and the adapter is limited to {source['rate_limit_per_second']} requests per second, a {source['timeout_seconds']}-second timeout, and {source['max_response_bytes']:,} response bytes.",
                    f"Authentication handling: {auth_description}. Credentials are read only at transport time and are omitted from public source metadata, raw manifests, logs, workflow state, and audit payloads. Licence note: {source['licence_notes']}",
                    " ".join(source_parse_notes(source["id"])),
                ),
                table_headers=("Property", "Value"),
                table_rows=(
                    ("Category", source["category"]),
                    ("Evidence tier", source["source_tier"]),
                    ("Status", source["implementation_status"]),
                    ("Enabled", str(source["enabled"])),
                    ("Rate limit", f"{source['rate_limit_per_second']} requests/second"),
                    ("Timeout / response cap", f"{source['timeout_seconds']} sec / {source['max_response_bytes']:,} bytes"),
                ),
                why=("This adapter is live because it has a bounded implementation and governance contract." if implemented else "The source is catalogued but fails closed until its adapter, fixtures, entity-resolution rules, licensing review, and benchmark tests are complete."),
                status="IMPLEMENTED" if implemented else "PLANNED",
                links=link_map.get(source["id"], ()),
            )
        )

    topics.extend(
        [
            Topic(
                "Adding a source without hardwiring research data",
                "Configuration declares source policy; an allow-listed adapter implements bounded behavior; evidence remains source-derived.",
                paragraphs=(
                    "A new source begins disabled. The catalog entry defines the official base URL, endpoints, source tier, authentication environment reference, operational limits, licence notes, and source-specific options. The connector contract defines point-in-time semantics and output type before implementation begins.",
                    "The adapter archives the original response before parsing, emits normalized documents or deterministic claims, and records a cursor and sync result. Provider fixtures cover pagination, corrections, malformed responses, rate limits, oversized responses, retries, and credential redaction. Entity and duplicate-document tests follow. Legal, security, data-owner, and model-processing approval precede enablement.",
                ),
                bullets=("Create disabled catalog entry.", "Define output and cutoff semantics.", "Implement registry-owned adapter.", "Archive raw bytes and manifest.", "Add parser/entity/idempotency/security tests.", "Run frozen benchmark and rank diff.", "Approve rights and enable explicitly."),
                why="A URL in configuration is not executable authority. Separating source definition from adapter code prevents a compromised catalog from importing arbitrary code or weakening the evidence contract.",
            ),
            Topic(
                "Bounded HTTPS acquisition",
                "The source client enforces HTTPS, public DNS destinations, safe redirects, rate limits, retries, response caps, and sanitized metadata.",
                paragraphs=(
                    "For each request the client constructs an endpoint from an HTTPS base URL, injects the configured credential immediately before transport, and sets a declared User-Agent. Conditional ETag and Last-Modified headers are applied from the stored cursor. DNS is resolved and every destination is rejected if private, loopback, link-local, reserved, localhost, or .local.",
                    "Redirects are disabled in HTTPX and followed manually for at most six hops so every location is revalidated. HTTP 429 and 5xx responses use bounded backoff; total attempts are clamped to one through eight. Only safe response headers are retained. The body is checked against the per-source byte cap before it can enter storage.",
                ),
                table_headers=("Control", "Implementation"),
                table_rows=(("Scheme", "HTTPS only"), ("DNS", "Reject non-public addresses"), ("Redirects", "Revalidate each hop; maximum six"), ("Retries", "Provider option, clamped to 1-8"), ("Rate", "Per-source monotonic interval"), ("Headers", "Allow list only"), ("Body", "Per-source byte ceiling")),
                code="catalog -> validate URL/DNS -> rate wait -> request -> safe redirect loop\n        -> retry policy -> response-size check -> sanitized FetchResponse",
            ),
            Topic(
                "Content-addressed raw storage",
                "Every fetched body is written to a deterministic SHA-256 path before downstream interpretation.",
                paragraphs=(
                    "RawSnapshotStore hashes the bytes, creates a directory by source/date/hash prefix, and writes the body with a content-type-derived extension. Writes use a temporary file followed by atomic replace. Repeated storage of the same bytes is idempotent because the content path already exists.",
                    "A sidecar manifest records schema version, source ID, external ID, source URL, content type, hash, byte count, retrieval timestamp, safe response headers, and adapter metadata. Normalized text is stored beside the original object with a .normalized.txt suffix. The interface is intentionally small so S3 or MinIO can replace local files later.",
                ),
                code="artifacts/raw-sources/{source_id}/YYYY/MM/DD/{hash[0:2]}/\n  {sha256}.{json|html|pdf|txt|bin}\n  {sha256}.manifest.json\n  {sha256}.normalized.txt  # when a text normalizer runs",
            ),
            Topic(
                "SEC universe ingestion",
                "The issuer universe comes from the regulator rather than a code-owned ticker list.",
                paragraphs=(
                    "The connector requests company_tickers_exchange.json with conditional headers. It fails if the provider schema is not exactly CIK, name, ticker, exchange. Rows are grouped by zero-padded CIK so multiple tickers and exchanges remain attached to one issuer. A stable company ID sec-{CIK} and identifier records are upserted.",
                    "New universe companies begin ineligible and without a capital-stack segment; a later company sync and research-classification process must complete those fields. Existing research classifications are preserved during identity refresh. The raw universe response and a source_document record remain available for audit.",
                ),
                code="source-sync sec_edgar --mode universe --limit 1000",
                links=source_links()["sec_edgar"],
            ),
            Topic(
                "SEC company and filing ingestion",
                "A company sync joins issuer identity, submissions history, XBRL facts, and bounded recent filing text.",
                paragraphs=(
                    "The caller supplies a CIK directly or selects a company whose metadata contains one. The adapter archives submissions and Company Facts, upserts identity and selected security, and creates two source documents. It then chooses allowed forms from the catalog and downloads at most the configured filing limit with filing dates on or before the cutoff.",
                    "Each filing response is archived, converted from HTML to normalized text, scanned for prompt-injection signatures, and stored as a regulatory_filing document with accession/form metadata. The cursor records the latest accession and last cutoff so operational history and incremental behavior remain visible.",
                ),
                code="source-sync sec_edgar --mode company --cik 0000320193\n  --segment compute_servers --subsegment ai_servers\n  --as-of-date 2026-09-01 --limit 3",
            ),
            Topic(
                "Deterministic SEC XBRL parsing",
                "Revenue and operating margin are calculated from regulator facts without an LLM.",
                paragraphs=(
                    "Revenue candidates are searched across RevenueFromContractWithCustomerExcludingAssessedTax, Revenues, and SalesRevenueNet. Only USD facts from 10-K, 20-F, or 40-F filings with fiscal-period FY or null and filed on/before the cutoff are considered. The latest candidate is chosen by period end, filing date, then accession.",
                    "OperatingIncomeLoss must match the selected revenue period. Revenue is stored in USD millions at 0.99 confidence. Operating margin is OperatingIncomeLoss divided by revenue times 100 and stored at 0.98 confidence. Both claims point to the XBRL concept or deterministic calculation path and remain Tier 1.",
                ),
                code="operating_margin_pct = OperatingIncomeLoss / selected_annual_revenue * 100\nselection key = (period_end, filed_date, accession)\ncutoff rule = filed_date <= research_as_of_date",
                why="Reported financial arithmetic is testable and repeatable. A model is useful for interpreting narrative disclosures, but it should not replace exact tag and period rules where structured regulator facts exist.",
            ),
            Topic(
                "HTML normalization and parsing",
                "Filing HTML is reduced to stable text while preserving the immutable original response.",
                paragraphs=(
                    "BeautifulSoup with the lxml parser reads the archived response. Script, style, noscript, and template nodes are removed; visible text is joined with spaces and whitespace is collapsed. The normalized path is recorded in document metadata, while the content hash continues to identify the original bytes.",
                    "This parser is intentionally conservative. It does not claim page coordinates, table-cell lineage, inline XBRL semantics, or rendered-layout fidelity. Those concerns require specialized adapters and fixtures. Model extraction may use the normalized text only after the document passes company, date, size, and local-path checks.",
                ),
                status="IMPLEMENTED",
            ),
            Topic(
                "Normalized evidence-package ingestion",
                "External parsers can integrate without bypassing the platform by emitting one normalized package contract.",
                paragraphs=(
                    "EvidencePackageIngestor requires companies, documents, and claims arrays. Companies are upserted first, documents second, and claims last to satisfy identity and lineage dependencies. Document previews are scanned for prompt-injection patterns and flagged; every claim is converted to the typed EvidenceClaim model before persistence.",
                    "The package contract keeps parsing separate from research judgment. A PDF, spreadsheet, API, licensed feed, or future document-AI pipeline may have different extraction mechanics, but it must still produce stable identity, document provenance, atomic claims, units, periods, exact evidence spans, tiers, and cutoff semantics.",
                ),
                code="{\n  companies: [...],\n  documents: [{id, company_id, source_url, published_at, content_hash, ...}],\n  claims: [{claim_type, value_numeric, unit, period_end, evidence_span, ...}]\n}",
            ),
            Topic(
                "Model-assisted evidence retrieval",
                "The extraction service retrieves a bounded, keyword-relevant subset of one company's eligible documents before calling the configured model.",
                paragraphs=(
                    "Documents must belong to the company, exist locally, be published on/before the cutoff, and be among the selected document limit. Files larger than 75 MB are rejected. PDFs are explicitly rejected until the optional page-aware parser is implemented. Text, JSON, normalized text, and controlled HTML are supported.",
                    "Text is split into 6,000-character chunks with 500-character overlap. Each chunk receives a deterministic keyword score against the extraction-policy claim definitions. The top eight relevant chunks and only their matched claim definitions enter the prompt. The model receives a maximum of 2,400 completion tokens and may return at most eight proposals per document.",
                ),
                table_headers=("Budget", "Value"),
                table_rows=(("Chunk size", "6,000 characters"), ("Overlap", "500 characters"), ("Context chunks", "Top 8"), ("Proposals/document", "Maximum 8"), ("Model completion", "Maximum 2,400 tokens"), ("Document size", "75 MB")),
                why="Role-specific retrieval reduces latency, cost, prompt-injection surface, and cross-company leakage. It also produces deterministic chunk identifiers that can be checked after generation.",
            ),
            Topic(
                "Proposal validation and human acceptance",
                "A model response is stored as pending or invalid; it never becomes an evidence claim automatically.",
                paragraphs=(
                    "Every proposal must use a claim type allowed for the retrieved context. Its quote must be an exact contiguous 20-600 character substring of the cited chunk. Confidence must be finite and no greater than 0.90. Numeric claims must be finite, within the configured range, and use the exact unit. Narrative claims may not contain numeric values and require nonempty text. Period end must be an ISO date or null.",
                    "The proposal ID is a deterministic UUID derived from document ID and normalized proposal JSON. An analyst may accept or reject only a pending proposal. Acceptance creates a second deterministic claim ID, persists the accepted EvidenceClaim with the model and prompt provenance in extraction_method, updates proposal review state, and writes an audit event.",
                ),
                code="MODEL OUTPUT -> deterministic validation -> pending | invalid\nPENDING + analyst accept -> accepted EvidenceClaim + audit event\nPENDING + reject -> retained rejected proposal + audit event",
                why="Human review occurs at the evidence boundary, where the reviewer can still compare the exact source quote, unit, period, and rubric. Waiting until after ranking would hide which model assumption moved the score.",
            ),
            Topic(
                "PDF and rendered-document roadmap",
                "PDF parsing is a deliberate fail-closed boundary in the current implementation, not an unmentioned capability.",
                paragraphs=(
                    "The next adapter should store original PDF bytes, extract page-aware text with pypdf or pdfplumber, render pages for visual quote verification, and retain page number, bounding box, table coordinates, OCR status, and parser version. Scanned filings require OCRmyPDF/Tesseract plus confidence and human review.",
                    "Tables must preserve row/column lineage and unit headers. Hidden text and prompt-injection content must be compared with the rendered page. The benchmark should include multi-column layouts, footnotes, rotated tables, scanned pages, conflicting unit multipliers, and restatements. Until that adapter exists, the service raises a clear error rather than silently returning unreliable text.",
                ),
                status="PLANNED",
            ),
            Topic(
                "System-of-record design",
                "SQLite/WAL is the authoritative local ledger; raw bytes and reports remain content-addressed filesystem artifacts.",
                paragraphs=(
                    "Database initialization enables write-ahead logging and foreign keys. Repository methods open short-lived managed connections and use transactions for grouped writes. Unique indexes prevent duplicate security records, duplicate document URL/hash pairs, duplicate run/company assessments, and duplicate run/company rankings.",
                    "JSON columns hold flexible metadata and complete structured assessments while first-class columns preserve common filters and integrity. The design favors auditability and low operational friction on one node. PostgreSQL is required before multiple concurrent writers or replicas.",
                ),
                table_headers=("Storage class", "Current path", "Production target"),
                table_rows=(("Transactional ledger", "artifacts/aifactory.db", "PostgreSQL + migrations"), ("Raw source bytes", "artifacts/raw-sources/", "Versioned S3/MinIO"), ("Normalized text", "Beside raw hash", "Versioned object key"), ("Reports/manifests", "artifacts/reports/", "Immutable object + metadata row"), ("Policy/prompt code", "config/", "Versioned release artifact")),
            ),
        ]
    )

    schema = database_schema()
    for table_name, columns in schema.items():
        rows = []
        for name, type_name, not_null, default, primary_key in columns:
            constraints = []
            if primary_key:
                constraints.append("PK")
            if not_null:
                constraints.append("NOT NULL")
            if default is not None:
                constraints.append(f"default {default}")
            rows.append((name, type_name or "untyped", ", ".join(constraints) or "optional"))
        topics.append(
            Topic(
                f"Database table: {table_name}",
                table_purpose(table_name),
                (
                    f"This table is part of the implemented 13-table SQLite schema. Its columns below are read from the actual artifacts/aifactory.db schema used by the platform, not a conceptual future model.",
                    "Rows are retained as operational or governance history. Updates are idempotent where identity is stable, while research runs, reviews, sync attempts, and audit events preserve chronological state rather than hiding earlier outcomes.",
                ),
                table_headers=("Column", "Type", "Constraint / default"),
                table_rows=tuple(rows),
                why="The table has one bounded ownership purpose so identity, provenance, accepted evidence, model proposals, assessments, rankings, reviews, and audit history do not collapse into an ungoverned document store.",
            )
        )

    topics.extend(
        [
            Topic(
                "Artifact paths and provenance example",
                "A reviewer can travel from a ranked field back to an accepted claim, source document, raw bytes, and retrieval manifest.",
                paragraphs=(
                    "The database stores evidence_claim.document_id. The document record stores source_url, published_at, retrieved_at, content_hash, local_path, licence note, parser version, injection flags, and metadata. The local_path resolves to the SHA-256 raw object; the adjacent manifest repeats the retrieval facts and safe response headers.",
                    "A report manifest stores run versions, model route, ranked-company count, report hash, and the union of evidence claim IDs. This creates a reproducibility chain from publication to score, score to assessment, assessment to claim, claim to document, and document to immutable bytes.",
                ),
                code="report.manifest.json\n  -> research_runs + rankings + company_assessments\n  -> evidence_claim_ids\n  -> evidence_claims.document_id\n  -> source_documents.local_path + content_hash\n  -> raw object + sidecar manifest + source_url",
            ),
            Topic(
                "Data lifecycle and retention",
                "Source acquisition, proposal review, research runs, and publication create separate lifecycle records.",
                paragraphs=(
                    "A connector attempt begins in source_sync_runs, captures cursor_before, and ends completed, not_modified, failed, or interrupted with counters and cursor_after. Raw objects remain immutable. A parsed document can yield deterministic claims or model proposals. Invalid and rejected proposals remain visible; accepted proposals create claims without deleting their proposal history.",
                    "A research run freezes versions and company IDs, creates per-company assessments, and writes rankings after fan-in. Dossier reviews are separate rows. Publication changes the run status and regenerates report artifacts only after the approval gate. Corrections create a new source version and new run, preserving the old record.",
                ),
                code="FETCH HISTORY -> RAW VERSION -> DOCUMENT -> PROPOSAL -> REVIEW -> CLAIM\nRUN CREATED -> RUNNING -> COMPLETED -> REVIEWED -> PUBLISHED\nCORRECTION -> NEW DOCUMENT HASH + NEW RUN (never history rewrite)",
            ),
            Topic(
                "Volume I implementation checklist",
                "Use this checklist to verify that data entered the platform through the intended control path.",
                bullets=(
                    "The source exists in config/sources.json and names a code-owned adapter.",
                    "HTTPS destination, DNS, redirect, rate, retry, timeout, and byte limits passed.",
                    "The original response and sidecar manifest exist under the content hash.",
                    "The source_document contains company, source URL, dates, hash, parser, licence, and flags.",
                    "Identity resolution preserves stable identifiers and ambiguity evidence.",
                    "Reported financials came from Tier-1 deterministic parsing.",
                    "Model output is a pending/invalid proposal until explicit review.",
                    "Accepted claims include type, value/text, unit, period, exact span, section, confidence, tier, and date.",
                    "The run cutoff excludes later evidence and the report manifest resolves every claim ID.",
                ),
            ),
            Topic(
                "Volume I references",
                "Primary implementation files and authoritative provider documentation used for this volume.",
                paragraphs=(
                    "Repository ground truth: README.md; config/taxonomy.json, sources.json, source_policy.json, and extraction_policy.json; src/aifactory/config.py, database.py, ingestion.py, extraction.py, security.py, sources/catalog.py, sources/http.py, sources/storage.py, and sources/service.py; docs/architecture.md, data-contracts.md, and production-data-sources.md.",
                    "Live artifact ground truth: artifacts/aifactory.db, artifacts/raw-sources/, and artifacts/reports/. The reference capital distribution is taken only from the user-supplied Stargate image and is explicitly labelled a seed hypothesis.",
                ),
                links=tuple(item for items in source_links().values() for item in items),
            ),
        ]
    )
    return topics


def build_volume_one(path: Path) -> None:
    doc = TechnicalDocTemplate(str(path), title="AI Factory Research Platform - Volume I", volume_label="VOLUME I - PLATFORM, DATA AND STORAGE")
    story: list[Flowable] = cover_story(
        "VOLUME I",
        "Platform, Data Sources and Evidence Storage",
        "A code-grounded explanation of the problem, architecture, capital stack, online sources, acquisition controls, parsing, lineage, and database design.",
        "Where the data comes from, how it is retrieved and parsed, what is stored, and how an auditor traces every ranked input back to immutable evidence.",
    )
    story.extend(toc_story("Read this volume first. It establishes the economic question, the implemented platform boundary, every online source, the ingestion and parsing path, and the complete persistence model used by Volumes II and III."))

    if REFERENCE_IMAGE.is_file():
        story.extend([
            h1("Reference capital-stack image"),
            Rule(),
            Spacer(1, 4 * mm),
            p("The following user-supplied image is the sole origin of the seed spend amounts in taxonomy version 2026.09.01. The platform treats the normalized weights as unvalidated discovery hypotheses, not audited market size."),
            Spacer(1, 3 * mm),
            Image(str(REFERENCE_IMAGE), width=165 * mm, height=92.8 * mm),
            Spacer(1, 3 * mm),
            p("Figure 1. User-provided Stargate equipment and capital allocation reference.", "small"),
            callout("Interpretation rule", "These values guide value-chain mapping. They are not multiplied into company TAFGS and must be replaced or corroborated by independently licensed market evidence for production research."),
            PageBreak(),
        ])

    story.extend([
        h1("Architecture at a glance"), Rule(), Spacer(1, 5 * mm),
        p("The platform moves from untrusted external content to approved evidence through explicit boundaries. Every stage narrows authority rather than expanding it.", "lead"),
        flow_diagram(["Source catalog", "Safe fetch", "Raw hash", "Document", "Claim ledger"]),
        Spacer(1, 5 * mm),
        flow_diagram(["Company graph", "Score code", "Portfolio rank", "Human review", "Report manifest"]),
        Spacer(1, 7 * mm),
        callout("Key invariant", "No raw webpage, filing, news result, or model response can write a final score or published report directly."),
        PageBreak(),
    ])
    for index, topic in enumerate(volume_one_topics(), start=1):
        story.extend(topic_page(topic, index))
    doc.multiBuild(story)


def agent_specs() -> list[dict[str, Any]]:
    return [
        {
            "name": "Eligibility Agent",
            "key": "eligibility",
            "owns": "Public-company universe eligibility, capital-stack segment capture, and minimum security-master completeness.",
            "inputs": "company record: eligible, segment, exchange, security_id",
            "outputs": "assessment.eligible, assessment.segment, validation_errors",
            "logic": (
                "Copies the current assessment, reads only the selected company identity, and fails eligibility when the source-derived eligible flag is false or when exchange/security_id is absent.",
                "It does not judge growth quality, valuation, or source evidence. Keeping this gate first prevents research effort and model context from being spent on an invalid security.",
            ),
            "failure": "The dossier continues through the graph for diagnostics, but final rankability is false because validation errors remain.",
        },
        {
            "name": "Evidence Agent",
            "key": "evidence",
            "owns": "Evidence inventory, tier-adjusted confidence, and early contradiction visibility.",
            "inputs": "all company claims eligible at the run cutoff",
            "outputs": "evidence_claim_ids, evidence_confidence, warnings/errors",
            "logic": (
                "Records every claim ID used by the dossier. If no claims exist it adds a validation error. Otherwise it multiplies each claim confidence by the tier weight (1.00, 0.80, or 0.45) and stores the arithmetic mean.",
                "Contradictory claim IDs are surfaced as warnings here and become a hard rankability error in the skeptic stage. Confidence remains a provenance-quality measure; it is not added to moat or growth.",
            ),
            "failure": "No as-of-date evidence makes the issuer non-rankable; low confidence is tested against policy later.",
        },
        {
            "name": "Exposure Agent",
            "key": "exposure",
            "owns": "Current fraction of issuer revenue directly attributable to AI-factory infrastructure.",
            "inputs": "best non-contradictory ai_exposure numeric claim",
            "outputs": "assessment.ai_exposure in [0, 1]",
            "logic": (
                "Selects the most recent, highest-confidence accepted exposure claim and validates the ratio. It does not fill a missing value from market size, product narrative, or a model guess.",
                "Exposure is separated from segment CAGR so the growth conversion can reflect materiality. A high-growth niche cannot be treated as if it represented the whole issuer.",
            ),
            "failure": "Missing or out-of-range exposure adds a validation error and prevents final scoring.",
        },
        {
            "name": "Moat Agent",
            "key": "moat",
            "owns": "Six independently evidenced defensibility components and their weighted 0-5 result.",
            "inputs": "architectural lock-in, switching costs, standards/IP, ecosystem/design wins, bottleneck scarcity, competitive-intensity claims",
            "outputs": "moat_components and moat_score",
            "logic": (
                "Builds a component dictionary from accepted non-contradictory claims. weighted_component_score requires every policy component, validates each score in [0, 5], and normalizes by the configured weight sum.",
                "The agent does not use a single brand-strength intuition. Each component has a separate evidence question so a strong ecosystem cannot conceal weak competitive structure or vice versa.",
            ),
            "failure": "Any missing or out-of-range component creates an explicit moat-assessment error.",
        },
        {
            "name": "Margin Agent",
            "key": "margin",
            "owns": "Reported operating margin and the assignment's normalized 1-5 margin bucket.",
            "inputs": "best non-contradictory Tier-1 operating_margin claim",
            "outputs": "operating_margin_pct, operating_margin_score, warning for negative margin",
            "logic": (
                "Requires regulator/company-primary authority and applies exact boundary handling: >40 scores 5; 30-40 scores 4; 20 to <30 scores 3; 10 to <20 scores 2; below 10 scores 1.",
                "In the SEC path the underlying margin is deterministic OperatingIncomeLoss divided by matching-period annual revenue. Adjusted metrics remain separate.",
            ),
            "failure": "No Tier-1 margin claim or a non-finite value prevents scoring.",
        },
        {
            "name": "Growth Forecast Agent",
            "key": "growth_forecast",
            "owns": "Bear, base, and bull AI-exposed-business CAGR scenarios and exposure-aware company conversion.",
            "inputs": "ai_exposure plus three accepted scenario CAGR claims",
            "outputs": "ScenarioForecast with segment and company-level CAGRs",
            "logic": (
                "Requires a complete ordered scenario set. create_forecast validates bear <= base <= bull and calls the deterministic exposure conversion for each case.",
                "The scenario claims are analyst-reviewed assumptions supported by disclosed demand, backlog, capacity, product timing, share, and price/mix. The model may propose them but cannot approve or calculate the final score.",
            ),
            "failure": "Incomplete or unordered scenarios create a validation error.",
        },
        {
            "name": "Risk Agent",
            "key": "risk",
            "owns": "Six risk severities and the capped deterministic discount.",
            "inputs": "customer concentration, cyclicality, execution, supply chain, geopolitical/regulatory, and commoditization claims",
            "outputs": "risk_components and risk_discount",
            "logic": (
                "Collects all six 0-5 severities, calculates their weighted mean, divides by five, and multiplies by the 35% maximum discount. The policy owns the weights and cap.",
                "Risk is modeled as a score discount, not a hidden change to growth or moat. This keeps the effect inspectable and supports sensitivity analysis.",
            ),
            "failure": "Missing or out-of-range risk components prevent scoring.",
        },
        {
            "name": "Skeptic Auditor",
            "key": "skeptic_auditor",
            "owns": "Falsification, required-claim coverage, conflict detection, policy gates, and final deterministic score authorization.",
            "inputs": "complete assessment, all accepted claims, scoring policy",
            "outputs": "citation_coverage, final errors, scores, rankable flag",
            "logic": (
                "Calculates coverage across total revenue, margin, exposure, three scenarios, six moat components, and six risk components. It rechecks Tier-1 authority for financials, blocks any unresolved contradiction, and compares confidence and coverage with policy thresholds.",
                "Only when no validation errors remain does it call calculate_assessment_scores. It always sets review_required=true and determines rankability without advocating for the thesis.",
            ),
            "failure": "Any unresolved evidence or scoring error leaves the dossier persisted but non-rankable.",
        },
        {
            "name": "Narrative Agent",
            "key": "narrative",
            "owns": "Investor-readable role, catalysts, moat narrative, risks, and contrary evidence from the approved dossier.",
            "inputs": "company identity, completed assessment, accepted evidence, optional model gateway",
            "outputs": "structured narrative with generation_mode",
            "logic": (
                "Offline mode builds an evidence template from accepted role, catalyst, and contrary-evidence claims. Online mode sends the company-scoped dossier to the model under the common prompt and a strict JSON schema.",
                "The narrative runs after scoring gates and has no authority to alter numeric fields. If the model call or schema fails, the evidence template remains and a warning records the fallback.",
            ),
            "failure": "Model failure degrades gracefully; the research score and evidence stay available.",
        },
    ]


def volume_two_topics() -> list[Topic]:
    topics: list[Topic] = [
        Topic(
            "What makes this an agentic system",
            "The platform is agentic because bounded roles interpret evidence and update typed state under a supervisor; it is not agentic because a model is allowed to browse and act freely.",
            (
                "Each agent has a decision boundary, a small context, an owned output, and an explicit failure behavior. Agents are composable functions over WorkflowState. Their authority is constrained by the workflow order and by deterministic services. Numeric arithmetic, portfolio sorting, persistence, and publication authorization are services rather than conversational agents.",
                "This distinction matters operationally. Model-dependent steps can fail or be replaced without changing the score contract. The same graph runs in offline mode because most roles query already accepted structured claims; only extraction and optional narrative generation require an LLM.",
            ),
            table_headers=("Agentic capability", "Implementation"),
            table_rows=(("Planning", "Predefined typed graph, not open-ended planner"), ("Specialization", "Nine role contracts"), ("Tool use", "Read-only evidence/model access by role"), ("Memory", "Persisted evidence ledger and run state"), ("Critique", "Skeptic auditor and contradiction gates"), ("Human control", "Evidence acceptance and publication approval")),
        ),
        Topic(
            "Why not one general research agent",
            "A monolithic agent would combine retrieval, interpretation, arithmetic, ranking, and narrative in one opaque context.",
            (
                "The research dimensions have different evidence standards. Margin requires exact Tier-1 reported facts; moat needs component-specific technical and ecosystem evidence; growth needs scenarios and a driver bridge; risk looks for disconfirming evidence; narrative must not introduce new facts. One prompt encourages cross-contamination and makes evaluation ambiguous.",
                "Separate agents create testable contracts. A margin error can be measured as numeric/period mismatch; moat can be scored at component level; skeptic performance can be measured by unsupported-claim recall; narrative can be checked for no-new-facts. Smaller contexts also reduce token cost and prompt-injection exposure.",
            ),
            why="Role separation is justified by different rubrics and permissions, not by naming every function an agent. Deterministic calculations remain plain code because there is no judgment advantage in using an LLM for arithmetic.",
        ),
        Topic(
            "Agentic design patterns used",
            "The implementation combines patterns rather than relying on a single multi-agent framework abstraction.",
            table_headers=("Pattern", "How it appears", "Benefit"),
            table_rows=(
                ("Supervisor-worker", "ResearchService owns portfolio execution; one graph per company", "Bounded coordination and failure isolation"),
                ("Pipeline/state graph", "Fixed ordered nodes over typed state", "Reproducibility and inspectability"),
                ("Blackboard/evidence ledger", "Agents share accepted claims and assessment state", "Common facts without free-form conversation"),
                ("Map-reduce", "Companies fan out; rankings fan in", "Parallelism where dependencies permit"),
                ("Human-in-the-loop", "Proposal acceptance and dossier approval", "High-risk judgment remains accountable"),
                ("Critic/evaluator", "Skeptic node tries to falsify and checks gates", "Reduces thesis-confirmation bias"),
                ("Deterministic tool core", "Scoring/ranking in code", "Exact reproducibility"),
                ("Graceful degradation", "Offline graph and narrative fallback", "Useful failure instead of total outage"),
            ),
        ),
        Topic(
            "Pattern: supervisor-worker",
            "The outer ResearchService is a supervisor; company graphs are workers with isolated state and deterministic fan-in.",
            (
                "The supervisor validates the cutoff, freezes taxonomy and scoring configuration, selects eligible companies, creates the run, and submits one workflow future per company up to max_workers. Completion order does not affect rank output because assessments are persisted independently and sorting uses score plus company ID tie-break.",
                "A worker exception becomes a non-rankable CompanyAssessment containing only the exception type. Other workers continue. After all futures complete, the supervisor calls the deterministic ranker, saves rankings, updates run status, emits audit events, and optionally generates a report.",
            ),
            code="SUPERVISOR\n  freeze run -> submit company graphs -> collect assessments\n  -> persist failure or success -> deterministic fan-in rank -> complete run",
            why="Portfolio companies are independent until ranking. This pattern gains concurrency without allowing agents to coordinate informally or leak evidence across issuers.",
        ),
        Topic(
            "Pattern: typed pipeline state graph",
            "A sequential state graph makes prerequisites and stopping behavior explicit.",
            (
                "WorkflowState contains run_id, as_of_date, one company record, that company's eligible claims, the scoring policy, and an assessment under construction. Each node deep-copies the assessment, updates only owned fields, and returns an assessment patch. Credentials, raw document bodies, and other companies never enter state.",
                "The graph order is eligibility, evidence, exposure, moat, margin, growth forecast, risk, skeptic, narrative. LangGraph compiles the same node sequence used by the local fallback. There are no hidden prompt-directed branches; validation errors accumulate and the skeptic decides whether deterministic scoring may run.",
            ),
            code="eligibility -> evidence -> exposure -> moat -> margin\n  -> growth_forecast -> risk -> skeptic_auditor -> narrative",
            why="A fixed graph is appropriate because the research method is known and regulated by policy. Open-ended planning would make it difficult to prove that every company passed the same gates.",
        ),
        Topic(
            "Pattern: evidence ledger as blackboard",
            "Agents coordinate through accepted, cited claims rather than free-form inter-agent messages.",
            (
                "The evidence_claims table is a durable blackboard. Every agent sees the same company-scoped, point-in-time set and selects claim types relevant to its rubric. Evidence IDs connect outputs to provenance. The assessment object stores derived component values and validation messages, while the claim ledger remains immutable research input.",
                "This design avoids conversational drift, repeated retrieval, and ambiguity about which statement is authoritative. It also permits offline replay: the company graph can run with no internet or model once claims are accepted.",
            ),
            why="A structured blackboard is easier to audit than a transcript. It turns agent collaboration into explicit state transitions and lets deterministic tests reproduce the same decisions.",
        ),
        Topic(
            "Pattern: map-reduce portfolio execution",
            "The company dimension is mapped in parallel and reduced through deterministic scenario ranking.",
            (
                "Map inputs are frozen company IDs and a shared run configuration. Each map task returns one CompanyAssessment. The reduce step filters rankable assessments, sorts base scores descending, creates independent bear and bull orderings, calculates scenario stability, and truncates to the configured Top 20.",
                "The current map executor is a local thread pool. In production, the same boundary should become durable Temporal child workflows or queue jobs with idempotent activity keys. The reduce step must wait for terminal status from all selected companies or apply an explicit partial-run policy.",
            ),
            status="IMPLEMENTED",
        ),
        Topic(
            "Pattern: human-in-the-loop at two boundaries",
            "Humans intervene where judgment changes the evidence set and where a ranked result becomes an external publication.",
            (
                "Evidence-level review accepts or rejects one validated model proposal after checking the source, exact quote, issuer, date, unit, period, confidence, and rubric. Acceptance creates an EvidenceClaim; rejection preserves the proposal. Dossier-level review approves, rejects, or requests changes for a completed company assessment.",
                "The publication service reads every ranked company's review_status and raises a conflict until all are approved. This two-stage control prevents an apparently polished report from hiding an unreviewed assumption and creates accountability for both inputs and outputs.",
            ),
            why="Human review is most effective at explicit decision gates. Requiring a person to monitor every token or connector call would be expensive without addressing the actual points where model judgment becomes authoritative.",
        ),
        Topic(
            "Pattern: critic and evaluator",
            "The skeptic agent is a critic node; evaluate_run is a deterministic portfolio evaluator.",
            (
                "The skeptic does not improve the thesis. It searches for missing support, source-tier violations, unresolved contradictions, low confidence, low coverage, non-finite values, and incomplete component sets. Only a clean assessment is passed to score calculation.",
                "After portfolio execution, evaluate_run recomputes every stored score, calculates coverage, confidence, rankable rate, unsupported-claim count, scenario stability, and approval coverage, then produces research-ready and publication-ready gates. The two evaluators operate at different scopes but share a fail-closed philosophy.",
            ),
        ),
        Topic(
            "Pattern: deterministic tool core",
            "Agents supply validated judgments; tested functions own all arithmetic and ordering.",
            (
                "operating_margin_score, company_ai_driven_cagr, weighted_component_score, risk_discount, create_forecast, calculate_assessment_scores, and rank_assessments are deterministic functions. They reject non-finite values, invalid ranges, missing components, unordered scenarios, and invalid discounts.",
                "This design prevents model temperature, provider updates, prompt changes, or narrative wording from changing arithmetic. A run manifest records the formula and policy values, and evaluation recomputes the stored output at 1e-9 tolerance.",
            ),
            why="LLMs are useful for interpretation under ambiguity, not for multiplication, boundary comparison, or sorting. Keeping numbers in code dramatically improves governance and debugging.",
        ),
        Topic(
            "Pattern: bounded autonomy and least privilege",
            "The system deliberately narrows what each role can see and do.",
            (
                "Source connectors are read-only and allow-listed. The model gateway can return JSON but has no connector or database tool. Research agents query only the frozen company evidence already supplied in state. The ranker and reporter have no internet access. Publication is a service method guarded by database review state.",
                "Maximum attempts, redirect hops, body bytes, context chunks, proposal count, completion tokens, company workers, and API input ranges are bounded. No agent can trade, send messages, modify external sites, add source adapters dynamically, or expose credentials.",
            ),
            status="BOUNDARY",
        ),
        Topic(
            "Pattern: graceful degradation",
            "Model unavailability does not erase deterministic research capability.",
            (
                "OfflineModelGateway raises a clear error if evidence extraction is attempted, but all accepted-claim agents and scoring remain available. Narrative generation starts with an evidence template; an optional model may replace it only after returning required JSON keys. Any model error appends a warning and keeps the template.",
                "LangGraph is preferred when installed, but the local runner executes the identical ordered agent list. A company failure is isolated and persisted; a portfolio run can still finish with an excluded issuer. These fallbacks are visible in run configuration and assessment warnings.",
            ),
        ),
        Topic(
            "Pattern: idempotency and immutable reruns",
            "Stable hashes and UUIDs make repeated work safe; changed research creates new history.",
            (
                "Raw files are keyed by SHA-256. Documents use a UUID derived from source URL plus content hash. Model proposals use document ID plus normalized proposal JSON. Accepted claims use proposal ID. Company assessments are unique per run/company. Repeating an identical ingestion therefore upserts the same logical record.",
                "A correction, new filing, changed source body, policy update, or new cutoff creates a different document, claim, or research run. Historical rankings are not rewritten to hide change. compare_runs makes entry, exit, rank movement, and score movement explicit.",
            ),
        ),
        Topic(
            "Framework decision: LangGraph",
            "LangGraph is used for the bounded company workflow because it represents typed nodes and edges without owning business arithmetic.",
            (
                "StateGraph(WorkflowState) adds each agent as a named node, connects START through the fixed sequence, connects the final node to END, and compiles once for reuse. invoke(state) returns the completed assessment. The runtime name is stored in the run configuration snapshot.",
                "The graph supplies inspection, explicit ordering, future checkpointing potential, and a clean path to conditional or parallel nodes. The repository retains a local fallback so core scoring tests do not depend on framework availability.",
            ),
            why="The problem has a known research method and a small typed state. LangGraph fits a governed state machine better than a free-form group chat.",
        ),
        Topic(
            "Why not AutoGen as the primary runtime",
            "AutoGen-style conversational multi-agent coordination was considered but not selected for the decision path.",
            (
                "Conversational agents are valuable when planning is open-ended, tools are negotiated dynamically, or multiple specialists must debate an unknown path. Here the role order, evidence inputs, equations, and release gates are known. A chat transcript would add token cost and make it harder to prove that every company received the same procedure.",
                "AutoGen could still be used in a sandboxed research-exploration layer to generate candidate questions or investigate missing evidence. Its outputs would need to enter the same proposal ledger and human-review gate; it should not write accepted claims or ranks directly.",
            ),
            status="BOUNDARY",
            why="Choose the least autonomous framework that still solves the task. The platform needs controlled interpretation, not emergent delegation in the authoritative path.",
        ),
        Topic(
            "Why n8n is outside the decision path",
            "n8n can schedule and notify, but the versioned graph and scoring rules remain in tested Python.",
            (
                "A low-code workflow is useful for calendar triggers, manual approval notifications, ticket creation, or moving final artifacts. It is weaker as the authoritative research engine because visual-node edits can silently change branching, payload shape, retry behavior, or ordering outside the code test suite.",
                "The recommended integration is n8n -> authenticated quarterly-refresh API/CLI -> status polling -> analyst notification. n8n should receive run IDs and summaries, not credentials, raw licensed documents, or authority to update scores.",
            ),
            status="PLANNED",
        ),
        Topic(
            "Framework comparison",
            "Framework selection follows the control problem, not popularity.",
            table_headers=("Option", "Best fit", "Decision for this platform"),
            table_rows=(("LangGraph", "Typed, inspectable state workflows", "Implemented for company graph"), ("Local Python graph", "Offline tests and minimal runtime", "Implemented fallback"), ("AutoGen", "Conversational multi-agent planning", "Optional exploration, not authoritative path"), ("n8n", "Triggers, approvals, notifications", "Outer automation only"), ("Temporal", "Durable distributed long-running workflows", "Planned outer supervisor"), ("FastAPI", "Typed analyst/operator service", "Implemented interface")),
        ),
        Topic(
            "Model gateway design",
            "One interface supports offline, OpenAI-compatible, and local Ollama execution while preserving the same JSON contract.",
            (
                "complete_json accepts a system prompt, user prompt, JSON schema, and optional completion cap. OpenAICompatibleGateway normalizes the chat-completions URL, validates HTTPS, sends temperature zero, adds the schema to the user contract, optionally suppresses provider reasoning, and parses one JSON object. Ollama permits plain HTTP only on loopback and requests format=json.",
                "The parser handles clean JSON, fenced JSON, or a JSON object embedded in explanatory text, then verifies required top-level keys. Provider/network/schema errors are sanitized as ModelGatewayError. Full JSON Schema validation is intentionally not delegated to the gateway; domain validators check individual proposals afterward.",
            ),
            code="provider = offline | openai_compatible | ollama\ncomplete_json(system_prompt, user_prompt, schema, max_tokens) -> dict",
        ),
        Topic(
            "OpenRouter and Nemotron routing",
            "The OpenAI-compatible route can call OpenRouter's canonical API and a free Nemotron model for bounded public-evidence narrative/proposal work.",
            (
                "Configuration selects provider=openai_compatible, base URL https://openrouter.ai/api/v1, a provider model identifier, and an environment-only API key. The gateway appends /chat/completions exactly once, uses temperature zero, enforces a completion ceiling, and can set reasoning effort to none while excluding reasoning from responses.",
                "Free endpoints may be rate-limited, change availability, or apply provider retention policies. They are suitable only for public filings, public web documents, and synthetic data unless organizational review approves confidential processing. The credential must be rotated after disclosure and never appears in prompts, logs, manifests, reports, or source configuration.",
            ),
            links=(("OpenRouter quickstart", "https://openrouter.ai/docs/quickstart"), ("Nemotron 3.5 Lightning free", "https://openrouter.ai/nvidia/nemotron-3.5-lightning:free")),
        ),
        Topic(
            "Typed workflow state",
            "State is intentionally small, company-scoped, and credential-free.",
            table_headers=("Field", "Meaning", "Producer/consumer"),
            table_rows=(("run_id", "Immutable research-run identifier", "Supervisor / all nodes"), ("as_of_date", "Research clock", "Supervisor / prompt and evidence filters"), ("company", "Selected issuer/security identity", "Database / eligibility and narrative"), ("claims", "Accepted eligible EvidenceClaim list", "Database / all research roles"), ("policy", "Frozen scoring policy", "Service / moat, risk, skeptic"), ("assessment", "Structured dossier under construction", "Every node returns an updated copy")),
            code="class WorkflowState(TypedDict, total=False):\n  run_id: str\n  as_of_date: str\n  company: dict\n  claims: list[EvidenceClaim]\n  assessment: CompanyAssessment\n  policy: dict",
        ),
        Topic(
            "Research run lifecycle",
            "A run freezes the research clock, selected universe, method versions, model route, and runtime before any company graph starts.",
            (
                "The service validates the date, upserts taxonomy segments, resolves eligible companies, and rejects unknown requested IDs. create_run persists created status with taxonomy, scoring, prompt, model, source-policy version, runtime, formula manifest, and selected company IDs. Status moves to running before fan-out.",
                "After all assessments and rankings persist, status becomes completed. An exception at the supervisor boundary changes status to failed with error and audit. Publication is a later explicit transition to published after the review gate. started_at, completed_at, and published_at preserve lifecycle timing.",
            ),
            code="CREATED -> RUNNING -> COMPLETED -> PUBLISHED\n                  \\-> FAILED",
        ),
        Topic(
            "Portfolio fan-out and fan-in",
            "Concurrency is applied across companies, not across dependent steps inside one dossier.",
            (
                "ThreadPoolExecutor uses the configured maximum worker count, clamped to at least one. Futures map back to company IDs. Each completed result is persisted immediately with a company_assessed audit event. Failures create a minimal non-rankable assessment and increment company_workflow_failures_total.",
                "Fan-in calls rank_assessments only after the executor block completes. Because scenario rankings need the whole eligible set, no company can know its final rank inside its own graph. This separation prevents cross-company evidence leakage and keeps portfolio logic deterministic.",
            ),
        ),
        Topic(
            "Company graph execution trace",
            "One company moves through nine roles using only its identity, cutoff-eligible claims, policy, and current assessment.",
            table_headers=("Step", "Consumes", "Adds"),
            table_rows=(("1 Eligibility", "company identity", "eligibility and segment"), ("2 Evidence", "all claims", "IDs, confidence, contradiction warning"), ("3 Exposure", "ai_exposure", "ratio"), ("4 Moat", "six moat claims", "components and weighted score"), ("5 Margin", "Tier-1 margin", "margin and bucket"), ("6 Growth", "exposure + scenarios", "segment/company forecasts"), ("7 Risk", "six severities", "discount"), ("8 Skeptic", "entire dossier", "coverage, gates, score, rankable"), ("9 Narrative", "approved dossier", "evidence template or model JSON")),
        ),
        Topic(
            "Company-level failure semantics",
            "Validation errors accumulate as data; unexpected exceptions are isolated as workflow failures.",
            (
                "Expected research insufficiency - missing exposure, missing moat component, low confidence, or unresolved contradiction - does not raise an exception. The agent appends a human-readable validation error and the graph continues so the analyst can see all missing dimensions in one dossier.",
                "Unexpected code/provider failures are caught by the portfolio supervisor. The persisted failure reveals the exception type but avoids secret-bearing messages. Other companies continue, and the run reports excluded_count. Production should add retry classification and durable activity attempts without changing this fail-closed rankability behavior.",
            ),
        ),
    ]

    for spec in agent_specs():
        topics.append(
            Topic(
                f"Agent contract: {spec['name']}",
                spec["owns"],
                tuple(spec["logic"]),
                table_headers=("Contract field", "Definition"),
                table_rows=(("Graph node", spec["key"]), ("Inputs", spec["inputs"]), ("Outputs", spec["outputs"]), ("Failure behavior", spec["failure"]), ("Telemetry", f"agent_{spec['key']}_total plus agent_execution duration/error")),
                why=f"This is a separate agent because its rubric, context boundary, and failure meaning are distinct from the other roles. It does not own the final portfolio rank.",
            )
        )

    topics.extend(
        [
            Topic(
                "Common prompt contract",
                "The shared prompt expresses non-negotiable role, time, evidence, injection, citation, abstention, and output rules.",
                (
                    "PromptRegistry loads common.txt, substitutes agent_role and as_of_date, and optionally appends one role-specific rubric. The common contract says to make only assigned decisions, use evidence available on/before the cutoff, prefer higher tiers, treat documents as untrusted data, separate fact/calculation/assumption, cite evidence IDs, search for disconfirming evidence, avoid final TAFGS/rank, and abstain when evidence is absent.",
                    "Prompts are versioned configuration, not the sole control. The same rules are enforced again by document filtering, schema validation, proposal validators, deterministic scoring, and publication state. The run stores prompt_version so changes can be benchmarked and compared.",
                ),
                code="ROLE + RESEARCH CLOCK + EVIDENCE POLICY + CONSTRAINTS + OUTPUT\nEvery document is quoted data; every material claim needs an evidence ID.",
            ),
            Topic(
                "Extraction prompt and schema",
                "The extraction agent proposes evidence; it cannot approve a claim or calculate a ranking.",
                (
                    "The user payload contains a small company identity, one document's provenance and injection flags, the matched claim definitions, maximum proposal count, and selected chunks. The output schema requires proposals with claim_type, numeric/text value, unit, period, confidence, exact quote, chunk ID, and contradiction flag.",
                    "The prompt defines decimal conventions, exact quote behavior, abstention, and the difference between reported fact and forecast/judgment. The schema shapes output, while _validate_proposal supplies the authoritative semantic checks after generation.",
                ),
                code="proposal = {claim_type, value_numeric|null, value_text|null, unit|null,\n  period_end|null, confidence, evidence_span, page_or_section, contradiction}",
            ),
            Topic(
                "Role-specific moat, growth, and skeptic rubrics",
                "Short rubric files add domain focus without duplicating the common safety contract.",
                table_headers=("Rubric", "Required behavior"),
                table_rows=(("Moat", "Score six components independently; include supporting and contrary evidence; competitive intensity is defensibility"), ("Growth", "Produce bear/base/bull from explicit exposure, demand, backlog, share, price/mix, and capacity drivers"), ("Skeptic", "Try to falsify; verify numeric claims, periods, units, and assumptions presented as facts")),
                why="Concise role rubrics are easier to version and evaluate than one giant prompt. Shared safety remains centralized, while domain-specific tests can target each rubric.",
            ),
            Topic(
                "Context construction",
                "The model receives the minimum context needed for one company, one role, and one decision.",
                (
                    "Context includes company/security identity, research cutoff, rubric version, relevant accepted evidence, contrary evidence, and an explicit output schema. Extraction uses top-scoring chunks rather than the whole document. Narrative generation receives the completed company dossier and accepted evidence, not other companies or the entire research lake.",
                    "This prevents cross-company leakage, reduces prompt-injection surface, lowers cost, improves provider latency, and makes failed outputs easier to reproduce. Credentials, hidden model reasoning, unrelated analyst notes, and unlicensed raw text are excluded.",
                ),
            ),
            Topic(
                "Scoring philosophy",
                "TAFGS combines defensibility, operating economics, and company-level AI-driven growth, then applies an explicit risk discount.",
                (
                    "The original assignment formula is Moat x Operating Margin Score x Forecast AI-Driven Growth. The implementation strengthens it by converting segment CAGR through current exposure and by reporting bear/base/bull scenarios. Risk applies after the base formula and is capped by policy.",
                    "Evidence confidence and citation coverage are gates and reporting dimensions, not multipliers. Keeping quality separate avoids rewarding a well-documented weak business or penalizing a strong business through double-counted uncertainty.",
                ),
                code="base_TAFGS = moat_score * margin_score * company_AI_CAGR_percent\nrisk_adjusted_TAFGS = base_TAFGS * (1 - risk_discount)",
            ),
            Topic(
                "Exposure-aware growth conversion",
                "Segment growth is translated into total-company growth by holding non-AI revenue flat solely to isolate the AI contribution.",
                (
                    "Let R0 be current total revenue, e the current AI-factory revenue fraction, g the three-year AI-exposed-business CAGR, and n=3 years. Current AI revenue is R0*e; year-three AI revenue is R0*e*(1+g)^3. Non-AI revenue stays R0*(1-e) for this attribution calculation.",
                    "The total-company future revenue ratio is (1-e)+e*(1+g)^3. Taking the three-year root and subtracting one gives company AI-driven CAGR. R0 cancels, so the formula does not require a currency conversion when exposure is already a ratio.",
                ),
                code="company_AI_CAGR = ((1 - e) + e * (1 + g)^3)^(1/3) - 1",
                why="Without this conversion, a diversified company with 5% exposure would receive the same growth input as a pure-play supplier facing the same segment CAGR.",
            ),
            Topic(
                "Worked exposure example",
                "A 40% AI segment CAGR does not imply 40% company growth when exposure is only 30%.",
                (
                    "Assume total revenue index 100, exposure 0.30, and AI segment CAGR 0.40. AI revenue grows from 30 to 82.32 after three years; non-AI revenue remains 70. Total year-three revenue is 152.32. The annualized company AI-driven CAGR is approximately 15.05%.",
                    "The table shows the nonlinear materiality effect. The same segment cycle produces very different company results as exposure changes, which is exactly what the original unadjusted formula misses.",
                ),
                table_headers=("Exposure", "AI segment CAGR", "Company AI-driven CAGR"),
                table_rows=tuple((f"{e:.0%}", "40%", f"{(((1-e)+e*(1.4**3))**(1/3)-1):.2%}") for e in (0.05, 0.10, 0.30, 0.50, 0.80, 1.0)),
            ),
            Topic(
                "Operating-margin scoring",
                "Margin is a normalized indicator of pricing power and operating leverage, using exact documented boundaries.",
                table_headers=("Reported operating margin", "Score"),
                table_rows=(("> 40%", "5"), ("30% through 40%", "4"), ("20% through <30%", "3"), ("10% through <20%", "2"), ("<10%", "1")),
                paragraphs=("Exactly 40% scores 4, exactly 30% scores 4, exactly 20% scores 3, and exactly 10% scores 2. Negative margins remain score 1 and trigger a warning. Non-finite values raise ScoringError.", "The implemented SEC path uses reported GAAP operating income and matching revenue. Adjusted or segment metrics require separate claims and disclosed methodology rather than silent substitution."),
            ),
            Topic(
                "Moat scoring",
                "Six 0-5 components separate different kinds of defensibility and use versioned weights.",
                table_headers=("Component", "Weight", "Evidence focus"),
                table_rows=(("Architectural lock-in", "22%", "Proprietary platform, software dependency"), ("Switching costs", "18%", "Qualification, migration, installed operations"), ("Standards and IP", "18%", "Protocol influence, defensible rights, certification"), ("Ecosystem and design wins", "18%", "Reference designs, partners, named deployment"), ("Bottleneck scarcity", "14%", "Qualified capacity, lead times, substitutes"), ("Competitive intensity", "10%", "Favorable structure versus commodity pressure")),
                code="moat_score = sum(component_i * weight_i) / sum(weights)",
            ),
            Topic(
                "Risk scoring",
                "Risk is a transparent, capped discount derived from six severity components where five is worst.",
                table_headers=("Risk", "Weight"),
                table_rows=(("Customer concentration", "20%"), ("Cyclicality", "15%"), ("Execution", "20%"), ("Supply chain", "15%"), ("Geopolitical/regulatory", "15%"), ("Commoditization", "15%")),
                code="weighted_severity = sum(severity_i * weight_i) / sum(weights)\nrisk_discount = weighted_severity / 5 * 0.35",
                why="Applying risk after the growth-quality score keeps the penalty visible. Hiding risk inside moat or growth would make analyst overrides and scenario sensitivity harder to understand.",
            ),
            Topic(
                "TAFGS worked example",
                "A complete score can be reproduced from four displayed quantities.",
                (
                    "Assume moat 4.0, margin score 4, company AI-driven base CAGR 15.05%, and weighted risk severity 2.0/5. The maximum discount is 35%, so risk discount is 14%. Base TAFGS is 4.0*4*15.05 = 240.8. Risk-adjusted TAFGS is 240.8*(1-0.14) = 207.09.",
                    "The score is an ordinal research ranking quantity, not a percentage return or fair-value estimate. Comparisons are meaningful only within the same policy version, cutoff, universe, and evidence standard.",
                ),
                code="base = 4.0 * 4 * 15.05 = 240.80\ndiscount = (2.0 / 5) * 0.35 = 0.14\nrisk_adjusted = 240.80 * 0.86 = 207.09",
            ),
            Topic(
                "Scenario ranking and rank confidence",
                "Base score determines order; bear and bull ranks reveal sensitivity; confidence combines evidence quality with scenario stability.",
                (
                    "The ranker sorts rankable assessments independently by base, bear, and bull risk-adjusted TAFGS. Ties are resolved by company_id for deterministic order. Stability equals one minus absolute bear/bull rank spread divided by max(1, universe size minus one), floored at zero.",
                    "Rank confidence is evidence_confidence multiplied by 0.65 + 0.35*stability and clipped to [0,1]. It is reported alongside rank and does not change base order. The Top 20 truncation occurs after the full eligible set receives scenario ranks.",
                ),
                code="stability = max(0, 1 - abs(bear_rank - bull_rank)/(N-1))\nrank_confidence = clip(evidence_confidence * (0.65 + 0.35*stability), 0, 1)",
            ),
            Topic(
                "Rankability gates",
                "A company is excluded instead of receiving guessed values when required evidence or controls fail.",
                bullets=("Eligible public security with exchange and security ID.", "At least one as-of-date claim.", "Tier-1 total revenue and operating margin.", "AI exposure in [0,1].", "Complete ordered bear/base/bull scenarios.", "All six moat and six risk components in [0,5].", "No unresolved contradictory claim.", "Evidence confidence >=65%.", "Required-claim citation coverage >=85%.", "All calculations finite and valid."),
                status="BOUNDARY",
            ),
            Topic(
                "Why capital-stack weights are not score multipliers",
                "The seed layer shares guide candidate discovery and source effort but do not directly alter TAFGS.",
                (
                    "A layer's current share of a reference project is not the same as a supplier's future addressable growth, market share, revenue exposure, or margin. Compute's large spend could already be reflected in growth expectations; construction's smaller share could still produce faster company growth for a focused contractor.",
                    "The growth forecast is where end-market demand, product cycle, supplier share, capacity, and project timing belong. Multiplying the capital weight again would double-count opportunity and hard-code one illustrative project mix into every company and geography.",
                ),
                status="BOUNDARY",
            ),
            Topic(
                "FastAPI interface",
                "The API exposes health, source operations, evidence review, research runs, rankings, evaluations, reports, and audit history.",
                (
                    "Pydantic request models bound dates, string lengths, enumerations, result limits, lookback days, and document limits. Long source sync, extraction, and research calls run through asyncio.to_thread so the async server loop remains responsive. Domain errors become 422 responses, missing records 404, publication conflicts 409, and database readiness failures 503.",
                    "The root workbench, health, readiness, and metrics endpoints are unprotected in the reference service. /api/v1 operations require the configured X-API-Key. This is a pilot control; production needs SSO, RBAC, user identity in audit events, CSRF/session controls for the UI, and secret-manager integration.",
                ),
                status="BOUNDARY",
            ),
            Topic(
                "Complete API surface",
                "The versioned API is organized around configuration, companies, sources, proposals, runs, review, reports, and evaluation.",
                table_headers=("Method", "Path", "Purpose"),
                table_rows=(("GET", "/health | /ready | /metrics", "Runtime health and process telemetry"), ("GET", "/api/v1/config/segments", "Taxonomy segments"), ("GET", "/api/v1/companies[/{id}]", "Universe, documents, identifiers"), ("GET", "/api/v1/sources | /source-syncs", "Source capability and history"), ("POST", "/api/v1/sources/{id}/sync", "Bounded connector operation"), ("POST/GET", "/api/v1/evidence/extract | /proposals", "Create/list review-only proposals"), ("POST", "/api/v1/evidence/proposals/{id}/review", "Accept or reject evidence"), ("POST/GET", "/api/v1/runs", "Execute/list point-in-time runs"), ("GET", "/api/v1/runs/{id}/rankings", "Ordered output"), ("GET", "/api/v1/runs/{id}/assessments[/{company}]", "Dossiers"), ("POST", "/api/v1/runs/{id}/assessments/{company}/reviews", "Human dossier decision"), ("POST", "/api/v1/runs/{id}/publish", "Apply publication gate"), ("POST/GET", "/api/v1/runs/{id}/report", "Generate/download report"), ("GET", "/api/v1/runs/{id}/audit | /evaluation", "Governance and quality"), ("GET", "/api/v1/runs/{previous}/compare/{current}", "Quarter-to-quarter diff")),
            ),
            Topic(
                "CLI and automation surface",
                "The CLI exposes the same service methods for local operation, scheduled jobs, and reproducible runbooks.",
                table_headers=("Group", "Commands"),
                table_rows=(("Initialize/demo", "init-db, seed-demo, reset-demo, approve-ranked-demo"), ("Sources", "source-list, source-syncs, source-sync, ingest-sec"), ("Evidence", "ingest, extract-evidence, list-proposals, review-proposal"), ("Research", "run, quarterly-refresh, list-runs, list-companies, show-run"), ("Governance", "review, evaluate, compare-runs, generate-report, publish"), ("Runtime", "model-check, serve")),
                code="aifactory quarterly-refresh --generate-report\naifactory evaluate RUN_ID\naifactory compare-runs PREVIOUS CURRENT\naifactory publish RUN_ID --actor analyst@example.com",
            ),
            Topic(
                "Primary analyst user journey",
                "The analyst moves from source freshness to evidence decisions, ranking review, and controlled publication.",
                bullets=("Choose and freeze the cutoff date.", "Inspect source catalog, credentials readiness, and recent sync failures.", "Sync universe, issuer filings, identity, and discovery sources.", "Review archived documents, parser flags, and claim proposals.", "Accept or reject each evidence proposal with a comment.", "Run selected or complete eligible universe.", "Inspect non-rankable validation errors and Top-20 scenario sensitivity.", "Approve every ranked dossier.", "Publish report and archive manifest.", "Compare with the previous quarter and explain material changes."),
            ),
            Topic(
                "Data steward user story",
                "As a data steward, I need to add or change a provider without leaking credentials, weakening rights, or changing scoring authority silently.",
                (
                    "Acceptance criteria include a disabled catalog entry, documented purpose and evidence tier, environment-only authentication, official endpoint links, bounded transport values, raw-response retention, parser and entity fixtures, licence/retention review, model-processing review, and benchmark results.",
                    "The steward can list public capability metadata and see whether a required environment variable is configured, but the API never returns its value. Enablement occurs only after implementation_status changes to implemented and the code-owned registry contains the adapter.",
                ),
            ),
            Topic(
                "Methodology owner user story",
                "As a methodology owner, I need to change taxonomy, weights, thresholds, prompts, or formulas without silent rank drift.",
                (
                    "The owner creates a new version, runs it on a frozen analyst-labelled benchmark, produces score and rank differences, inspects sensitivity by segment and research dimension, and obtains model-risk and research approval. The default changes only after release gates pass.",
                    "Every research run stores the taxonomy, scoring, prompt, model, source-policy, runtime, formula manifest, and selected company IDs. Old runs remain reproducible under their original version set.",
                ),
            ),
            Topic(
                "Operator and auditor user stories",
                "Operators watch execution health; auditors reproduce evidence and decisions. Neither role may silently change the score.",
                table_headers=("Actor", "Journey", "Evidence of completion"),
                table_rows=(("Platform operator", "Monitor syncs, logs, metrics, durations, company failures, and scheduled run status", "Run/audit records and alerts"), ("Model-risk reviewer", "Inspect prompts, schemas, invalid proposals, benchmark drift, and provider changes", "Approval record and benchmark report"), ("Auditor", "Resolve report hash -> run versions -> assessments -> claim IDs -> document hashes -> raw bytes", "Exact score and report reproduction")),
            ),
            Topic(
                "Quarterly refresh user story",
                "The quarterly workflow is a governed research release, not simply a scheduled model call.",
                (
                    "The CronJob starts the command at 06:00 UTC on the fifth day of January, April, July, and October with concurrencyPolicy=Forbid. The human runbook confirms rights and source health, freezes the cutoff, syncs evidence, validates taxonomy, reviews proposals, executes the graph, evaluates and compares, resolves conflicts, approves the Top 20, and publishes.",
                    "A filing-aware event trigger may supplement the calendar. Re-running after a material filing creates a new run and comparison; the existing published result remains intact.",
                ),
            ),
            Topic(
                "Volume II implementation checklist",
                "Use this checklist to verify that agentic behavior remains bounded and reproducible.",
                bullets=("Every agent has one owned decision and typed output.", "Workflow state contains no credentials or cross-company evidence.", "The node order is explicit and versioned.", "Model calls use strict schemas and bounded tokens.", "Evidence proposals require exact quotes and human review.", "Arithmetic and ranking execute only in deterministic code.", "A skeptic node validates coverage, tiers, contradictions, and thresholds.", "Company failures are isolated and persisted.", "Rank confidence remains separate from rank.", "Publication reads human review status from the database."),
            ),
            Topic(
                "Volume II references",
                "Primary implementation files and framework/provider references used for this volume.",
                paragraphs=("Repository ground truth: src/aifactory/models.py, agents/roles.py, workflow.py, scoring.py, service.py, llm.py, extraction.py, api.py, cli.py, evaluation.py, and reporting.py; config/prompts/*.txt, scoring_policy.json, and extraction_policy.json; docs/agents-and-prompts.md and scoring-methodology.md.", "No provider documentation is treated as evidence for company scores. Framework and model links explain runtime integration only."),
                links=(("OpenRouter quickstart", "https://openrouter.ai/docs/quickstart"), ("Nemotron 3.5 Lightning free", "https://openrouter.ai/nvidia/nemotron-3.5-lightning:free"), ("LangGraph documentation", "https://docs.langchain.com/oss/python/langgraph/overview"), ("FastAPI documentation", "https://fastapi.tiangolo.com/")),
            ),
        ]
    )
    return topics


def build_volume_two(path: Path) -> None:
    doc = TechnicalDocTemplate(str(path), title="AI Factory Research Platform - Volume II", volume_label="VOLUME II - AGENTS, WORKFLOW AND SCORING")
    story: list[Flowable] = cover_story(
        "VOLUME II",
        "Agentic Design, Workflow and Scoring",
        "A detailed explanation of the multi-agent design patterns, framework choices, role contracts, prompts, state graph, model routing, equations, interfaces, and user journeys.",
        "Why the system is agentic, why its autonomy is bounded, how every node works, and how qualitative research becomes a deterministic portfolio rank.",
    )
    story.extend(toc_story("Read after Volume I. This volume assumes that identity, documents, and accepted claims already exist. It explains how the bounded agent network interprets them and how deterministic services produce the final rank."))
    story.extend([
        h1("Company workflow at a glance"), Rule(), Spacer(1, 5 * mm),
        p("The graph is sequential inside one dossier and parallel across companies. The skeptic is the only node that authorizes final deterministic scoring.", "lead"),
        flow_diagram(["Eligibility", "Evidence", "Exposure", "Moat", "Margin"]),
        Spacer(1, 5 * mm),
        flow_diagram(["Growth", "Risk", "Skeptic", "Narrative", "Persist"]),
        Spacer(1, 7 * mm),
        callout("Design rule", "Agents interpret and validate bounded evidence. Code calculates, sorts, persists, evaluates, and enforces release gates."),
        PageBreak(),
    ])
    for index, topic in enumerate(volume_two_topics(), start=1):
        story.extend(topic_page(topic, index))
    doc.multiBuild(story)


def volume_three_topics() -> list[Topic]:
    topics: list[Topic] = [
        Topic(
            "Trust model",
            "The system treats the internet, parser output, model output, and analyst override as separate trust boundaries.",
            (
                "Internet content is untrusted and may be malicious, inaccurate, stale, or contractually restricted. Parser output is untrusted until identity, date, unit, schema, and lineage checks pass. Model output is untrusted until exact-quote, type, range, unit, period, confidence, contradiction, and human-review checks pass. Analyst decisions are privileged and must be authenticated and audited.",
                "Published reports contain only approved claims and deterministic calculations. Trust increases through explicit verification stages; it is never granted because a source looks professional or a model sounds confident.",
            ),
            code="UNTRUSTED INTERNET -> HASHED RAW -> VALIDATED DOCUMENT -> PROPOSAL\n  -> HUMAN-ACCEPTED CLAIM -> DETERMINISTIC ASSESSMENT -> APPROVED REPORT",
        ),
        Topic(
            "Threat model",
            "Threats include malicious content, unsafe networking, evidence manipulation, model drift, secret leakage, and privileged misuse.",
            table_headers=("Threat", "Primary control"),
            table_rows=(("Indirect prompt injection", "Quoted document context, signature flags, role prompt, no document tool authority"), ("SSRF", "HTTPS only, public DNS/IP, redirect revalidation"), ("Hallucinated figures", "Exact quote, schema, unit/range/period checks, human acceptance"), ("Data poisoning", "Source tiers, hashes, contrary evidence, review"), ("Look-ahead bias", "Frozen cutoff and filing-date filters"), ("Secret leakage", "Environment-only credentials and no secret-bearing state"), ("Cross-company leakage", "Company-scoped state and retrieval"), ("Silent model/prompt drift", "Versioned configuration and benchmark diff"), ("Ranking manipulation", "Deterministic code and reproducibility gate"), ("Malicious override", "Production RBAC + comments + audit"), ("Supply-chain compromise", "Pinned ranges, SBOM, signatures, scans")),
        ),
        Topic(
            "Prompt-injection guardrail",
            "Retrieved instructions are data, never authority.",
            (
                "The security module scans text for phrases such as ignore previous instructions, system prompt, developer message, reveal prompt/secret, call this tool, and exfiltration. Filing normalization scans up to the first 100,000 characters; normalized evidence packages scan document previews; discovery titles are scanned. Matches are stored as injection flags and counted.",
                "Detection is not the only defense. The common and extraction prompts explicitly state that source text is untrusted quoted material. Model contexts expose no retrieval, database-write, publication, or external-action tools. Exact quotes must still match the supplied chunk. A flagged document can be reviewed or excluded without executing any embedded instruction.",
            ),
            why="Signature scanning catches common attacks but can miss obfuscation. The decisive controls are least privilege, quoted context, deterministic validation, and human acceptance.",
        ),
        Topic(
            "SSRF and network-egress guardrail",
            "External data access is restricted to public HTTPS destinations and every redirect is revalidated.",
            (
                "validate_external_url rejects non-HTTPS schemes, missing hosts, localhost, .local names, private addresses, loopback, link-local, and reserved networks. Source requests resolve DNS and check every resolved address. HTTPX automatic redirects are disabled so up to six redirects can be followed manually with the same validation.",
                "A production cluster should add network-policy or proxy enforcement because application validation alone cannot defend against DNS rebinding, compromised dependencies, or alternate egress paths. Source workers should reach only approved domains and the model gateway; scoring, ranking, and reporting need no internet access.",
            ),
            status="BOUNDARY",
        ),
        Topic(
            "Credential and secret guardrail",
            "Secrets are referenced by environment variable name and injected only at the transport boundary.",
            (
                "Settings loads .env without overriding a value already supplied by the process. Source definitions contain only an auth type, header/query name, environment-variable name, and optional flag. SourceHttpClient reads the value immediately before the request. Public source metadata may reveal the required variable name and whether it is configured, but never the value.",
                "The model API key and pilot API key follow the same environment-only rule. Secrets do not enter source manifests, workflow state, prompts, report manifests, or audit payloads. Production should use short-lived credentials from a secret manager, distinct development/production accounts, spend and rate limits, and immediate rotation after disclosure.",
            ),
            status="BOUNDARY",
        ),
        Topic(
            "Connector-authority guardrail",
            "Configuration can select only adapters already registered in code.",
            (
                "SourceIngestionService owns a connector dictionary containing sec_edgar, gleif, and gdelt. sync fails when a source is disabled, planned, missing a credential, or names an unregistered connector. The catalog cannot supply an import path, code expression, shell command, or arbitrary tool.",
                "This fail-closed registry is a supply-chain boundary. Adding a provider requires a reviewed code change plus fixtures and governance, not only a configuration edit.",
            ),
        ),
        Topic(
            "Transport guardrails",
            "Per-source rate, time, retry, redirect, header, and body limits bound connector behavior.",
            table_headers=("Control", "Implemented behavior"),
            table_rows=(("Rate", "Monotonic minimum interval from catalog requests/second"), ("Timeout", "HTTPX timeout per source"), ("Retries", "1-8 attempts; 429/5xx and network errors only"), ("Backoff", "Retry-After clamped 0.25-30 sec; exponential fallback capped"), ("Redirects", "Maximum six, validated at every hop"), ("Response bytes", "Per-source hard cap after retrieval"), ("Headers", "Small safe allow list"), ("Errors", "Sanitized type/status without credentials")),
        ),
        Topic(
            "Evidence-integrity guardrails",
            "Every accepted claim carries enough structure to validate and reproduce its meaning.",
            (
                "Required fields include company, document, claim type, numeric/text value, unit, period, confidence, exact evidence span, page/section or chunk, source tier, publication date, cutoff eligibility, contradiction flag, and extraction method. Database foreign keys connect claims to the company and document.",
                "Proposal validation checks exact contiguous quote inclusion, permitted claim type, numeric finiteness/range, exact unit, narrative/numeric exclusivity, ISO period, and confidence cap. The skeptic checks required-claim coverage and Tier-1 authority for financials. The system retains invalid/rejected proposals and contradictory claims rather than hiding them.",
            ),
        ),
        Topic(
            "Point-in-time and look-ahead guardrails",
            "The research clock is enforced at request, source selection, document selection, claim query, and run-manifest levels.",
            (
                "A future run date is rejected. SEC filing and XBRL facts must be filed on or before the cutoff. Evidence extraction filters documents by publication date. Database list_claims excludes later and as_of_eligible=false records. The run stores the cutoff and selected company IDs.",
                "Historical corrections never replace the published record in place. A restatement or taxonomy change triggers a new run. Production should extend effective dating to security identity, currency rates, project states, and provider revisions.",
            ),
        ),
        Topic(
            "Financial-authority guardrail",
            "Reported revenue and operating margin require Tier-1 evidence and deterministic period alignment.",
            (
                "The margin agent requests a non-contradictory Tier-1 claim. The skeptic independently checks Tier-1 total revenue and operating margin. The SEC parser filters annual forms and fiscal periods, selects the most recent cutoff-eligible fact, and requires the operating-income period to equal the revenue period.",
                "This prevents a Tier-3 article, model narrative, quarterly/annual mismatch, or stale insertion from supplying a critical margin input. Adjusted and segment measures may be stored separately but cannot silently replace the documented rubric.",
            ),
        ),
        Topic(
            "Scoring guardrails",
            "Deterministic functions reject missing, non-finite, out-of-range, and unordered inputs before ranking.",
            bullets=("AI exposure must be within [0,1].", "Segment CAGR must be finite and greater than -100%.", "Forecast years must be positive.", "Every weighted component must exist and be within [0,5].", "Weight sum must be positive.", "Maximum risk discount must be within [0,1].", "Bear <= base <= bull.", "Moat and risk discount remain within ranges.", "Margin must be finite.", "Ties use company ID for deterministic order."),
        ),
        Topic(
            "Human-control guardrails",
            "Evidence acceptance and report publication require explicit, persisted human decisions.",
            (
                "Only pending, validation-clean proposals can be accepted. The reviewer and comment are stored on the proposal and in an audit event. Company reviews capture reviewer, decision, comment, and optional override metadata. The reference implementation records overrides but does not provide a separate deterministic override recalculation engine.",
                "The publication gate permits only completed/published runs and verifies that every ranked company is approved. Production must associate these actions with SSO/RBAC identities and separate research, methodology, data, and operations permissions.",
            ),
            status="BOUNDARY",
        ),
        Topic(
            "Operational-isolation guardrail",
            "A bad company, source, document, or model response should fail within its smallest safe boundary.",
            (
                "Source failures close their sync attempt, preserve cursor_before, record a sanitized error, and leave existing evidence intact. Invalid model proposals remain invalid and cannot be accepted. Expected dossier insufficiency becomes validation_errors rather than an exception. Unexpected company exceptions create a non-rankable assessment while other futures continue.",
                "The supervisor fails the entire run only when a portfolio-level operation cannot complete safely. Publication is always fail-closed. The incident process creates a corrected run instead of rewriting historical rows.",
            ),
        ),
        Topic(
            "API authentication boundary",
            "The reference X-API-Key is a pilot control, not an institutional identity system.",
            (
                "All /api/v1 operations depend on require_api_key, which compares the request header with AIFACTORY_API_KEY. The workbench HTML, /health, /ready, and /metrics are unprotected. Input schemas bound common abuse cases, but there is no per-user role, tenant, session, object authorization, or rate limit.",
                "Before shared deployment, place the service behind SSO/OIDC, implement RBAC and per-action audit identity, protect the UI session, restrict metrics/readiness exposure, add API and provider quotas, and retrieve secrets from a managed vault.",
            ),
            status="BOUNDARY",
        ),
        Topic(
            "Data privacy, retention, and model processing",
            "The intended data is public-company research, but licensed text, analyst notes, and provider logs still require policy.",
            (
                "Do not send confidential analyst notes, personal data, or licensed full transcripts to an unapproved free model endpoint. Retain only what the provider licence permits. Logs should contain identifiers, counts, error types, and evidence references rather than full documents or hidden reasoning.",
                "Production retention classes should cover raw public evidence, licensed documents, proposals, accepted claims, audit events, reports, security logs, and backups separately. Deletion must not break the integrity of a published report; where rights require deletion, retain a tombstone and impact record.",
            ),
            status="PLANNED",
        ),
        Topic(
            "Telemetry architecture",
            "The reference implementation combines structured JSON logs, process-local Prometheus metrics, timed operations, and persistent SQLite audit events.",
            (
                "Logs answer what happened now, metrics answer how often and how long in the current process, and audit events answer who changed research state across restarts. Context variables attach run_id and company_id to logs without passing them through every function call.",
                "The OTEL endpoint and optional OpenTelemetry packages are declared but no exporter is wired. The current metrics registry is in-memory and has no labels, histograms, persistence, or multi-process aggregation. Those limitations are explicit rather than implied by dependency declarations.",
            ),
            status="BOUNDARY",
        ),
        Topic(
            "Structured JSON logging",
            "Every application log line is machine-readable and correlation-aware.",
            table_headers=("Field", "Source and meaning"),
            table_rows=(("timestamp", "UTC ISO timestamp generated by formatter"), ("level", "Python logging severity"), ("logger", "Module/logger name"), ("message", "Sanitized human-readable event"), ("run_id", "Context variable for portfolio run"), ("company_id", "Context variable for dossier"), ("exception", "Formatted traceback when present"), ("event", "Optional operation/event name"), ("agent", "Optional graph node"), ("duration_ms", "Optional timed duration"), ("status", "ok or error")),
                code='{"timestamp":"...Z","level":"INFO","logger":"aifactory.service",\n "message":"research_run completed","run_id":"...","company_id":"",\n "event":"research_run","duration_ms":1250.4,"status":"ok"}',
        ),
        Topic(
            "Timed operations",
            "A context manager records duration and error count for source fetches, research runs, and every agent invocation.",
            (
                "timed_operation captures perf_counter at entry. On exception it sets status=error, increments {operation}_errors_total, and re-raises. In finally it records a duration observation and emits a structured log. Agent completion uses debug level; other operations use info.",
                "Current duration summaries expose only count and sum. Production should export histogram buckets or exemplars with run/source/agent attributes, while avoiding company ticker as a high-cardinality metric label when a trace/log correlation ID is sufficient.",
            ),
            code="with timed_operation('source_fetch', logger): ...\nwith timed_operation('research_run', logger): ...\nwith timed_operation('agent_execution', logger, agent=name): ...",
        ),
        Topic(
            "Process metrics captured",
            "The registry exposes counters and summary count/sum series with the aifactory_ prefix.",
            table_headers=("Metric family", "Meaning"),
            table_rows=(("source_fetch_total", "Successful bounded source responses"), ("source_fetch_retry_total", "Transport/provider retries"), ("source_fetch_errors_total", "Timed source operation errors"), ("source_sync_completed_total", "Completed/not-modified source syncs"), ("source_sync_failed_total", "Failed source syncs"), ("source_prompt_injection_flags_total", "Documents with detected signatures"), ("agent_{name}_total", "Executions per graph node"), ("agent_execution_errors_total", "Unhandled node errors"), ("company_workflow_failures_total", "Isolated company exceptions"), ("research_runs_completed_total", "Successful portfolio runs"), ("research_runs_failed_total", "Failed portfolio runs"), ("*_seconds_count/sum", "Timed operation summary")),
        ),
        Topic(
            "Prometheus endpoint and limitations",
            "GET /metrics renders the in-memory registry as Prometheus text.",
            (
                "Metric names replace non-alphanumeric characters with underscores and add the aifactory_ prefix. Counters emit a TYPE line and value. Duration summaries emit TYPE summary plus seconds_count and seconds_sum. A lock protects concurrent updates.",
                "The endpoint is process-local. Restarting resets metrics; multiple workers do not aggregate; labels, buckets, HELP text, and exemplars are absent. Production should use a Prometheus client or OpenTelemetry SDK and a collector, and should protect the endpoint from unauthenticated external access.",
            ),
            status="BOUNDARY",
        ),
        Topic(
            "Persistent audit events",
            "Audit events preserve research and governance actions after logs and process metrics are gone.",
            table_headers=("Event", "Actor", "Key payload"),
            table_rows=(("source_sync_completed/failed", "source_ingestion_service", "source, scope, status, counters or error type"), ("evidence_extraction_completed", "evidence_proposal_service", "documents, pending/invalid, policy, model"), ("claim_proposal_reviewed", "reviewer", "proposal, decision, claim ID, comment"), ("run_started/completed/failed", "workflow_supervisor/ranking_service", "counts, runtime, error type"), ("company_assessed", "workflow_supervisor", "rankable, score, validation errors"), ("assessment_reviewed", "reviewer", "decision, comment, overrides"), ("run_published", "actor", "report and manifest paths"), ("demo_seeded / package_ingested", "system/service", "record counts")),
                paragraphs=("audit_events stores UUID, optional run and company IDs, actor, event_type, JSON payload, and creation time. The list endpoint supports run-scoped review.",),
        ),
        Topic(
            "Correlation and trace model",
            "run_id and company_id are the primary correlations; source sync and proposal IDs add operation-level lineage.",
            (
                "The company workflow sets context variables before executing nodes and resets them in finally. The service sets run context for the portfolio. Source syncs, proposals, documents, claims, assessments, and reviews each have stable IDs that appear in database relationships and audit payloads.",
                "Production OpenTelemetry should create one quarterly-run trace, child source-sync and company-workflow spans, and node/model/parser spans. Attributes should include versions, source ID, agent name, status, counts, and hashes - not raw prompts, secret values, licensed text, or hidden reasoning.",
            ),
            status="PLANNED",
        ),
        Topic(
            "Observability signal matrix",
            "A complete operating view connects sources, parsers, models, agents, scoring, review, and publication.",
            table_headers=("Stage", "Signals to capture", "Primary diagnosis"),
            table_rows=(("Source", "availability, HTTP status, latency, retries, freshness, bytes", "Provider or network failure"), ("Parser", "raw/normalized counts, duration, failure reason, hash change", "Format drift and data quality"), ("Entity", "method, score, ambiguity, override", "Wrong issuer/security"), ("Model", "provider/model, latency, tokens/cost, schema error, proposal count", "Drift, budget, invalid output"), ("Agent", "duration, validation errors, evidence coverage", "Research bottleneck"), ("Score", "reproducibility, sensitivity, non-finite rejection", "Method/code regression"), ("Review", "queue age, acceptance/rejection reasons, approval coverage", "Human bottleneck"), ("Publication", "gate failures, report hash, delivery", "Governance/release issue")),
                status="PLANNED",
        ),
        Topic(
            "Alerts and operating thresholds",
            "Alerts should correspond to user impact or research-integrity risk, not every warning.",
            bullets=("Any failed scheduled quarterly run.", "More than 5% company-workflow failures.", "Source freshness beyond a segment/provider threshold.", "Repeated provider 429/5xx or credential failures.", "Citation coverage below 85% or declining materially.", "Score reproducibility below 100%.", "Unexpected Top-20 churn without material evidence change.", "Proposal invalid/rejection rate outside baseline.", "Model latency, token use, or cost above budget.", "Publication attempted with incomplete approval.", "Backup or restore drill failure."),
            status="PLANNED",
        ),
        Topic(
            "Service-level objectives",
            "Initial SLOs balance research integrity, scheduled reliability, read availability, and recoverability.",
            table_headers=("SLO", "Initial target", "Measurement source"),
            table_rows=(("Scheduled run completion", "99%", "research_runs + scheduler"), ("Score reproducibility", "100%", "evaluate_run"), ("Required numeric citation coverage", "100%", "claim/assessment audit"), ("Mean full-dossier citation coverage", ">=95%", "evaluation metrics"), ("Rankable workflow success", ">=95%", "assessment/ranking counts"), ("API read availability", "99.5%", "external probe"), ("Restore point objective", "24 hours", "backup policy"), ("Restore time objective", "4 hours", "restore drills")),
                status="PLANNED",
        ),
        Topic(
            "OpenTelemetry target design",
            "The production target exports traces and metrics through an organization collector without leaking research content.",
            (
                "The pyproject already declares OpenTelemetry API, SDK, and OTLP HTTP exporter extras, and Settings includes AIFACTORY_OTEL_ENDPOINT. Wiring should create resource attributes for service/version/environment, instrument FastAPI and HTTPX, and wrap source sync, parser, extraction, company graph, agent, scorer, report, and publication operations.",
                "Use sampling and redaction policies. Do not export full prompts, model completions, raw documents, API keys, authorization headers, analyst comments containing sensitive data, or hidden reasoning. Store stable hashes and IDs so authorized operators can join telemetry to the evidence ledger.",
            ),
            status="PLANNED",
        ),
        Topic(
            "LLM telemetry and model-risk capture",
            "Model observability must measure behavior without turning telemetry into a second ungoverned data lake.",
            (
                "Capture provider, model, endpoint class, prompt/extraction-policy version, request duration, completion cap, token counts when returned, cost estimate, HTTP error class, JSON parse outcome, required-key outcome, proposal count, invalid reasons, human acceptance/rejection, and fallback usage.",
                "Do not capture credentials, full licensed content, private analyst notes, or hidden reasoning. Sample prompt/completion bodies only in an approved evaluation store with explicit retention and access. Hash canonical request context to detect repeatability without retaining everything in logs.",
            ),
            status="PLANNED",
        ),
        Topic(
            "Evaluation philosophy",
            "The platform evaluates deterministic correctness, evidence fitness, scenario stability, and human readiness separately.",
            (
                "A single LLM-as-judge score would conceal whether a failure came from identity, source quality, arithmetic, unsupported claims, or writing style. evaluate_run therefore recomputes numeric outputs from stored fields and reports multiple metrics and release gates.",
                "Model/agent quality needs a separate point-in-time analyst-labelled benchmark. LLM judges may supplement human labels only after calibration and must preserve judge prompt/model versions. Production model changes cannot affect default proposals until the benchmark and rank-diff gates pass.",
            ),
        ),
        Topic(
            "Implemented run-evaluation metrics",
            "evaluate_run reads the persisted run, assessments, and rankings and derives eight integrity metrics.",
            table_headers=("Metric", "Calculation / interpretation"),
            table_rows=(("assessment_count", "All persisted company dossiers"), ("ranked_count", "Portfolio outputs after Top-N"), ("rankable_rate", "rankable assessments / all assessments"), ("mean_evidence_confidence", "Mean tier-adjusted claim confidence by dossier"), ("mean_citation_coverage", "Mean required-claim coverage"), ("score_reproducibility_rate", "Stored score matches deterministic recomputation within 1e-9"), ("unsupported_required_claim_count", "Validation errors containing missing/lack"), ("mean_scenario_rank_stability", "Bear/bull spread normalized across ranking"), ("ranked_approval_coverage", "Approved ranked companies / ranked companies")),
        ),
        Topic(
            "Research-ready and publication-ready gates",
            "Evaluation separates a methodologically usable result from one authorized for external release.",
            (
                "Research-ready requires 100% score reproducibility, mean citation coverage at or above policy, mean evidence confidence at or above policy, and nonempty rank output. Publication-ready requires all research gates plus 100% ranked approval coverage.",
                "These are portfolio-level checks. A company can still be excluded for its own missing evidence while the remaining portfolio is research-ready, provided the rankable-rate and operating policies are acceptable. Production should add minimum universe coverage and segment-balance gates.",
            ),
        ),
        Topic(
            "Score reproducibility evaluation",
            "Every stored risk-adjusted score is recalculated from the stored moat, margin score, company CAGR, and risk discount.",
            (
                "The evaluator multiplies moat_score, operating_margin_score, forecast.base_company_ai_cagr, 100, and one minus risk_discount. Absolute difference from stored risk_adjusted_tafgs must be at most 1e-9. The rate must equal one for the release gate.",
                "A failure indicates code/version drift, corrupt persistence, unexpected override behavior, or a report built from inconsistent data. The appropriate response is to pause publication, identify the affected run and version, and create a corrected run after remediation.",
            ),
        ),
        Topic(
            "Golden benchmark design",
            "Before production model changes, create a frozen analyst-labelled set of at least 30-50 companies across all five capital layers.",
            bullets=("Preserve the exact source bundle and cutoff analysts saw.", "Include exact XBRL and margin labels.", "Cover currency, unit, period, and accounting-basis normalization.", "Include public-parent, ADR, dual-listing, merger, and ambiguous-name cases.", "Label exposure intervals and methods.", "Label all moat and risk components with rationale evidence.", "Define bear/base/bull drivers and walk-forward outcomes.", "Include unsupported, contradictory, and prompt-injection documents.", "Measure rank sensitivity and quarterly churn.", "Test narrative no-new-facts and citation correctness."),
            status="PLANNED",
        ),
        Topic(
            "Agent-specific evaluation",
            "Each role has a metric aligned with its own decision boundary.",
            table_headers=("Agent", "Primary evaluation"),
            table_rows=(("Eligibility", "Identity precision/recall and ambiguous-match escalation"), ("Evidence", "Tier/coverage calculation and contradiction recall"), ("Exposure", "Analyst interval overlap and materiality error"), ("Moat", "Component-level agreement and evidence coverage"), ("Margin", "Exact numeric and accounting-period match"), ("Growth", "Driver coverage, scenario ordering, walk-forward calibration"), ("Risk", "Category recall and severity agreement"), ("Skeptic", "Unsupported-claim recall versus false rejection"), ("Narrative", "No-new-facts rate and citation correctness")),
                status="PLANNED",
        ),
        Topic(
            "Red-team corpus",
            "Adversarial documents test the full evidence boundary, not only prompt wording.",
            bullets=("Ignore-previous-instructions and fake tool-call content.", "Hidden HTML/PDF text and white-on-white instructions.", "Conflicting currencies and unit multipliers.", "Later-dated restatements inserted into historical runs.", "Subsidiary names designed to map to the wrong public parent.", "Duplicate filings with different hashes.", "News estimates presented as reported company facts.", "Malformed JSON and schema-confusing output.", "Oversized responses, redirect chains, and unsafe DNS targets.", "Analyst override attempts without correct role."),
            why="The expected outcome is a flagged, invalid, rejected, or non-rankable record. The system never takes autonomous corrective action against an external source.",
        ),
        Topic(
            "Executable test suite",
            "The repository contains 29 tests across configuration, scoring, security, ingestion, extraction, sources, model routing, and end-to-end publication.",
            table_headers=("Suite", "Representative checks"),
            table_rows=(("test_config", "Dotenv does not override runtime values"), ("test_security", "Injection flag, HTTPS/private-network rejection"), ("test_scoring", "Margin boundaries, finiteness, exposure materiality, risk, deterministic score"), ("test_ingestion", "XBRL cutoff/period and prompt flag persistence"), ("test_llm", "OpenRouter URL, JSON parsing, schema and token cap"), ("test_sources", "Secret redaction, idempotent storage, cursors, auth, response cap"), ("test_extraction", "Model proposal requires review before evidence"), ("test_end_to_end", "Seed -> run -> rank -> report -> review -> publish; missing evidence excludes")),
        ),
        Topic(
            "Change control and model governance",
            "Any source tier, parser, prompt, model, taxonomy, formula, risk weight, or threshold change is a research-method release.",
            bullets=("Assign a new version.", "Run the frozen benchmark.", "Produce extraction, score, and rank differences.", "Measure segment and subgroup regressions.", "Review invalid/rejection and abstention changes.", "Confirm data-rights and security impact.", "Obtain methodology and model-risk approval.", "Deploy with rollback and retain the prior version."),
            status="PLANNED",
        ),
        Topic(
            "Governance roles and separation of duties",
            "Method, data, research, operations, model risk, and security require distinct accountability.",
            table_headers=("Role", "Owns", "Must not do silently"),
            table_rows=(("Research owner", "Methodology, taxonomy, thresholds", "Change defaults without benchmark"), ("Data steward", "Sources, rights, retention", "Enable unreviewed provider"), ("Analyst", "Evidence/dossier review and release", "Rewrite historical score"), ("Platform operator", "Reliability, deployment, restore", "Alter scoring data"), ("Model-risk reviewer", "Model/prompt approval", "Approve based only on demos"), ("Security owner", "Threat model, egress, incident", "Expose secrets or weaken controls")),
            status="PLANNED",
        ),
        Topic(
            "Local and single-node deployment",
            "The simplest supported deployment runs one process with a persistent artifact volume.",
            (
                "A Python environment installs the base package and launches Uvicorn. Settings point to config/, artifacts/aifactory.db, artifacts/raw-sources, and artifacts/reports. One API/workflow process avoids SQLite multi-writer conflicts. The operator supplies a non-default API key and a real SEC contact User-Agent.",
                "This mode is appropriate for a developer or controlled pilot. Backups must capture database, raw artifacts, reports, and config versions together. The workbench and metrics exposure should be restricted if the host is shared.",
            ),
        ),
        Topic(
            "Docker and Compose deployment",
            "The image uses Python 3.12 slim, installs the package, runs as non-root UID 10001, exposes port 8000, and includes a health check.",
            (
                "compose.yaml fails closed unless AIFACTORY_API_KEY and AIFACTORY_SEC_USER_AGENT are supplied. It mounts one named volume at /app/artifacts and maps source/model environment variables. The container starts Uvicorn on 0.0.0.0 and restarts unless stopped.",
                "For production, build in CI, pin the base image digest, generate an SBOM, scan dependencies and image layers, sign the image, use a private registry, inject secrets at runtime, and restrict egress.",
            ),
            status="BOUNDARY",
        ),
        Topic(
            "Kubernetes quarterly CronJob",
            "The supplied manifest schedules a prohibited-overlap refresh at 06:00 UTC on the fifth day of each quarter-opening month.",
            table_headers=("Field", "Configured value"),
            table_rows=(("schedule", "0 6 5 1,4,7,10 *"), ("concurrencyPolicy", "Forbid"), ("successful history", "4"), ("failed history", "4"), ("backoffLimit", "2"), ("restartPolicy", "Never"), ("command", "aifactory quarterly-refresh --generate-report"), ("secret", "aifactory-secrets"), ("volume", "aifactory-data PVC at /app/artifacts")),
                paragraphs=("The placeholder image must be replaced. More than one writer requires PostgreSQL first. Plain Kubernetes Secret objects should be replaced by a secret-manager integration in an institutional deployment.",),
                status="BOUNDARY",
        ),
        Topic(
            "Quarterly operating runbook",
            "The scheduled command starts automation; the release remains a controlled research process.",
            bullets=("Confirm source licences, credentials, and connector health.", "Freeze the research cutoff.", "Sync filings, IR, project, technical, and discovery evidence.", "Review taxonomy and capital-weight assumptions.", "Validate parser outputs and adjudicate proposals.", "Execute the company graph and portfolio rank.", "Evaluate the run and compare with the previous quarter.", "Resolve contradictions and investigate unexpected churn.", "Review every provisional Top-20 dossier.", "Publish and archive the report, manifest, benchmark, and approvals."),
        ),
        Topic(
            "Backup strategy",
            "A valid backup is a consistent set of transactional data, raw evidence, reports, and method versions.",
            (
                "On the reference node, stop writes or use SQLite's online backup API, then copy the database, raw-sources directory, reports directory, and exact configuration release together. Hash the backup inventory and test restoration quarterly.",
                "Production uses PostgreSQL point-in-time recovery, versioned object retention, immutable report manifests in a separate location, encryption, access logging, and cross-region copies according to policy. Redis caches and in-memory metrics are not authoritative backup data.",
            ),
            status="PLANNED",
        ),
        Topic(
            "Restore and reproducibility drill",
            "A restore is complete only when the system can reproduce the stored research output, not merely open the database.",
            bullets=("Restore the database to the selected timestamp.", "Restore raw and report object versions.", "Verify content hashes and missing-object inventory.", "Load the exact configuration/prompt release.", "Recompute stored assessment scores.", "Regenerate the report and match its SHA-256.", "Confirm audit chronology and review state.", "Measure RPO/RTO and document gaps."),
            status="PLANNED",
        ),
        Topic(
            "Incident response",
            "Integrity incidents pause publication while preserving evidence acquisition and forensic history when safe.",
            bullets=("Pause publication and scheduled scoring.", "Identify affected runs, sources, documents, prompts, models, parsers, and credentials from manifests.", "Preserve raw evidence, logs, audit events, and provider response metadata.", "Revoke compromised credentials or disable the connector/model route.", "Assess rank/report impact and notify owners.", "Correct code, source, or policy under change control.", "Create a new run; do not rewrite historical rankings.", "Record cause, remediation, validation, and communication."),
            status="PLANNED",
        ),
        Topic(
            "Failure-semantics matrix",
            "Every layer has a defined safe failure state and retained evidence.",
            table_headers=("Boundary", "Behavior"),
            table_rows=(("Source retrieval", "Bounded retry; failed sync; cursor unchanged; sanitized error"), ("Parser", "Raw bytes preserved; parser failure recorded; alternate parser may retry"), ("Model", "Invalid/error proposal operation; no accepted claim"), ("Agent validation", "Error accumulated; dossier non-rankable"), ("Company exception", "Persist isolated failure; portfolio continues"), ("Scoring", "Reject non-finite/missing/range/order errors"), ("Portfolio", "Run fails only if fan-in/persistence cannot complete safely"), ("Publication", "Conflict until every ranked dossier is approved"), ("Correction", "New immutable run and rank diff")),
        ),
        Topic(
            "Scaling path",
            "Scale only after measuring real source, parser, model, and company-workflow load.",
            bullets=("Keep one process and SQLite while validating method and evidence quality.", "Move repositories to PostgreSQL before multiple writers.", "Move raw and rendered documents to versioned object storage.", "Separate API replicas from workers.", "Use Temporal for durable quarterly/source workflows.", "Partition company workflows and bound each provider's concurrency.", "Use Redis for distributed rate limits and locks, not evidence.", "Cache by document hash plus prompt/policy version, never ticker alone.", "Add OTLP, SSO/RBAC, secret manager, and egress policy.", "Load-test, restore-test, and red-team before broad access."),
            status="PLANNED",
        ),
        Topic(
            "PostgreSQL migration",
            "The production database must implement the same repository semantics with migrations and multi-writer transactions.",
            (
                "The pyproject declares psycopg, SQLAlchemy, and Alembic, but installing them does not migrate storage. Implement a repository interface, translate schema and indexes, add effective-dated identity where required, use JSONB judiciously, and preserve uniqueness/idempotency keys.",
                "Migration should backfill SQLite data with counts and hashes, run dual-read or shadow verification, compare all assessments and ranks, then cut over writers. Connection pools, transaction isolation, statement timeouts, row-level access, PITR, and migration rollback become operational responsibilities.",
            ),
            status="PLANNED",
        ),
        Topic(
            "S3 or MinIO migration",
            "RawSnapshotStore is the seam for moving immutable evidence out of the local filesystem.",
            (
                "Use keys that preserve source ID, retrieval date, hash prefix, digest, and extension. Store sidecar metadata or object tags for source URL, content type, external ID, parser version, rights, and retention. Enable versioning, encryption, checksums, object lock where appropriate, and lifecycle rules.",
                "The database should store bucket/key/version ID plus SHA-256 rather than a local path. Retrieval for parsing must verify the digest. Reports and rendered PDF pages require separate prefixes and retention classes.",
            ),
            status="PLANNED",
        ),
        Topic(
            "Temporal outer orchestration",
            "Temporal is planned for durable source, quarterly, and portfolio workflows; LangGraph remains the bounded company research graph.",
            (
                "Temporal workflows can schedule source syncs, wait on rate-limited activities, retry transient provider failures, fan out company child workflows, record heartbeats, survive process restarts, and enforce idempotency. Human evidence and publication approvals can appear as signals or external state checks.",
                "Activities must use stable keys and avoid repeating irreversible side effects. The workflow history should store IDs and statuses, not licensed source bodies. LangGraph can execute inside a company activity because its role is local typed reasoning, not infrastructure durability.",
            ),
            status="PLANNED",
        ),
        Topic(
            "Redis, analytics, and vector retrieval",
            "Declared production extras support coordination and analysis but do not replace the evidence ledger.",
            table_headers=("Component", "Permitted role", "Not authoritative for"),
            table_rows=(("Redis", "Rate limits, locks, short caches", "Evidence or review decisions"), ("DuckDB/Polars", "Batch QA, benchmark analysis, rank diff", "Transactional system of record"), ("pgvector", "Semantic candidate retrieval", "Exact citation or accepted claim"), ("Arelle", "Taxonomy-aware XBRL validation", "Analyst exposure estimate"), ("Playwright", "Approved JS-only acquisition", "Scoring worker browser authority")),
            status="PLANNED",
        ),
        Topic(
            "Run-to-run comparison",
            "compare_runs explains portfolio movement without mutating either run.",
            (
                "Rankings are keyed by company. A company in both runs is retained with rank_change = previous rank minus current rank and score_change = current minus previous. A new company is entered; a missing company is exited. Results sort by current rank with exits last.",
                "The comparison should be joined with evidence, policy, parser, and model diffs to explain causality. Production reporting should classify movement as source update, identity change, claim review, methodology change, scenario change, or operational exclusion.",
            ),
        ),
        Topic(
            "Report and manifest reproducibility",
            "The report is a presentation of approved database records; the manifest is the verification handle.",
            (
                "ReportGenerator reads the run and ranking rows, renders methodology and company profiles, writes Markdown, and calculates its SHA-256. The adjacent JSON manifest stores run ID, cutoff, status, generation time, taxonomy/scoring/prompt/model versions, ranked count, report hash, and sorted unique evidence claim IDs.",
                "An auditor can reload the run, resolve assessments and claims, regenerate the report, and compare the hash. Publication writes a run_published audit event naming both artifacts.",
            ),
        ),
        Topic(
            "Current workspace implementation snapshot",
            "The local artifact database demonstrates the platform lifecycle but should not be confused with a production research publication.",
            table_headers=("Record type", "Current count"),
            table_rows=(("Companies", "25"), ("Market segments", "5"), ("Source documents", "67"), ("Evidence claims", "402"), ("Entity identifiers", "11"), ("Source cursors", "4"), ("Source sync runs", "9"), ("Claim proposals", "8"), ("Research runs", "6"), ("Company assessments", "43"), ("Rankings", "43"), ("Audit events", "66")),
                paragraphs=("The repository includes a 20-company synthetic fixture explicitly marked demo and live connector artifacts. Counts are a September 2026 workspace snapshot, not a claim of complete global coverage or an investment recommendation.",),
                status="BOUNDARY",
        ),
        Topic(
            "Known limitations",
            "The reference platform is real and testable, but several institutional capabilities remain deliberately incomplete.",
            bullets=("Valuation and expected return are absent.", "Global regulator coverage is incomplete.", "PDF/page-aware parsing is not implemented.", "SQLite/local files support one controlled node, not horizontal writers.", "API authentication is a single header key.", "Metrics are local and OTLP export is unwired.", "Outer orchestration is not durable across process loss.", "Review overrides are recorded but not deterministically recalculated.", "Security master effective dating and corporate actions need expansion.", "Licensed data rights and vendor contracts require procurement review."),
            status="BOUNDARY",
        ),
        Topic(
            "Recommended roadmap",
            "Implementation order follows research value and control maturity rather than adding the largest number of connectors.",
            table_headers=("Order", "Capability", "Reason"),
            table_rows=(("1", "Harden SEC + GLEIF pilot", "Reliable identity/financial foundation"), ("2", "IR RSS/sitemap + page-aware PDF", "Unlock exposure, backlog, catalysts, risk"), ("3", "EU/UK/Japan filings", "Selected global universe"), ("4", "OpenFIGI/security master", "Share-class and corporate-action integrity"), ("5", "EIA/utility/awards/projects", "Independent demand evidence"), ("6", "Licensed transcripts/news/market data", "Coverage after rights evaluation"), ("7", "Postgres + S3 + Temporal", "Durable horizontal data plane"), ("8", "SSO/RBAC + OTLP + immutable retention", "Institutional controls"), ("9", "Frozen analyst benchmark", "Safe model/provider iteration")),
            status="PLANNED",
        ),
        Topic(
            "Production readiness acceptance criteria",
            "A production release is ready only when data, model, software, security, operations, and research controls all pass.",
            bullets=("Approved source rights and machine-processing terms.", "Point-in-time global security master for selected universe.", "Parser benchmarks for every enabled content type.", "PostgreSQL migrations and object-store integrity tests.", "Durable orchestration with idempotent activities.", "SSO/RBAC, secret manager, approved egress, signed image, SBOM, vulnerability scans.", "OTLP telemetry, alerts, dashboards, and retention.", "Golden dataset and agent/model release thresholds.", "Backup/PITR and restore/reproduction drill.", "Analyst, methodology, model-risk, data, security, and operations sign-off."),
            status="PLANNED",
        ),
        Topic(
            "Operational checklist",
            "A compact checklist for the person responsible for a real quarterly execution.",
            bullets=("Verify API, database, raw store, and model readiness.", "Check source credentials without displaying values.", "Review last sync failures and freshness.", "Confirm cutoff and selected universe.", "Monitor retries, bytes, injection flags, proposals, and workflow failures.", "Run evaluation and require 100% score reproduction.", "Investigate coverage/confidence and scenario instability.", "Confirm every ranked dossier is approved.", "Publish, hash, archive, compare, and notify.", "Confirm backup and retention jobs captured the new release."),
        ),
        Topic(
            "Volume III references",
            "Primary implementation and operating specifications used for this volume.",
            paragraphs=("Repository ground truth: src/aifactory/security.py, telemetry.py, database.py, sources/http.py, extraction.py, service.py, evaluation.py, reporting.py, api.py; tests/*.py; pyproject.toml, Dockerfile, compose.yaml, deployment/quarterly-cronjob.yaml; docs/evaluation-and-security.md, operations.md, and deployment/README.md.", "Provider links in Volume I describe external data. This volume focuses on the controls that govern how that data and model output are handled."),
        ),
    ]
    return topics


def build_volume_three(path: Path) -> None:
    doc = TechnicalDocTemplate(str(path), title="AI Factory Research Platform - Volume III", volume_label="VOLUME III - SECURITY, TELEMETRY AND OPERATIONS")
    story: list[Flowable] = cover_story(
        "VOLUME III",
        "Security, Telemetry, Evaluation and Operations",
        "A detailed control manual for trust boundaries, guardrails, observability, model risk, testing, SLOs, deployment, backup, incident response, scaling, governance, and production readiness.",
        "What the platform records, how it fails safely, how operators know it is healthy, how reviewers approve it, and what must change before institutional scale.",
    )
    story.extend(toc_story("Read after Volumes I and II. This volume explains how the platform protects data and decisions, what telemetry is implemented, what evaluation proves, how quarterly operations run, and which production controls are still planned."))
    story.extend([
        h1("Control planes at a glance"), Rule(), Spacer(1, 5 * mm),
        p("Security and observability are cross-cutting planes. They surround the evidence and research pipeline rather than appearing only at the API edge.", "lead"),
        flow_diagram(["Egress guard", "Source bounds", "Evidence checks", "Human gate", "Release gate"]),
        Spacer(1, 5 * mm),
        flow_diagram(["JSON logs", "Metrics", "Audit ledger", "Evaluation", "Incident loop"]),
        Spacer(1, 7 * mm),
        callout("Operating invariant", "When the platform cannot prove identity, evidence authority, numeric validity, or approval, it preserves the record and withholds the rank or publication."),
        PageBreak(),
    ])
    for index, topic in enumerate(volume_three_topics(), start=1):
        story.extend(topic_page(topic, index))
    doc.multiBuild(story)


def build_all() -> list[Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    outputs = [
        OUTPUT_DIR / "AI_Factory_Platform_Volume_1_Data_Architecture.pdf",
        OUTPUT_DIR / "AI_Factory_Platform_Volume_2_Agents_Workflow_Scoring.pdf",
        OUTPUT_DIR / "AI_Factory_Platform_Volume_3_Security_Telemetry_Operations.pdf",
    ]
    build_volume_one(outputs[0])
    build_volume_two(outputs[1])
    build_volume_three(outputs[2])
    return outputs


if __name__ == "__main__":
    for output in build_all():
        print(output)
