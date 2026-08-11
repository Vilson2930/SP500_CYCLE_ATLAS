# ============================================================
# SP500 CYCLE ATLAS
# report.py
# ============================================================
#
# Responsável por:
#
# - gerar relatório executivo
# - salvar current_state.csv
# - atualizar cycle_history.csv
# - evitar duplicidade de data
# - mostrar mudanças de regime
#
# IMPORTANTE:
# Este módulo NÃO calcula o ciclo.
# Ele apenas apresenta e persiste o resultado do engine.
# ============================================================

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

from settings import (
    DATA_DIR,
    CURRENT_STATE_FILE,
    CYCLE_HISTORY_FILE,
    HISTORY_COLUMNS,
    REPORT_SEPARATOR,
)


# ============================================================
# UTILITÁRIOS
# ============================================================

def _valid(value):
    return (
        value is not None
        and not pd.isna(value)
    )


def _fmt_pct(value, decimals=2):

    if not _valid(value):
        return "N/A"

    return f"{float(value) * 100:.{decimals}f}%"


def _fmt_number(value, decimals=2):

    if not _valid(value):
        return "N/A"

    return f"{float(value):,.{decimals}f}"


def _fmt_pp(value, decimals=2):

    if not _valid(value):
        return "N/A"

    return f"{float(value):+.{decimals}f} p.p."


def _fmt_date(value):

    if not _valid(value):
        return "N/A"

    try:
        return pd.Timestamp(value).strftime(
            "%Y-%m-%d"
        )

    except Exception:
        return str(value)

# ============================================================
# INTERPRETAÇÃO EXECUTIVA / PAINEL
# ============================================================

def _regime_interpretation(regime):

    mapping = {
        "GREEN_EXPANSION":
            "Mercado em expansão, com ambiente predominantemente construtivo. "
            "O Atlas permite aporte integral no S&P 500.",

        "YELLOW_EXPENSIVE_BULL":
            "O mercado permanece em tendência de alta e com força, porém o valuation "
            "está historicamente elevado. A estratégia mantém a posição existente, "
            "reduz a agressividade dos novos aportes e aumenta a reserva.",

        "NEUTRAL_UNCERTAIN":
            "Os sinais estão mistos e ainda não há confirmação suficiente para uma postura "
            "mais agressiva. O Atlas divide o novo aporte entre S&P 500 e reserva.",

        "ORANGE_DETERIORATION":
            "Há deterioração relevante no ambiente de mercado e/ou macroeconômico. "
            "O Atlas preserva a posição existente, mas direciona a maior parte do novo aporte "
            "para a reserva.",

        "RED_STRUCTURAL_STRESS":
            "O mercado está em stress estrutural. O Atlas mantém a posição existente, "
            "reduz fortemente os novos aportes no S&P 500 e bloqueia temporariamente "
            "tranches da reserva, que ficam pendentes até a saída do regime RED.",

        "BLUE_REASSESS_ACCUMULATION":
            "O mercado passou por stress relevante e entrou em fase de reavaliação/acumulação. "
            "O Atlas volta a priorizar aportes no S&P 500 e pode liberar tranches pendentes "
            "quando as regras de drawdown forem atendidas.",
    }

    return mapping.get(
        regime,
        "O regime atual não possui interpretação executiva cadastrada."
    )


def _indicator_interpretation(label, status):

    status = str(status)

    mapping = {
        ("TREND", "BULL"):
            ("FAVORÁVEL", "A tendência principal do mercado permanece positiva."),

        ("TREND", "BEAR"):
            ("RISCO", "A tendência principal do mercado está deteriorada."),

        ("VALUATION", "EXTREME_TOP_1"):
            ("RISCO ELEVADO", "O valuation está no extremo histórico superior, aumentando o risco estrutural."),

        ("VALUATION", "EXTREME_TOP_5"):
            ("RISCO ELEVADO", "O valuation está entre os níveis historicamente mais altos."),

        ("VALUATION", "VERY_HIGH"):
            ("ATENÇÃO", "O valuation está elevado e reduz a margem de segurança para novos aportes."),

        ("MOMENTUM", "STRONG_POSITIVE"):
            ("FAVORÁVEL", "O momentum confirma força de preço no horizonte de 12 meses."),

        ("MOMENTUM", "POSITIVE"):
            ("FAVORÁVEL", "O momentum permanece positivo."),

        ("MOMENTUM", "NEGATIVE"):
            ("ATENÇÃO", "O momentum perdeu força e exige maior cautela."),

        ("LABOR", "STABLE"):
            ("FAVORÁVEL", "O mercado de trabalho permanece estável."),

        ("LABOR", "DETERIORATING"):
            ("ATENÇÃO", "O mercado de trabalho apresenta deterioração."),

        ("LABOR", "DETERIORATION_SEVERE"):
            ("RISCO", "O mercado de trabalho apresenta deterioração severa."),

        ("INDUSTRIAL", "EXPANSION"):
            ("FAVORÁVEL", "A produção industrial está em expansão."),

        ("INDUSTRIAL", "CONTRACTION"):
            ("ATENÇÃO", "A produção industrial está em contração."),

        ("INDUSTRIAL", "CONTRACTION_STRONG"):
            ("RISCO", "A produção industrial apresenta contração forte."),

        ("INFLATION", "REACCELERATING"):
            ("ATENÇÃO", "A inflação voltou a acelerar e pode limitar a flexibilização monetária."),

        ("INFLATION", "HIGH"):
            ("RISCO", "A inflação permanece elevada."),

        ("INFLATION", "FALLING"):
            ("FAVORÁVEL", "A inflação está desacelerando."),

        ("MONETARY", "EASING"):
            ("FAVORÁVEL", "A política monetária está em flexibilização."),

        ("MONETARY", "TIGHTENING"):
            ("RISCO", "A política monetária está em aperto."),

        ("YIELD_CURVE", "INVERTED"):
            ("RISCO", "A curva de juros está invertida, sinal historicamente associado a maior risco macro."),

        ("YIELD_CURVE", "FLAT_POSITIVE"):
            ("NEUTRO", "A curva está positiva, porém ainda pouco inclinada."),

        ("YIELD_CURVE", "NORMAL_POSITIVE"):
            ("FAVORÁVEL", "A curva de juros apresenta inclinação positiva normal."),
    }

    return mapping.get(
        (label, status),
        ("NEUTRO", f"Estado atual: {status}.")
    )


def _current_action_text(
    operational,
    equity,
    reserve,
    reserve_stage,
    reserve_status,
):

    eq_pct = (
        f"{float(equity) * 100:.0f}%"
        if _valid(equity)
        else "N/A"
    )

    reserve_pct = (
        f"{float(reserve) * 100:.0f}%"
        if _valid(reserve)
        else "N/A"
    )

    try:
        stage = int(reserve_stage)
    except Exception:
        stage = 0

    if stage <= 0:
        reserve_action = (
            "Não utilizar a reserva acumulada agora; "
            "continuar formando reserva conforme o regime."
        )

    elif reserve_status == "PENDING_REGIME_CONFIRMATION":
        reserve_action = (
            "O drawdown ativou tranche(s), mas a execução está bloqueada pelo regime RED. "
            "Manter as tranches pendentes."
        )

    elif reserve_status == "DEPLOYMENT_ALLOWED":
        reserve_action = (
            "O drawdown ativou tranche(s) e o regime permite o deployment "
            "conforme a política 40/30/20/10."
        )

    else:
        reserve_action = (
            "Aguardar confirmação operacional para utilização da reserva."
        )

    return (
        f"Manter a posição existente. "
        f"Direcionar {eq_pct} do novo aporte ao S&P 500 e {reserve_pct} à reserva. "
        f"{reserve_action}"
    )


def _status_color(reading):

    palette = {
        "FAVORÁVEL": "#15803d",
        "NEUTRO": "#64748b",
        "ATENÇÃO": "#d97706",
        "RISCO": "#dc2626",
        "RISCO ELEVADO": "#b91c1c",
    }

    return palette.get(
        reading,
        "#64748b"
    )


def _build_indicator_rows_html(current_state):

    import html

    items = [
        ("TREND", str(current_state.get("market_regime", "N/A")).replace(" MARKET", "")),
        ("VALUATION", current_state.get("valuation_regime", "N/A")),
        ("MOMENTUM", current_state.get("momentum_regime", "N/A")),
        ("LABOR", current_state.get("labor_regime", "N/A")),
        ("INDUSTRIAL", current_state.get("industrial_regime", "N/A")),
        ("INFLATION", current_state.get("inflation_regime", "N/A")),
        ("MONETARY", current_state.get("monetary_regime", "N/A")),
        ("YIELD_CURVE", current_state.get("curve_regime", "N/A")),
    ]

    label_names = {
        "TREND": "Tendência",
        "VALUATION": "Valuation",
        "MOMENTUM": "Momentum",
        "LABOR": "Mercado de trabalho",
        "INDUSTRIAL": "Produção industrial",
        "INFLATION": "Inflação",
        "MONETARY": "Política monetária",
        "YIELD_CURVE": "Curva de juros",
    }

    rows = []

    for label, status in items:

        reading, explanation = _indicator_interpretation(
            label,
            status,
        )

        color = _status_color(
            reading
        )

        rows.append(
            f"""
            <tr>
                <td style="padding:10px;border-bottom:1px solid #e5e7eb;"><strong>{html.escape(label_names[label])}</strong></td>
                <td style="padding:10px;border-bottom:1px solid #e5e7eb;">{html.escape(str(status))}</td>
                <td style="padding:10px;border-bottom:1px solid #e5e7eb;"><span style="font-weight:700;color:{color};">{html.escape(reading)}</span></td>
                <td style="padding:10px;border-bottom:1px solid #e5e7eb;">{html.escape(explanation)}</td>
            </tr>
            """
        )

    return "\n".join(rows)


def build_email_html_report(
    current_state: dict,
    scorecard: pd.DataFrame | None = None,
    regime_change: dict | None = None,
):

    import html

    date = _fmt_date(current_state.get("date"))
    sp500 = _fmt_number(current_state.get("sp500"))
    drawdown = _fmt_pct(current_state.get("drawdown"))
    cape = _fmt_number(current_state.get("cape"))
    cape_percentile = _fmt_pct(current_state.get("cape_percentile"), 2)

    operational = current_state.get("operational_regime", "N/A")
    cycle_phase = current_state.get("cycle_phase", "N/A")
    structural_risk = current_state.get("structural_risk", "N/A")
    top_timing = current_state.get("top_timing", "N/A")
    position = current_state.get("existing_position", "N/A")

    equity = current_state.get("new_contribution_equity")
    reserve = current_state.get("new_contribution_reserve")
    reserve_stage = current_state.get("reserve_stage", 0)
    reserve_status = current_state.get("reserve_deployment_status", "NOT_ACTIVE")

    eq_pct = f"{float(equity) * 100:.0f}%" if _valid(equity) else "N/A"
    reserve_pct = f"{float(reserve) * 100:.0f}%" if _valid(reserve) else "N/A"

    interpretation = _regime_interpretation(operational)

    action_text = _current_action_text(
        operational,
        equity,
        reserve,
        reserve_stage,
        reserve_status,
    )

    indicator_rows = _build_indicator_rows_html(current_state)

    try:
        stage_int = int(reserve_stage)
    except Exception:
        stage_int = 0

    reserve_now = (
        _fmt_pct(current_state.get("reserve_cumulative_fraction", 0.0), 0)
        if stage_int > 0
        else "0%"
    )

    change_html = ""

    if regime_change and regime_change.get("changed"):
        change_html = f"""
        <div style="margin:16px 0;padding:14px;background:#fff7ed;border-left:5px solid #ea580c;">
            <strong>MUDANÇA DE REGIME:</strong>
            {html.escape(str(regime_change.get("previous")))}
            →
            {html.escape(str(regime_change.get("current")))}
        </div>
        """

    return f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:Arial,Helvetica,sans-serif;color:#0f172a;">
<div style="max-width:920px;margin:0 auto;padding:24px;">

    <div style="background:#0f172a;color:white;padding:26px;border-radius:14px 14px 0 0;">
        <div style="font-size:13px;letter-spacing:1.5px;opacity:.8;">SP500 CYCLE ATLAS</div>
        <div style="font-size:28px;font-weight:700;margin-top:5px;">PAINEL DE CONTROLE</div>
        <div style="font-size:14px;margin-top:8px;opacity:.8;">Data da análise: {date}</div>
    </div>

    <div style="background:white;padding:24px;border-radius:0 0 14px 14px;margin-bottom:18px;">
        <div style="font-size:13px;color:#64748b;font-weight:700;">REGIME ATUAL</div>
        <div style="font-size:27px;font-weight:800;margin-top:5px;">{html.escape(str(operational))}</div>
        <div style="font-size:16px;line-height:1.55;margin-top:12px;">
            <strong>Interpretação:</strong> {html.escape(interpretation)}
        </div>
    </div>

    {change_html}

    <table role="presentation" width="100%" cellspacing="10" cellpadding="0" style="margin-bottom:16px;">
        <tr>
            <td style="width:25%;background:white;padding:18px;border-radius:12px;text-align:center;">
                <div style="font-size:12px;color:#64748b;">S&P 500</div>
                <div style="font-size:25px;font-weight:800;">{sp500}</div>
            </td>
            <td style="width:25%;background:white;padding:18px;border-radius:12px;text-align:center;">
                <div style="font-size:12px;color:#64748b;">DRAWDOWN</div>
                <div style="font-size:25px;font-weight:800;">{drawdown}</div>
            </td>
            <td style="width:25%;background:white;padding:18px;border-radius:12px;text-align:center;">
                <div style="font-size:12px;color:#64748b;">CAPE</div>
                <div style="font-size:25px;font-weight:800;">{cape}</div>
            </td>
            <td style="width:25%;background:white;padding:18px;border-radius:12px;text-align:center;">
                <div style="font-size:12px;color:#64748b;">CAPE PERCENTIL</div>
                <div style="font-size:25px;font-weight:800;">{cape_percentile}</div>
            </td>
        </tr>
    </table>

    <div style="background:#fffbeb;border:1px solid #fde68a;padding:22px;border-radius:14px;margin-bottom:18px;">
        <div style="font-size:13px;color:#92400e;font-weight:800;">DECISÃO DO ATLAS HOJE</div>
        <div style="font-size:18px;font-weight:700;margin-top:10px;">{html.escape(action_text)}</div>
    </div>

    <table role="presentation" width="100%" cellspacing="10" cellpadding="0" style="margin-bottom:18px;">
        <tr>
            <td style="width:33%;background:white;padding:20px;border-radius:12px;text-align:center;">
                <div style="font-size:12px;color:#64748b;">POSIÇÃO EXISTENTE</div>
                <div style="font-size:22px;font-weight:800;">{html.escape(str(position))}</div>
            </td>
            <td style="width:33%;background:white;padding:20px;border-radius:12px;text-align:center;">
                <div style="font-size:12px;color:#64748b;">NOVO APORTE S&P</div>
                <div style="font-size:28px;font-weight:800;color:#15803d;">{eq_pct}</div>
            </td>
            <td style="width:33%;background:white;padding:20px;border-radius:12px;text-align:center;">
                <div style="font-size:12px;color:#64748b;">NOVA RESERVA</div>
                <div style="font-size:28px;font-weight:800;color:#d97706;">{reserve_pct}</div>
            </td>
        </tr>
    </table>

    <div style="background:white;padding:22px;border-radius:14px;margin-bottom:18px;">
        <div style="font-size:18px;font-weight:800;margin-bottom:12px;">POR QUE ESTAMOS NESTE PONTO?</div>
        <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;font-size:14px;">
            <tr style="background:#f8fafc;">
                <th align="left" style="padding:10px;">Indicador</th>
                <th align="left" style="padding:10px;">Estado</th>
                <th align="left" style="padding:10px;">Leitura</th>
                <th align="left" style="padding:10px;">Interpretação</th>
            </tr>
            {indicator_rows}
        </table>
    </div>

    <div style="background:white;padding:22px;border-radius:14px;margin-bottom:18px;">
        <div style="font-size:18px;font-weight:800;">PAINEL DA RESERVA</div>
        <div style="margin-top:12px;line-height:1.7;">
            <strong>Estágio atual:</strong> {html.escape(str(reserve_stage))}<br>
            <strong>Status:</strong> {html.escape(str(reserve_status))}<br>
            <strong>Reserva potencialmente utilizável agora:</strong> {reserve_now}
        </div>

        <table width="100%" cellpadding="10" cellspacing="0" style="border-collapse:collapse;margin-top:14px;font-size:14px;">
            <tr style="background:#f8fafc;">
                <th align="left">Drawdown</th>
                <th align="left">Parcela da reserva</th>
                <th align="left">Regra</th>
            </tr>
            <tr><td>-15%</td><td><strong>40%</strong></td><td>Primeiro estágio</td></tr>
            <tr><td>-20%</td><td><strong>+30%</strong></td><td>Segundo estágio</td></tr>
            <tr><td>-30%</td><td><strong>+20%</strong></td><td>Terceiro estágio</td></tr>
            <tr><td>-35%</td><td><strong>+10%</strong></td><td>Quarto estágio</td></tr>
        </table>

        <div style="margin-top:14px;padding:14px;background:#fef2f2;border-left:5px solid #dc2626;">
            <strong>Regra de confirmação:</strong>
            se o Atlas estiver em RED_STRUCTURAL_STRESS, a tranche fica PENDING.
            Ao sair de RED, as tranches pendentes podem ser liberadas.
        </div>
    </div>

    <div style="background:white;padding:22px;border-radius:14px;margin-bottom:18px;">
        <div style="font-size:18px;font-weight:800;">DIAGNÓSTICO ESTRUTURAL</div>
        <div style="margin-top:12px;line-height:1.8;">
            <strong>Fase do ciclo:</strong> {html.escape(str(cycle_phase))}<br>
            <strong>Risco estrutural:</strong> {html.escape(str(structural_risk))}<br>
            <strong>Timing de topo:</strong> {html.escape(str(top_timing))}
        </div>
    </div>

    <div style="padding:18px;color:#64748b;font-size:12px;line-height:1.6;text-align:center;">
        O SP500 Cycle Atlas classifica regime e disciplina aportes e utilização da reserva.
        Ele não prevê preço, topo ou crash. Valuation extremo isoladamente não é sinal automático de venda.
    </div>

</div>
</body>
</html>
"""


def save_html_report(
    report_html: str,
):

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    report_html_path = (
        DATA_DIR
        /
        "current_report.html"
    )

    with open(
        report_html_path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            report_html
        )

    return report_html_path


# ============================================================
# 1. PREPARAR CURRENT STATE
# ============================================================

def state_to_dataframe(
    current_state: dict,
) -> pd.DataFrame:

    row = {}

    for column in HISTORY_COLUMNS:

        row[column] = (
            current_state.get(
                column,
                np.nan
            )
        )

    # --------------------------------------------------------
    # Mapeamentos necessários
    # --------------------------------------------------------

    row["momentum_12m"] = (
        current_state.get(
            "return_12m",
            np.nan
        )
    )

    row["yield_curve"] = (
        current_state.get(
            "yield_curve_10y_2y",
            np.nan
        )
    )

    row["inflation"] = (
        current_state.get(
            "inflation_yoy",
            np.nan
        )
    )

    row[
        "industrial_production"
    ] = (
        current_state.get(
            "industrial_production_yoy",
            np.nan
        )
    )

    row["sahm"] = (
        current_state.get(
            "sahm_indicator",
            np.nan
        )
    )

    row["date"] = pd.to_datetime(
        current_state.get(
            "date"
        )
    )

    return pd.DataFrame(
        [row]
    )


# ============================================================
# 2. SALVAR ESTADO ATUAL
# ============================================================

def save_current_state(
    current_state: dict,
):

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    df = state_to_dataframe(
        current_state
    )

    df.to_csv(
        CURRENT_STATE_FILE,
        index=False
    )

    return df


# ============================================================
# 3. CARREGAR HISTÓRICO
# ============================================================

def load_cycle_history():

    if not Path(
        CYCLE_HISTORY_FILE
    ).exists():

        return pd.DataFrame(
            columns=HISTORY_COLUMNS
        )

    try:

        history = pd.read_csv(
            CYCLE_HISTORY_FILE
        )

    except Exception:

        return pd.DataFrame(
            columns=HISTORY_COLUMNS
        )

    if "date" in history.columns:

        history["date"] = (
            pd.to_datetime(
                history["date"],
                errors="coerce"
            )
        )

    return history


# ============================================================
# 4. ATUALIZAR HISTÓRICO
# ============================================================

def update_cycle_history(
    current_state: dict,
):

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    current_df = (
        state_to_dataframe(
            current_state
        )
    )

    history = (
        load_cycle_history()
    )

    # --------------------------------------------------------
    # Se vazio, cria
    # --------------------------------------------------------

    if history.empty:

        updated = current_df.copy()

    else:

        # ----------------------------------------------------
        # Garante colunas
        # ----------------------------------------------------

        for column in HISTORY_COLUMNS:

            if column not in history.columns:
                history[column] = np.nan

        history = history[
            HISTORY_COLUMNS
        ].copy()

        current_df = current_df[
            HISTORY_COLUMNS
        ].copy()

        # ----------------------------------------------------
        # Remove mesma data para atualizar em vez de duplicar
        # ----------------------------------------------------

        current_date = (
            current_df[
                "date"
            ].iloc[0]
        )

        history = history[
            history["date"]
            != current_date
        ]

        updated = pd.concat(
            [
                history,
                current_df
            ],
            ignore_index=True
        )

    updated = (
        updated
        .sort_values("date")
        .drop_duplicates(
            subset="date",
            keep="last"
        )
        .reset_index(drop=True)
    )

    updated.to_csv(
        CYCLE_HISTORY_FILE,
        index=False
    )

    return updated


# ============================================================
# 5. DETECTAR MUDANÇA DE REGIME
# ============================================================

def detect_regime_change(
    history: pd.DataFrame,
):

    if (
        history is None
        or len(history) < 2
    ):

        return {
            "changed": False,
            "previous": None,
            "current": None,
        }

    ordered = (
        history
        .sort_values("date")
        .reset_index(drop=True)
    )

    previous = (
        ordered.iloc[-2]
        .get(
            "operational_regime"
        )
    )

    current = (
        ordered.iloc[-1]
        .get(
            "operational_regime"
        )
    )

    return {

        "changed":
            previous != current,

        "previous":
            previous,

        "current":
            current,
    }


# ============================================================
# 6. CONSTRUIR RESUMO EXECUTIVO
# ============================================================

def build_executive_report(
    current_state: dict,
    scorecard: pd.DataFrame | None = None,
    regime_change: dict | None = None,
):

    date = _fmt_date(
        current_state.get("date")
    )

    sp500 = _fmt_number(
        current_state.get("sp500")
    )

    drawdown = _fmt_pct(
        current_state.get(
            "drawdown"
        )
    )

    momentum = _fmt_pct(
        current_state.get(
            "return_12m"
        )
    )

    cape = _fmt_number(
        current_state.get(
            "cape"
        )
    )

    cape_percentile = _fmt_pct(
        current_state.get(
            "cape_percentile"
        ),
        2
    )

    bull_age = (
        current_state.get(
            "bull_age_years"
        )
    )

    bull_return = _fmt_pct(
        current_state.get(
            "bull_return"
        )
    )

    fed = _fmt_number(
        current_state.get(
            "fed_funds"
        )
    )

    fed_change = _fmt_pp(
        current_state.get(
            "fed_change_12m"
        )
    )

    curve = _fmt_pp(
        current_state.get(
            "yield_curve_10y_2y"
        )
    )

    inflation = (
        current_state.get(
            "inflation_yoy"
        )
    )

    inflation_change = (
        current_state.get(
            "inflation_change_6m"
        )
    )

    unemployment = (
        current_state.get(
            "unemployment"
        )
    )

    sahm = (
        current_state.get(
            "sahm_indicator"
        )
    )

    industrial = (
        current_state.get(
            "industrial_production_yoy"
        )
    )

    market_regime = (
        current_state.get(
            "market_regime",
            "N/A"
        )
    )

    cycle_phase = (
        current_state.get(
            "cycle_phase",
            "N/A"
        )
    )

    structural_risk = (
        current_state.get(
            "structural_risk",
            "N/A"
        )
    )

    top_timing = (
        current_state.get(
            "top_timing",
            "N/A"
        )
    )

    operational = (
        current_state.get(
            "operational_regime",
            "N/A"
        )
    )

    position = (
        current_state.get(
            "existing_position",
            "N/A"
        )
    )

    equity = (
        current_state.get(
            "new_contribution_equity"
        )
    )

    reserve = (
        current_state.get(
            "new_contribution_reserve"
        )
    )

    reserve_stage = (
        current_state.get(
            "reserve_stage",
            0
        )
    )

    reserve_stage_fraction = (
        current_state.get(
            "reserve_stage_fraction",
            0.0
        )
    )

    reserve_cumulative_fraction = (
        current_state.get(
            "reserve_cumulative_fraction",
            0.0
        )
    )

    reserve_deployment_status = (
        current_state.get(
            "reserve_deployment_status",
            "NOT_ACTIVE"
        )
    )

    reserve_pending = (
        current_state.get(
            "reserve_pending",
            False
        )
    )

    reserve_blocked_by_regime = (
        current_state.get(
            "reserve_blocked_by_regime",
            False
        )
    )

    # --------------------------------------------------------
    # Cabeçalho
    # --------------------------------------------------------

    lines = []

    lines.append(
        REPORT_SEPARATOR
    )

    lines.append(
        "S&P 500 HISTORICAL CYCLE ATLAS"
    )

    lines.append(
        REPORT_SEPARATOR
    )

    lines.append("")

    lines.append(
        f"Data: {date}"
    )

    lines.append(
        f"S&P 500: {sp500}"
    )

    lines.append("")

    # --------------------------------------------------------
    # Diagnóstico principal
    # --------------------------------------------------------

    lines.append(
        "DIAGNÓSTICO DO CICLO"
    )

    lines.append("-" * 72)

    lines.append(
        f"Regime de mercado : {market_regime}"
    )

    lines.append(
        f"Fase do ciclo     : {cycle_phase}"
    )

    lines.append(
        f"Risco estrutural  : {structural_risk}"
    )

    lines.append(
        f"Timing de topo    : {top_timing}"
    )

    lines.append(
        f"Regime operacional: {operational}"
    )

    lines.append("")

    lines.append(
        "INTERPRETAÇÃO EXECUTIVA"
    )

    lines.append("-" * 72)

    lines.append(
        _regime_interpretation(
            operational
        )
    )

    lines.append("")

    lines.append(
        "DECISÃO DO ATLAS HOJE"
    )

    lines.append("-" * 72)

    lines.append(
        _current_action_text(
            operational,
            equity,
            reserve,
            reserve_stage,
            reserve_deployment_status,
        )
    )

    lines.append("")

    lines.append(
        "POR QUE ESTAMOS NESTE PONTO?"
    )

    lines.append("-" * 72)

    interpretation_items = [
        ("TREND", str(market_regime).replace(" MARKET", "")),
        ("VALUATION", current_state.get("valuation_regime", "N/A")),
        ("MOMENTUM", current_state.get("momentum_regime", "N/A")),
        ("LABOR", current_state.get("labor_regime", "N/A")),
        ("INDUSTRIAL", current_state.get("industrial_regime", "N/A")),
        ("INFLATION", current_state.get("inflation_regime", "N/A")),
        ("MONETARY", current_state.get("monetary_regime", "N/A")),
        ("YIELD_CURVE", current_state.get("curve_regime", "N/A")),
    ]

    label_names = {
        "TREND": "Tendência",
        "VALUATION": "Valuation",
        "MOMENTUM": "Momentum",
        "LABOR": "Trabalho",
        "INDUSTRIAL": "Indústria",
        "INFLATION": "Inflação",
        "MONETARY": "Política monetária",
        "YIELD_CURVE": "Curva de juros",
    }

    for label, status in interpretation_items:

        reading, explanation = _indicator_interpretation(
            label,
            status,
        )

        lines.append(
            f"{label_names[label]:18s}: "
            f"{status} | {reading} | {explanation}"
        )

    # --------------------------------------------------------
    # Mudança
    # --------------------------------------------------------

    if regime_change:

        if regime_change.get(
            "changed"
        ):

            lines.append("")

            lines.append(
                "⚠️ MUDANÇA DE REGIME"
            )

            lines.append(
                f"{regime_change.get('previous')} "
                f"→ "
                f"{regime_change.get('current')}"
            )

    lines.append("")

    # --------------------------------------------------------
    # Mercado
    # --------------------------------------------------------

    lines.append(
        "MERCADO"
    )

    lines.append("-" * 72)

    lines.append(
        f"Drawdown         : {drawdown}"
    )

    lines.append(
        f"Momentum 12m     : {momentum}"
    )

    if _valid(bull_age):

        lines.append(
            f"Idade do bull    : "
            f"{float(bull_age):.2f} anos"
        )

    lines.append(
        f"Retorno do bull  : {bull_return}"
    )

    # --------------------------------------------------------
    # Valuation
    # --------------------------------------------------------

    lines.append("")

    lines.append(
        "VALUATION"
    )

    lines.append("-" * 72)

    lines.append(
        f"CAPE             : {cape}"
    )

    lines.append(
        f"Percentil CAPE   : {cape_percentile}"
    )

    lines.append(
        f"Classificação    : "
        f"{current_state.get('valuation_regime', 'N/A')}"
    )

    # --------------------------------------------------------
    # Macro
    # --------------------------------------------------------

    lines.append("")

    lines.append(
        "MACRO & MONETÁRIO"
    )

    lines.append("-" * 72)

    lines.append(
        f"Fed Funds        : {fed}%"
    )

    lines.append(
        f"Fed Δ12m         : {fed_change}"
    )

    lines.append(
        f"Curva 10Y-2Y     : {curve}"
    )

    if _valid(inflation):

        lines.append(
            f"Inflação YoY     : "
            f"{float(inflation):.2f}%"
        )

    if _valid(
        inflation_change
    ):

        lines.append(
            f"Inflação Δ6m     : "
            f"{float(inflation_change):+.2f} p.p."
        )

    if _valid(unemployment):

        lines.append(
            f"Desemprego       : "
            f"{float(unemployment):.2f}%"
        )

    if _valid(sahm):

        lines.append(
            f"Sahm             : "
            f"{float(sahm):.2f}"
        )

    if _valid(industrial):

        lines.append(
            f"Produção ind. YoY: "
            f"{float(industrial):+.2f}%"
        )

    # --------------------------------------------------------
    # Classificações
    # --------------------------------------------------------

    lines.append("")

    lines.append(
        "CLASSIFICAÇÕES"
    )

    lines.append("-" * 72)

    classifications = [

        (
            "Valuation",
            current_state.get(
                "valuation_regime"
            )
        ),

        (
            "Momentum",
            current_state.get(
                "momentum_regime"
            )
        ),

        (
            "Drawdown",
            current_state.get(
                "drawdown_regime"
            )
        ),

        (
            "Labor",
            current_state.get(
                "labor_regime"
            )
        ),

        (
            "Industrial",
            current_state.get(
                "industrial_regime"
            )
        ),

        (
            "Inflation",
            current_state.get(
                "inflation_regime"
            )
        ),

        (
            "Monetary",
            current_state.get(
                "monetary_regime"
            )
        ),

        (
            "Yield curve",
            current_state.get(
                "curve_regime"
            )
        ),
    ]

    for label, value in classifications:

        lines.append(
            f"{label:16s}: {value}"
        )

    # --------------------------------------------------------
    # Scorecard
    # --------------------------------------------------------

    if (
        scorecard is not None
        and
        not scorecard.empty
    ):

        lines.append("")

        lines.append(
            "EVIDENCE SCORECARD"
        )

        lines.append("-" * 72)

        for _, row in scorecard.iterrows():

            signal = row.get(
                "signal",
                "N/A"
            )

            if signal == "CONSTRUCTIVE":

                icon = "✅"

            elif signal == "RISK":

                icon = "⚠️"

            else:

                icon = "•"

            lines.append(
                f"{icon} "
                f"{row.get('dimension')} | "
                f"{row.get('status')} | "
                f"{row.get('strength')}"
            )

    # --------------------------------------------------------
    # Política
    # --------------------------------------------------------

    lines.append("")

    lines.append(
        "POLÍTICA OPERACIONAL"
    )

    lines.append("-" * 72)

    lines.append(
        f"Posição existente: {position}"
    )

    if _valid(equity):

        lines.append(
            f"Novo aporte S&P : "
            f"{float(equity) * 100:.0f}%"
        )

    if _valid(reserve):

        lines.append(
            f"Nova reserva    : "
            f"{float(reserve) * 100:.0f}%"
        )

    lines.append("")

    lines.append(
        "UTILIZAÇÃO DA RESERVA"
    )

    lines.append("-" * 72)

    try:
        stage_int = int(reserve_stage)
    except Exception:
        stage_int = 0

    if stage_int <= 0:

        lines.append(
            "Estágio atual   : 0"
        )

        lines.append(
            "Status          : NOT_ACTIVE"
        )

        lines.append(
            "Ação            : continuar formando reserva conforme o regime."
        )

    else:

        lines.append(
            f"Estágio atual   : {stage_int}"
        )

        if _valid(reserve_stage_fraction):

            lines.append(
                f"Tranche estágio : "
                f"{float(reserve_stage_fraction) * 100:.0f}% da reserva-base"
            )

        if _valid(reserve_cumulative_fraction):

            lines.append(
                f"Tranche acum.   : "
                f"{float(reserve_cumulative_fraction) * 100:.0f}% da reserva-base"
            )

        lines.append(
            f"Status          : {reserve_deployment_status}"
        )

        if reserve_blocked_by_regime or reserve_pending:

            lines.append(
                "Condição        : RED_STRUCTURAL_STRESS bloqueia execução."
            )

            lines.append(
                "Ação            : manter tranche(s) PENDING até sair de RED."
            )

        elif reserve_deployment_status == "DEPLOYMENT_ALLOWED":

            lines.append(
                "Condição        : drawdown atingido e regime não está RED."
            )

            lines.append(
                "Ação            : deployment permitido conforme política 40/30/20/10."
            )

        else:

            lines.append(
                "Ação            : aguardar confirmação operacional."
            )

    lines.append("")

    lines.append(
        "REGRAS DA RESERVA"
    )

    lines.append("-" * 72)

    lines.append(
        "-15% drawdown -> 40% da reserva-base"
    )

    lines.append(
        "-20% drawdown -> +30%"
    )

    lines.append(
        "-30% drawdown -> +20%"
    )

    lines.append(
        "-35% drawdown -> +10%"
    )

    lines.append(
        "Se estiver RED_STRUCTURAL_STRESS: manter PENDING."
    )

    lines.append(
        "Ao sair de RED: liberar as tranches pendentes."
    )

    lines.append("")

    lines.append(
        "IMPORTANTE:"
    )

    lines.append(
        "O Atlas classifica regime."
    )

    lines.append(
        "Ele não prevê preço, topo ou crash."
    )

    lines.append(
        "Valuation extremo não é sinal automático de venda."
    )

    lines.append(
        "Drawdown define o tamanho potencial da tranche; "
        "o regime define se ela pode ser executada."
    )

    lines.append("")

    lines.append(
        REPORT_SEPARATOR
    )

    return "\n".join(
        lines
    )


# ============================================================
# 7. SALVAR RELATÓRIO TXT
# ============================================================

def save_text_report(
    report_text: str,
):

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    report_path = (
        DATA_DIR
        /
        "current_report.txt"
    )

    with open(
        report_path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            report_text
        )

    return report_path


# ============================================================
# 8. RELATÓRIO COMPLETO
# ============================================================

def generate_report(
    current_state: dict,
    scorecard: pd.DataFrame | None = None,
):

    # --------------------------------------------------------
    # Estado atual
    # --------------------------------------------------------

    current_df = save_current_state(
        current_state
    )

    # --------------------------------------------------------
    # Histórico
    # --------------------------------------------------------

    history = update_cycle_history(
        current_state
    )

    # --------------------------------------------------------
    # Mudança
    # --------------------------------------------------------

    regime_change = (
        detect_regime_change(
            history
        )
    )

    # --------------------------------------------------------
    # Texto
    # --------------------------------------------------------

    report_text = (
        build_executive_report(
            current_state=current_state,
            scorecard=scorecard,
            regime_change=regime_change,
        )
    )

    # --------------------------------------------------------
    # Salva TXT
    # --------------------------------------------------------

    report_path = (
        save_text_report(
            report_text
        )
    )

    # --------------------------------------------------------
    # Painel HTML para e-mail
    # --------------------------------------------------------

    report_html = (
        build_email_html_report(
            current_state=current_state,
            scorecard=scorecard,
            regime_change=regime_change,
        )
    )

    report_html_path = (
        save_html_report(
            report_html
        )
    )

    return {

        "current_state":
            current_df,

        "history":
            history,

        "regime_change":
            regime_change,

        "report_text":
            report_text,

        "report_path":
            report_path,

        "report_html":
            report_html,

        "report_html_path":
            report_html_path,
    }


# ============================================================
# 9. TESTE ISOLADO
# ============================================================

if __name__ == "__main__":

    from market_data import (
        build_master_dataset
    )

    from cycle_engine import (
        run_cycle_engine,
        get_current_cycle_state,
        build_evidence_scorecard,
    )

    print(
        REPORT_SEPARATOR
    )

    print(
        "TESTE — REPORT"
    )

    print(
        REPORT_SEPARATOR
    )

    master = (
        build_master_dataset()
    )

    classified = (
        run_cycle_engine(
            master
        )
    )

    current_state = (
        get_current_cycle_state(
            classified
        )
    )

    scorecard = (
        build_evidence_scorecard(
            current_state
        )
    )

    result = generate_report(
        current_state=current_state,
        scorecard=scorecard,
    )

    print("")

    print(
        result[
            "report_text"
        ]
    )

    print("")

    print(
        "Arquivos:"
    )

    print(
        CURRENT_STATE_FILE
    )

    print(
        CYCLE_HISTORY_FILE
    )

    print(
        result[
            "report_path"
        ]
    )

    print("")

    print(
        "✅ report.py executado."
    )
