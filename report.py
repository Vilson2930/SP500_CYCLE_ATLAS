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
