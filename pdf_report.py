# ============================================================
# SP500 CYCLE ATLAS
# pdf_report.py
# ============================================================
#
# Gera:
# reports/relatorio_sp500_cycle_atlas.pdf
#
# Fonte principal:
# data/current_state.csv
#
# O PDF é uma camada de apresentação.
# Ele NÃO recalcula o ciclo.
#
# Dependência:
# reportlab
#
# Adicione ao requirements.txt:
# reportlab>=4.2.0
# ============================================================

from __future__ import annotations

from pathlib import Path
from datetime import datetime
import math

import pandas as pd

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
)

# ============================================================
# CAMINHOS
# ============================================================

DATA_DIR = Path("data")
REPORTS_DIR = Path("reports")

CURRENT_STATE_FILE = DATA_DIR / "current_state.csv"
CURRENT_REPORT_TXT = DATA_DIR / "current_report.txt"

PDF_FILE = REPORTS_DIR / "relatorio_sp500_cycle_atlas.pdf"

PROJECT_TITLE = "SP500 CYCLE ATLAS"
REPORT_TITLE = "Relatório Institucional de Ciclo e Política de Reserva"


# ============================================================
# CORES
# ============================================================

NAVY = colors.HexColor("#0F172A")
SLATE = colors.HexColor("#475569")
LIGHT = colors.HexColor("#F8FAFC")
BORDER = colors.HexColor("#E2E8F0")
GREEN = colors.HexColor("#15803D")
AMBER = colors.HexColor("#D97706")
RED = colors.HexColor("#B91C1C")
BLUE = colors.HexColor("#1D4ED8")
GRAY = colors.HexColor("#64748B")
WHITE = colors.white
BLACK = colors.HexColor("#111827")


# ============================================================
# UTILITÁRIOS
# ============================================================

def _valid(value) -> bool:
    try:
        return value is not None and not pd.isna(value)
    except Exception:
        return value is not None


def _safe_float(value, default=None):
    try:
        if not _valid(value):
            return default
        return float(value)
    except Exception:
        return default


def _fmt_number(value, decimals=2):
    value = _safe_float(value)
    if value is None:
        return "N/A"
    return f"{value:,.{decimals}f}"


def _fmt_pct(value, decimals=2):
    value = _safe_float(value)
    if value is None:
        return "N/A"
    return f"{value * 100:.{decimals}f}%"


def _fmt_pct_already_percent(value, decimals=2):
    value = _safe_float(value)
    if value is None:
        return "N/A"
    return f"{value:.{decimals}f}%"


def _fmt_pp(value, decimals=2):
    value = _safe_float(value)
    if value is None:
        return "N/A"
    return f"{value:+.{decimals}f} p.p."


def _date_text(value):
    """
    Formata a data-base do estado de forma defensiva.
    """
    if not _valid(value):
        return "N/A"

    try:
        parsed = pd.to_datetime(
            value,
            errors="coerce",
        )

        if pd.isna(parsed):
            return "N/A"

        return pd.Timestamp(parsed).strftime(
            "%d/%m/%Y"
        )

    except Exception:
        return "N/A"


def _escape(value):
    if value is None:
        return ""
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _display_value(value):
    mapping = {
        "HOLD": "MANTER POSIÇÃO",
        "HOLD_ACCUMULATE": "MANTER + ACUMULAR",

        "NOT_ACTIVE": "INATIVA - CONTINUAR ACUMULANDO",
        "PENDING_REGIME_CONFIRMATION": "PENDENTE - AGUARDAR SAÍDA DO RED",
        "DEPLOYMENT_ALLOWED": "LIBERADA PARA UTILIZAÇÃO",

        "YELLOW_EXPENSIVE_BULL": "AMARELO - ALTA COM VALUATION ELEVADO",
        "GREEN_EXPANSION": "VERDE - EXPANSÃO",
        "NEUTRAL_UNCERTAIN": "NEUTRO - INCERTEZA",
        "ORANGE_DETERIORATION": "LARANJA - DETERIORAÇÃO",
        "RED_STRUCTURAL_STRESS": "VERMELHO - STRESS ESTRUTURAL",
        "BLUE_REASSESS_ACCUMULATION": "AZUL - REAVALIAÇÃO / ACUMULAÇÃO",

        "EXTREME_TOP_1": "EXTREMO - TOP 1%",
        "EXTREME_TOP_5": "EXTREMO - TOP 5%",
        "VERY_HIGH": "MUITO ELEVADO",
        "HIGH": "ALTO",
        "NORMAL": "NORMAL",

        "STRONG_POSITIVE": "FORTEMENTE POSITIVO",
        "POSITIVE": "POSITIVO",
        "NEGATIVE": "NEGATIVO",

        "STABLE": "ESTÁVEL",
        "DETERIORATING": "DETERIORANDO",
        "DETERIORATION_SEVERE": "DETERIORAÇÃO SEVERA",

        "EXPANSION": "EXPANSÃO",
        "CONTRACTION": "CONTRAÇÃO",
        "CONTRACTION_STRONG": "CONTRAÇÃO FORTE",

        "REACCELERATING": "REACELERANDO",
        "FALLING": "DESACELERANDO",

        "EASING": "FLEXIBILIZAÇÃO",
        "TIGHTENING": "APERTO",

        "FLAT_POSITIVE": "POSITIVA, MAS ACHATADA",
        "NORMAL_POSITIVE": "POSITIVA NORMAL",
        "INVERTED": "INVERTIDA",

        "LATE_EXPANSION / VALUATION_EXTREME":
            "EXPANSÃO TARDIA / VALUATION EXTREMO",

        "MODERATE": "MODERADO",
        "LOW": "BAIXO",

        "NOT_CONFIRMED": "NÃO CONFIRMADO",
        "CONFIRMED": "CONFIRMADO",

        "BULL MARKET": "MERCADO DE ALTA",
        "BEAR MARKET": "MERCADO DE BAIXA",
        "BULL": "ALTA",
        "BEAR": "BAIXA",
    }

    return mapping.get(str(value), str(value))


def _regime_interpretation(regime):
    mapping = {
        "GREEN_EXPANSION":
            "O ambiente é predominantemente construtivo. Tendência, atividade e condições "
            "macro permitem aporte integral no S&amp;P 500.",

        "YELLOW_EXPENSIVE_BULL":
            "O mercado segue em alta e com força, mas o valuation está historicamente elevado. "
            "A política mantém a posição existente, reduz a agressividade dos novos aportes "
            "e aumenta a formação de reserva.",

        "NEUTRAL_UNCERTAIN":
            "Os sinais estão mistos. O Atlas divide o novo aporte entre mercado e reserva "
            "até que o regime ganhe maior clareza.",

        "ORANGE_DETERIORATION":
            "Há deterioração relevante nos sinais de mercado e/ou macroeconômicos. "
            "A prioridade passa a ser preservar capital novo por meio de maior reserva.",

        "RED_STRUCTURAL_STRESS":
            "O sistema identifica stress estrutural. A posição existente é mantida, "
            "novos aportes no S&amp;P são reduzidos e tranches da reserva ficam pendentes "
            "até a saída do regime RED.",

        "BLUE_REASSESS_ACCUMULATION":
            "Após stress relevante, o mercado entra em fase de reavaliação/acumulação. "
            "O Atlas volta a priorizar compras e pode liberar tranches pendentes "
            "quando os gatilhos de drawdown estiverem satisfeitos.",
    }
    return mapping.get(
        str(regime),
        "O regime atual não possui interpretação executiva cadastrada."
    )


def _indicator_interpretation(label, status):
    status = str(status)

    mapping = {
        ("TREND", "BULL"): (
            "FAVORÁVEL",
            "A tendência principal permanece positiva."
        ),
        ("TREND", "BEAR"): (
            "RISCO",
            "A tendência principal está deteriorada."
        ),

        ("VALUATION", "EXTREME_TOP_1"): (
            "RISCO ELEVADO",
            "O valuation está no extremo histórico superior."
        ),
        ("VALUATION", "EXTREME_TOP_5"): (
            "RISCO ELEVADO",
            "O valuation está entre os níveis historicamente mais altos."
        ),
        ("VALUATION", "VERY_HIGH"): (
            "ATENÇÃO",
            "O valuation está elevado e reduz a margem de segurança."
        ),

        ("MOMENTUM", "STRONG_POSITIVE"): (
            "FAVORÁVEL",
            "O momentum confirma força de preço no horizonte de 12 meses."
        ),
        ("MOMENTUM", "POSITIVE"): (
            "FAVORÁVEL",
            "O momentum permanece positivo."
        ),
        ("MOMENTUM", "NEGATIVE"): (
            "ATENÇÃO",
            "O momentum perdeu força."
        ),

        ("LABOR", "STABLE"): (
            "FAVORÁVEL",
            "O mercado de trabalho permanece estável."
        ),
        ("LABOR", "DETERIORATING"): (
            "ATENÇÃO",
            "O mercado de trabalho apresenta deterioração."
        ),
        ("LABOR", "DETERIORATION_SEVERE"): (
            "RISCO",
            "O mercado de trabalho apresenta deterioração severa."
        ),

        ("INDUSTRIAL", "EXPANSION"): (
            "FAVORÁVEL",
            "A produção industrial está em expansão."
        ),
        ("INDUSTRIAL", "CONTRACTION"): (
            "ATENÇÃO",
            "A produção industrial está em contração."
        ),
        ("INDUSTRIAL", "CONTRACTION_STRONG"): (
            "RISCO",
            "A produção industrial apresenta contração forte."
        ),

        ("INFLATION", "REACCELERATING"): (
            "ATENÇÃO",
            "A inflação voltou a acelerar e pode limitar a flexibilização monetária."
        ),
        ("INFLATION", "HIGH"): (
            "RISCO",
            "A inflação permanece elevada."
        ),
        ("INFLATION", "FALLING"): (
            "FAVORÁVEL",
            "A inflação está desacelerando."
        ),

        ("MONETARY", "EASING"): (
            "FAVORÁVEL",
            "A política monetária está em flexibilização."
        ),
        ("MONETARY", "TIGHTENING"): (
            "RISCO",
            "A política monetária está em aperto."
        ),

        ("YIELD_CURVE", "INVERTED"): (
            "RISCO",
            "A curva de juros está invertida."
        ),
        ("YIELD_CURVE", "FLAT_POSITIVE"): (
            "NEUTRO",
            "A curva está positiva, porém pouco inclinada."
        ),
        ("YIELD_CURVE", "NORMAL_POSITIVE"): (
            "FAVORÁVEL",
            "A curva apresenta inclinação positiva normal."
        ),
    }

    return mapping.get(
        (label, status),
        ("NEUTRO", f"Estado atual: {_display_value(status)}.")
    )


def _reading_color(reading):
    mapping = {
        "FAVORÁVEL": GREEN,
        "NEUTRO": GRAY,
        "ATENÇÃO": AMBER,
        "RISCO": RED,
        "RISCO ELEVADO": RED,
    }
    return mapping.get(reading, GRAY)


# ============================================================
# CARREGAR ESTADO
# ============================================================

def load_current_state() -> dict:

    if not CURRENT_STATE_FILE.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {CURRENT_STATE_FILE}"
        )

    df = pd.read_csv(
        CURRENT_STATE_FILE
    )

    if df.empty:
        raise RuntimeError(
            "current_state.csv está vazio."
        )

    row = df.iloc[-1].to_dict()

    # Garantir uma data-base utilizável no PDF.
    if "date" in df.columns:

        parsed_date = pd.to_datetime(
            df.iloc[-1]["date"],
            errors="coerce",
        )

        if not pd.isna(parsed_date):
            row["date"] = pd.Timestamp(
                parsed_date
            )

    return row


# ============================================================
# ESTILOS
# ============================================================

def build_styles():

    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="AtlasTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=WHITE,
            alignment=TA_LEFT,
            spaceAfter=4,
        )
    )

    styles.add(
        ParagraphStyle(
            name="AtlasSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#CBD5E1"),
        )
    )

    styles.add(
        ParagraphStyle(
            name="Section",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=NAVY,
            spaceBefore=8,
            spaceAfter=8,
        )
    )

    styles.add(
        ParagraphStyle(
            name="BodyAtlas",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=14,
            textColor=BLACK,
            spaceAfter=6,
        )
    )

    styles.add(
        ParagraphStyle(
            name="Small",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=SLATE,
        )
    )

    styles.add(
        ParagraphStyle(
            name="CardLabel",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=10,
            textColor=SLATE,
            alignment=TA_CENTER,
        )
    )

    styles.add(
        ParagraphStyle(
            name="CardValue",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=19,
            textColor=NAVY,
            alignment=TA_CENTER,
        )
    )

    styles.add(
        ParagraphStyle(
            name="Decision",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=16,
            textColor=BLACK,
        )
    )

    return styles


# ============================================================
# CABEÇALHO / RODAPÉ
# ============================================================

def _page_header_footer(canvas, doc):

    canvas.saveState()

    width, height = A4

    canvas.setStrokeColor(BORDER)
    canvas.line(
        18 * mm,
        15 * mm,
        width - 18 * mm,
        15 * mm,
    )

    canvas.setFont(
        "Helvetica",
        7.5
    )
    canvas.setFillColor(SLATE)

    canvas.drawString(
        18 * mm,
        9 * mm,
        "SP500 Cycle Atlas - Relatório Institucional"
    )

    canvas.drawRightString(
        width - 18 * mm,
        9 * mm,
        f"Página {doc.page}"
    )

    canvas.restoreState()


# ============================================================
# COMPONENTES
# ============================================================

def _section_title(text, styles):
    return Paragraph(
        _escape(text),
        styles["Section"]
    )


def _metric_cards(state, styles):

    data = [[
        Paragraph("S&amp;P 500", styles["CardLabel"]),
        Paragraph("DRAWDOWN", styles["CardLabel"]),
        Paragraph("CAPE", styles["CardLabel"]),
        Paragraph("CAPE PERCENTIL", styles["CardLabel"]),
    ], [
        Paragraph(
            _fmt_number(state.get("sp500")),
            styles["CardValue"]
        ),
        Paragraph(
            _fmt_pct(state.get("drawdown")),
            styles["CardValue"]
        ),
        Paragraph(
            _fmt_number(state.get("cape")),
            styles["CardValue"]
        ),
        Paragraph(
            _fmt_pct(state.get("cape_percentile"), 2),
            styles["CardValue"]
        ),
    ]]

    table = Table(
        data,
        colWidths=[43 * mm] * 4,
        rowHeights=[9 * mm, 15 * mm],
    )

    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), WHITE),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ])
    )

    return table


def _allocation_cards(state, styles):

    position = _display_value(
        state.get("existing_position", "N/A")
    )

    equity = _safe_float(
        state.get("new_contribution_equity")
    )

    reserve = _safe_float(
        state.get("new_contribution_reserve")
    )

    equity_text = (
        f"{equity * 100:.0f}%"
        if equity is not None
        else "N/A"
    )

    reserve_text = (
        f"{reserve * 100:.0f}%"
        if reserve is not None
        else "N/A"
    )

    data = [[
        Paragraph("POSIÇÃO EXISTENTE", styles["CardLabel"]),
        Paragraph("NOVO APORTE S&amp;P", styles["CardLabel"]),
        Paragraph("NOVA RESERVA", styles["CardLabel"]),
    ], [
        Paragraph(position, styles["CardValue"]),
        Paragraph(equity_text, styles["CardValue"]),
        Paragraph(reserve_text, styles["CardValue"]),
    ]]

    table = Table(
        data,
        colWidths=[57.3 * mm] * 3,
        rowHeights=[9 * mm, 16 * mm],
    )

    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), WHITE),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ])
    )

    return table


def _indicator_table(state, styles):

    items = [
        (
            "TREND",
            "Tendência",
            str(state.get("market_regime", "N/A")).replace(" MARKET", "")
        ),
        (
            "VALUATION",
            "Valuation",
            state.get("valuation_regime", "N/A")
        ),
        (
            "MOMENTUM",
            "Momentum",
            state.get("momentum_regime", "N/A")
        ),
        (
            "LABOR",
            "Mercado de trabalho",
            state.get("labor_regime", "N/A")
        ),
        (
            "INDUSTRIAL",
            "Produção industrial",
            state.get("industrial_regime", "N/A")
        ),
        (
            "INFLATION",
            "Inflação",
            state.get("inflation_regime", "N/A")
        ),
        (
            "MONETARY",
            "Política monetária",
            state.get("monetary_regime", "N/A")
        ),
        (
            "YIELD_CURVE",
            "Curva de juros",
            state.get("curve_regime", "N/A")
        ),
    ]

    data = [[
        Paragraph("<b>Indicador</b>", styles["Small"]),
        Paragraph("<b>Estado</b>", styles["Small"]),
        Paragraph("<b>Leitura</b>", styles["Small"]),
        Paragraph("<b>Interpretação</b>", styles["Small"]),
    ]]

    row_colors = []

    for label, name, status in items:

        reading, explanation = _indicator_interpretation(
            label,
            status,
        )

        data.append([
            Paragraph(
                f"<b>{_escape(name)}</b>",
                styles["Small"]
            ),
            Paragraph(
                _escape(_display_value(status)),
                styles["Small"]
            ),
            Paragraph(
                f"<font color='{_reading_color(reading).hexval()}'>"
                f"<b>{_escape(reading)}</b></font>",
                styles["Small"]
            ),
            Paragraph(
                _escape(explanation),
                styles["Small"]
            ),
        ])

    table = Table(
        data,
        colWidths=[
            36 * mm,
            43 * mm,
            29 * mm,
            64 * mm,
        ],
        repeatRows=1,
    )

    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.35, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])
    )

    return table


def _macro_table(state, styles):

    data = [
        ["Fed Funds", _fmt_pct_already_percent(state.get("fed_funds"))],
        ["Fed Δ12m", _fmt_pp(state.get("fed_change_12m"))],
        ["Curva 10Y-2Y", _fmt_pp(state.get("yield_curve_10y_2y"))],
        ["Inflação YoY", _fmt_pct_already_percent(state.get("inflation_yoy"))],
        ["Inflação Δ6m", _fmt_pp(state.get("inflation_change_6m"))],
        ["Desemprego", _fmt_pct_already_percent(state.get("unemployment"))],
        ["Sahm", _fmt_number(state.get("sahm_indicator"))],
        ["Produção Industrial YoY", _fmt_pct_already_percent(state.get("industrial_production_yoy"))],
    ]

    wrapped = [
        [
            Paragraph(f"<b>{_escape(label)}</b>", styles["Small"]),
            Paragraph(_escape(value), styles["Small"]),
        ]
        for label, value in data
    ]

    table = Table(
        wrapped,
        colWidths=[78 * mm, 45 * mm],
    )

    table.setStyle(
        TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.35, BORDER),
            ("BACKGROUND", (0, 0), (0, -1), LIGHT),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])
    )

    return table


def _reserve_table(styles):

    data = [
        [
            Paragraph("<b>Drawdown</b>", styles["Small"]),
            Paragraph("<b>Parcela da reserva</b>", styles["Small"]),
            Paragraph("<b>Regra</b>", styles["Small"]),
        ],
        ["-15%", "40%", "Primeiro estágio"],
        ["-20%", "+30%", "Segundo estágio"],
        ["-30%", "+20%", "Terceiro estágio"],
        ["-35%", "+10%", "Quarto estágio"],
    ]

    table = Table(
        data,
        colWidths=[
            35 * mm,
            50 * mm,
            70 * mm,
        ],
        repeatRows=1,
    )

    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.35, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 1), (1, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])
    )

    return table


def _decision_text(state):

    equity = _safe_float(
        state.get("new_contribution_equity")
    )

    reserve = _safe_float(
        state.get("new_contribution_reserve")
    )

    equity_text = (
        f"{equity * 100:.0f}%"
        if equity is not None
        else "N/A"
    )

    reserve_text = (
        f"{reserve * 100:.0f}%"
        if reserve is not None
        else "N/A"
    )

    reserve_stage = int(
        _safe_float(
            state.get("reserve_stage"),
            0
        )
    )

    reserve_status = str(
        state.get(
            "reserve_deployment_status",
            "NOT_ACTIVE"
        )
    )

    if reserve_stage <= 0:
        reserve_action = (
            "Não utilizar a reserva acumulada agora; continuar formando reserva conforme o regime."
        )
    elif reserve_status == "PENDING_REGIME_CONFIRMATION":
        reserve_action = (
            "O drawdown ativou tranche(s), mas a execução está bloqueada pelo regime RED. "
            "Manter as parcelas pendentes."
        )
    elif reserve_status == "DEPLOYMENT_ALLOWED":
        reserve_action = (
            "O drawdown ativou tranche(s) e o regime permite utilização conforme a política 40/30/20/10."
        )
    else:
        reserve_action = (
            "Aguardar confirmação operacional para utilização da reserva."
        )

    return (
        f"Manter a posição existente. Direcionar {equity_text} do novo aporte ao S&P 500 "
        f"e {reserve_text} à reserva. {reserve_action}"
    )


# ============================================================
# PDF
# ============================================================

def generate_pdf_report(
    output_path: str | Path = PDF_FILE,
) -> Path:

    state = load_current_state()

    REPORTS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path = Path(
        output_path
    )

    styles = build_styles()

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=20 * mm,
        title=REPORT_TITLE,
        author="SP500 Cycle Atlas",
        subject="Relatório de ciclo de mercado e política de reserva",
    )

    story = []

    # --------------------------------------------------------
    # CAPA / CABEÇALHO
    # --------------------------------------------------------

    header = Table(
        [[
            Paragraph(
                PROJECT_TITLE,
                styles["AtlasTitle"]
            ),
            Paragraph(
                "INSTITUTIONAL<br/>CYCLE REPORT",
                ParagraphStyle(
                    "HeaderRight",
                    parent=styles["Small"],
                    textColor=colors.HexColor("#CBD5E1"),
                    alignment=TA_CENTER,
                    fontName="Helvetica-Bold",
                    fontSize=8.5,
                    leading=12,
                )
            ),
        ]],
        colWidths=[125 * mm, 47 * mm],
    )

    header.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), NAVY),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ])
    )

    story.append(header)
    story.append(Spacer(1, 6 * mm))

    operational = state.get(
        "operational_regime",
        "N/A"
    )

    regime_box = Table(
        [[
            Paragraph(
                "<b>REGIME ATUAL</b>",
                styles["Small"]
            ),
        ], [
            Paragraph(
                f"<b>{_escape(_display_value(operational))}</b>",
                ParagraphStyle(
                    "RegimeBig",
                    parent=styles["BodyAtlas"],
                    fontName="Helvetica-Bold",
                    fontSize=16,
                    leading=20,
                    textColor=NAVY,
                )
            ),
        ], [
            Paragraph(
                "Código técnico: "
                f"{_escape(operational)}",
                styles["Small"]
            ),
        ]],
        colWidths=[172 * mm],
    )

    regime_box.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), WHITE),
            ("BOX", (0, 0), (-1, -1), 0.7, BORDER),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ])
    )

    story.append(regime_box)
    story.append(Spacer(1, 3 * mm))

    story.append(
        Paragraph(
            "<b>Interpretação:</b> "
            + _escape(
                _regime_interpretation(
                    operational
                )
            ),
            styles["BodyAtlas"]
        )
    )

    story.append(Spacer(1, 3 * mm))
    story.append(_metric_cards(state, styles))
    story.append(Spacer(1, 5 * mm))

    # --------------------------------------------------------
    # AÇÃO
    # --------------------------------------------------------

    decision_box = Table(
        [[
            Paragraph(
                "<b>AÇÃO DO ATLAS HOJE</b>",
                styles["Small"]
            ),
        ], [
            Paragraph(
                f"<b>{_escape(_display_value(state.get('existing_position', 'N/A')))}</b>",
                ParagraphStyle(
                    "DecisionTitle",
                    parent=styles["BodyAtlas"],
                    fontName="Helvetica-Bold",
                    fontSize=15,
                    leading=18,
                    textColor=NAVY,
                )
            ),
        ], [
            Paragraph(
                _escape(
                    _decision_text(state)
                ),
                styles["Decision"]
            ),
        ]],
        colWidths=[172 * mm],
    )

    decision_box.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFBEB")),
            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#FDE68A")),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ])
    )

    story.append(decision_box)
    story.append(Spacer(1, 4 * mm))
    story.append(_allocation_cards(state, styles))
    story.append(Spacer(1, 6 * mm))

    # --------------------------------------------------------
    # INDICADORES
    # --------------------------------------------------------

    story.append(
        _section_title(
            "Por que estamos neste ponto?",
            styles
        )
    )

    story.append(
        _indicator_table(
            state,
            styles
        )
    )

    story.append(Spacer(1, 5 * mm))

    # --------------------------------------------------------
    # VALUATION
    # --------------------------------------------------------

    story.append(
        _section_title(
            "Valuation",
            styles
        )
    )

    valuation_text = (
        f"CAPE atual: <b>{_escape(_fmt_number(state.get('cape')))}</b>. "
        f"Percentil histórico: <b>{_escape(_fmt_pct(state.get('cape_percentile'), 2))}</b>. "
        f"Classificação: <b>{_escape(_display_value(state.get('valuation_regime', 'N/A')))}</b>. "
        "Valuation extremo aumenta o risco estrutural e reduz a margem de segurança, "
        "mas não constitui, isoladamente, sinal automático de venda."
    )

    story.append(
        Paragraph(
            valuation_text,
            styles["BodyAtlas"]
        )
    )

    # --------------------------------------------------------
    # MACRO
    # --------------------------------------------------------

    story.append(
        _section_title(
            "Macro & Monetário",
            styles
        )
    )

    story.append(
        _macro_table(
            state,
            styles
        )
    )

    story.append(Spacer(1, 5 * mm))

    # --------------------------------------------------------
    # RESERVA
    # --------------------------------------------------------

    story.append(
        _section_title(
            "Painel da Reserva",
            styles
        )
    )

    reserve_stage = int(
        _safe_float(
            state.get("reserve_stage"),
            0
        )
    )

    reserve_status = state.get(
        "reserve_deployment_status",
        "NOT_ACTIVE"
    )

    cumulative = _safe_float(
        state.get(
            "reserve_cumulative_fraction"
        ),
        0.0
    )

    reserve_now = (
        f"{cumulative * 100:.0f}%"
        if reserve_stage > 0
        else "0%"
    )

    reserve_summary = Table(
        [[
            Paragraph(
                "<b>Estágio atual</b>",
                styles["Small"]
            ),
            Paragraph(
                "<b>Status da reserva</b>",
                styles["Small"]
            ),
            Paragraph(
                "<b>Reserva liberada agora</b>",
                styles["Small"]
            ),
        ], [
            Paragraph(
                str(reserve_stage),
                styles["CardValue"]
            ),
            Paragraph(
                _escape(
                    _display_value(
                        reserve_status
                    )
                ),
                styles["BodyAtlas"]
            ),
            Paragraph(
                reserve_now,
                styles["CardValue"]
            ),
        ]],
        colWidths=[
            35 * mm,
            93 * mm,
            44 * mm,
        ],
    )

    reserve_summary.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), WHITE),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.35, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (2, 0), (2, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
    )

    story.append(reserve_summary)
    story.append(Spacer(1, 4 * mm))
    story.append(_reserve_table(styles))
    story.append(Spacer(1, 3 * mm))

    story.append(
        Paragraph(
            "<b>Regra de confirmação:</b> "
            "se o Atlas estiver em RED_STRUCTURAL_STRESS, a parcela fica aguardando confirmação. "
            "Ao sair de RED, as tranches pendentes podem ser liberadas.",
            styles["BodyAtlas"]
        )
    )

    story.append(
        Paragraph(
            "<b>Princípio operacional:</b> "
            "o drawdown define o tamanho potencial da tranche; "
            "o regime define se ela pode ser executada.",
            styles["BodyAtlas"]
        )
    )

    # --------------------------------------------------------
    # DIAGNÓSTICO ESTRUTURAL
    # --------------------------------------------------------

    story.append(
        _section_title(
            "Diagnóstico Estrutural",
            styles
        )
    )

    structural_data = [
        [
            Paragraph("<b>Fase do ciclo</b>", styles["Small"]),
            Paragraph(
                _escape(
                    _display_value(
                        state.get(
                            "cycle_phase",
                            "N/A"
                        )
                    )
                ),
                styles["Small"]
            ),
        ],
        [
            Paragraph("<b>Risco estrutural</b>", styles["Small"]),
            Paragraph(
                _escape(
                    _display_value(
                        state.get(
                            "structural_risk",
                            "N/A"
                        )
                    )
                ),
                styles["Small"]
            ),
        ],
        [
            Paragraph("<b>Timing de topo</b>", styles["Small"]),
            Paragraph(
                _escape(
                    _display_value(
                        state.get(
                            "top_timing",
                            "N/A"
                        )
                    )
                ),
                styles["Small"]
            ),
        ],
        [
            Paragraph("<b>Regime de mercado</b>", styles["Small"]),
            Paragraph(
                _escape(
                    _display_value(
                        state.get(
                            "market_regime",
                            "N/A"
                        )
                    )
                ),
                styles["Small"]
            ),
        ],
    ]

    structural_table = Table(
        structural_data,
        colWidths=[
            55 * mm,
            100 * mm,
        ],
    )

    structural_table.setStyle(
        TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.35, BORDER),
            ("BACKGROUND", (0, 0), (0, -1), LIGHT),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])
    )

    story.append(structural_table)
    story.append(Spacer(1, 6 * mm))

    # --------------------------------------------------------
    # METODOLOGIA / AVISO
    # --------------------------------------------------------

    story.append(
        _section_title(
            "Metodologia Operacional",
            styles
        )
    )

    story.append(
        Paragraph(
            "O SP500 Cycle Atlas classifica o regime de mercado combinando tendência, valuation, "
            "momentum, mercado de trabalho, produção industrial, inflação, política monetária "
            "e curva de juros. A política operacional utiliza o regime para disciplinar novos "
            "aportes e a formação de reserva, e utiliza drawdowns do S&amp;P 500 para dimensionar "
            "as tranches potenciais de utilização dessa reserva.",
            styles["BodyAtlas"]
        )
    )

    story.append(
        Paragraph(
            "<b>Importante:</b> o Atlas não prevê preço, topo ou crash. "
            "Valuation extremo não é sinal automático de venda. "
            "O objetivo é aplicar uma política disciplinada e repetível.",
            styles["BodyAtlas"]
        )
    )

    story.append(
        Spacer(
            1,
            3 * mm
        )
    )

    report_generated_at = (
        datetime.now()
        .strftime("%d/%m/%Y %H:%M:%S")
    )

    state_date_text = (
        _date_text(
            state.get("date")
        )
    )

    story.append(
        Paragraph(
            f"Relatório gerado em {report_generated_at}.",
            styles["Small"]
        )
    )

    story.append(
        Paragraph(
            f"<b>Data-base do estado:</b> "
            f"{_escape(state_date_text)}.",
            styles["Small"]
        )
    )

    # --------------------------------------------------------
    # BUILD
    # --------------------------------------------------------

    doc.build(
        story,
        onFirstPage=_page_header_footer,
        onLaterPages=_page_header_footer,
    )

    if (
        not output_path.exists()
        or output_path.stat().st_size < 1000
    ):
        raise RuntimeError(
            "PDF não foi gerado corretamente."
        )

    print("=" * 72)
    print("SP500 CYCLE ATLAS — PDF REPORT")
    print("=" * 72)
    print(f"Arquivo: {output_path}")
    print(
        f"Tamanho: "
        f"{output_path.stat().st_size / 1024:.1f} KB"
    )
    print("✅ PDF gerado com sucesso.")

    return output_path


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":

    generate_pdf_report()
