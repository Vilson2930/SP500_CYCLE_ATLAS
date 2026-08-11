# ============================================================
# SP500 CYCLE ATLAS
# cycle_engine.py
# ============================================================
#
# ÚNICO ENGINE DO PROJETO
#
# Responsável por:
#
# - classificar valuation
# - classificar momentum
# - classificar drawdown
# - classificar política monetária
# - classificar curva de juros
# - classificar inflação
# - classificar trabalho / Sahm
# - classificar produção industrial
# - identificar bull / bear
# - estimar idade e retorno do bull atual
# - classificar fase do ciclo
# - calcular risco estrutural
# - avaliar timing de topo
# - gerar regime operacional:
#
#   GREEN_EXPANSION
#   YELLOW_EXPENSIVE_BULL
#   ORANGE_DETERIORATION
#   RED_STRUCTURAL_STRESS
#   BLUE_REASSESS_ACCUMULATION
#   NEUTRAL_UNCERTAIN
#
# IMPORTANTE:
# O engine CLASSIFICA REGIME.
# Ele NÃO prevê preço, topo ou retorno futuro.
# ============================================================

from __future__ import annotations

import numpy as np
import pandas as pd

from settings import (

    # Drawdown
    DRAWDOWN_WARNING,
    DRAWDOWN_STRUCTURAL,
    DRAWDOWN_DEEP,
    DRAWDOWN_SEVERE,

    # Momentum
    MOMENTUM_SEVERE_NEGATIVE,
    MOMENTUM_NEGATIVE,
    MOMENTUM_STRONG,

    # CAPE
    CAPE_HIGH,
    CAPE_EXTREME,
    CAPE_ULTRA_EXTREME,

    CAPE_PERCENTILE_HIGH,
    CAPE_PERCENTILE_EXTREME,
    CAPE_PERCENTILE_ULTRA,

    # Sahm
    SAHM_WARNING,
    SAHM_RECESSION,

    # Industrial
    INDUSTRIAL_CONTRACTION,
    INDUSTRIAL_STRONG_CONTRACTION,

    # Inflação
    INFLATION_HIGH,
    INFLATION_REACCELERATION_LEVEL,
    INFLATION_ACCELERATION_THRESHOLD,

    # Fed
    FED_EASING_THRESHOLD,
    FED_TIGHTENING_THRESHOLD,

    # Curva
    CURVE_INVERTED,
    CURVE_FLAT_MAX,

    # Bear
    BEAR_THRESHOLD,

    # Regimes
    REGIME_GREEN,
    REGIME_YELLOW,
    REGIME_ORANGE,
    REGIME_RED,
    REGIME_BLUE,
    REGIME_NEUTRAL,

    # Ciclo
    CYCLE_BULL,
    CYCLE_BEAR,
    CYCLE_TRANSITION,

    # Fases
    PHASE_EXPANSION,
    PHASE_LATE_EXPANSION,
    PHASE_LATE_EXPANSION_EXTREME,
    PHASE_DETERIORATION,
    PHASE_STRUCTURAL_STRESS,
    PHASE_RECOVERY,

    # Risco
    RISK_LOW,
    RISK_MODERATE,
    RISK_HIGH,
    RISK_VERY_HIGH,

    # Top timing
    TOP_NOT_CONFIRMED,
    TOP_PARTIAL,
    TOP_STRONG,

    # Política
    CONTRIBUTION_POLICY,
    DEFAULT_EXISTING_POSITION,

    # Reserva / deployment
    RESERVE_DEPLOYMENT,
)


# ============================================================
# UTILITÁRIOS
# ============================================================

def _valid(value):
    return (
        value is not None
        and not pd.isna(value)
    )


def _safe_float(value):
    if not _valid(value):
        return np.nan

    try:
        return float(value)

    except Exception:
        return np.nan


# ============================================================
# 1. VALUATION
# ============================================================

def classify_valuation(
    cape,
    cape_percentile=None,
):

    cape = _safe_float(cape)

    percentile = _safe_float(
        cape_percentile
    )

    # --------------------------------------------------------
    # Percentil tem prioridade quando disponível.
    # --------------------------------------------------------

    if _valid(percentile):

        if percentile >= CAPE_PERCENTILE_ULTRA:
            return "EXTREME_TOP_1"

        if percentile >= CAPE_PERCENTILE_EXTREME:
            return "EXTREME_TOP_5"

        if percentile >= CAPE_PERCENTILE_HIGH:
            return "VERY_HIGH"

    # --------------------------------------------------------
    # Fallback absoluto
    # --------------------------------------------------------

    if _valid(cape):

        if cape >= CAPE_ULTRA_EXTREME:
            return "ULTRA_EXTREME"

        if cape >= CAPE_EXTREME:
            return "EXTREME"

        if cape >= CAPE_HIGH:
            return "HIGH"

        return "NORMAL"

    return "UNKNOWN"


# ============================================================
# 2. MOMENTUM
# ============================================================

def classify_momentum(
    momentum_12m,
):

    value = _safe_float(
        momentum_12m
    )

    if not _valid(value):
        return "UNKNOWN"

    if value <= MOMENTUM_SEVERE_NEGATIVE:
        return "SEVERE_NEGATIVE"

    if value <= MOMENTUM_NEGATIVE:
        return "NEGATIVE"

    if value >= MOMENTUM_STRONG:
        return "STRONG_POSITIVE"

    return "POSITIVE"


# ============================================================
# 3. DRAWDOWN
# ============================================================

def classify_drawdown(
    drawdown,
):

    dd = _safe_float(
        drawdown
    )

    if not _valid(dd):
        return "UNKNOWN"

    if dd <= DRAWDOWN_SEVERE:
        return "SEVERE_STRESS"

    if dd <= DRAWDOWN_DEEP:
        return "DEEP_STRESS"

    if dd <= DRAWDOWN_STRUCTURAL:
        return "STRUCTURAL_STRESS"

    if dd <= DRAWDOWN_WARNING:
        return "WARNING"

    return "NORMAL"


# ============================================================
# 4. MERCADO DE TRABALHO
# ============================================================

def classify_labor(
    sahm_indicator,
):

    sahm = _safe_float(
        sahm_indicator
    )

    if not _valid(sahm):
        return "UNKNOWN"

    if sahm >= SAHM_RECESSION:
        return "RECESSION_SIGNAL"

    if sahm >= SAHM_WARNING:
        return "DETERIORATING"

    return "STABLE"


# ============================================================
# 5. PRODUÇÃO INDUSTRIAL
# ============================================================

def classify_industrial(
    industrial_yoy,
):

    value = _safe_float(
        industrial_yoy
    )

    if not _valid(value):
        return "UNKNOWN"

    if value <= INDUSTRIAL_STRONG_CONTRACTION:
        return "STRONG_CONTRACTION"

    if value < INDUSTRIAL_CONTRACTION:
        return "CONTRACTION"

    if value >= 3:
        return "STRONG_EXPANSION"

    return "EXPANSION"


# ============================================================
# 6. INFLAÇÃO
# ============================================================

def classify_inflation(
    inflation_yoy,
    inflation_change_6m,
):

    inflation = _safe_float(
        inflation_yoy
    )

    acceleration = _safe_float(
        inflation_change_6m
    )

    if (
        not _valid(inflation)
        or
        not _valid(acceleration)
    ):
        return "UNKNOWN"

    if (
        inflation >= INFLATION_HIGH
        and
        acceleration > 0
    ):
        return "HIGH_RISING"

    if (
        inflation >= INFLATION_REACCELERATION_LEVEL
        and
        acceleration >= INFLATION_ACCELERATION_THRESHOLD
    ):
        return "REACCELERATING"

    if acceleration <= -INFLATION_ACCELERATION_THRESHOLD:
        return "FALLING"

    if acceleration <= 0:
        return "STABLE_OR_FALLING"

    return "MODERATE"


# ============================================================
# 7. POLÍTICA MONETÁRIA
# ============================================================

def classify_monetary(
    fed_change_12m,
):

    value = _safe_float(
        fed_change_12m
    )

    if not _valid(value):
        return "UNKNOWN"

    if value <= FED_EASING_THRESHOLD:
        return "EASING"

    if value >= FED_TIGHTENING_THRESHOLD:
        return "TIGHTENING"

    return "NEUTRAL"


# ============================================================
# 8. CURVA 10Y-2Y
# ============================================================

def classify_curve(
    yield_curve,
):

    value = _safe_float(
        yield_curve
    )

    if not _valid(value):
        return "UNKNOWN"

    if value < CURVE_INVERTED:
        return "INVERTED"

    if value <= CURVE_FLAT_MAX:
        return "FLAT_POSITIVE"

    return "NORMAL_POSITIVE"


# ============================================================
# 9. DETECTOR DE BULL MARKET
# ============================================================
#
# O estudo identificou bulls a partir do fundo de bear markets
# de -20% ou mais.
#
# Aqui fazemos a reconstrução histórica usando a série mensal.
# ============================================================

def calculate_bull_state(
    master: pd.DataFrame,
) -> pd.DataFrame:

    df = master.copy()

    if "sp500" not in df.columns:
        raise ValueError(
            "Coluna 'sp500' ausente."
        )

    df = (
        df
        .sort_values("date")
        .reset_index(drop=True)
    )

    prices = (
        df["sp500"]
        .astype(float)
        .values
    )

    dates = pd.to_datetime(
        df["date"]
    ).values

    n = len(df)

    bull_start_dates = [
        pd.NaT
    ] * n

    bull_start_prices = np.full(
        n,
        np.nan
    )

    bull_age_years = np.full(
        n,
        np.nan
    )

    bull_return = np.full(
        n,
        np.nan
    )

    # --------------------------------------------------------
    # Estado interno
    # --------------------------------------------------------

    peak_price = prices[0]
    peak_index = 0

    in_bear = False

    bear_bottom_price = np.nan
    bear_bottom_index = None

    current_bull_start_index = 0
    current_bull_start_price = prices[0]

    for i in range(n):

        price = prices[i]

        if pd.isna(price):
            continue

        # ----------------------------------------------------
        # ATH / pico corrente
        # ----------------------------------------------------

        if price > peak_price:

            peak_price = price
            peak_index = i

            if not in_bear:
                pass

        drawdown_from_peak = (
            price /
            peak_price
            - 1
        )

        # ----------------------------------------------------
        # Entrou em bear
        # ----------------------------------------------------

        if (
            drawdown_from_peak
            <= BEAR_THRESHOLD
            and
            not in_bear
        ):

            in_bear = True

            bear_bottom_price = price
            bear_bottom_index = i

        # ----------------------------------------------------
        # Atualiza fundo do bear
        # ----------------------------------------------------

        if in_bear:

            if price < bear_bottom_price:

                bear_bottom_price = price
                bear_bottom_index = i

            # ------------------------------------------------
            # Recuperou ATH anterior
            #
            # Nesse momento consideramos o bull iniciado
            # no fundo observado do bear.
            # ------------------------------------------------

            if price >= peak_price:

                current_bull_start_index = (
                    bear_bottom_index
                )

                current_bull_start_price = (
                    bear_bottom_price
                )

                in_bear = False

                peak_price = price
                peak_index = i

        # ----------------------------------------------------
        # Durante bear, continuamos usando o último bull start
        # apenas como referência histórica.
        # ----------------------------------------------------

        start_i = (
            current_bull_start_index
        )

        start_price = (
            current_bull_start_price
        )

        bull_start_dates[i] = (
            pd.Timestamp(
                dates[start_i]
            )
        )

        bull_start_prices[i] = (
            start_price
        )

        if _valid(start_price):

            bull_return[i] = (
                price /
                start_price
                - 1
            )

        age_days = (
            pd.Timestamp(
                dates[i]
            )
            -
            pd.Timestamp(
                dates[start_i]
            )
        ).days

        bull_age_years[i] = (
            age_days /
            365.25
        )

    df[
        "bull_start_date"
    ] = bull_start_dates

    df[
        "bull_start_price"
    ] = bull_start_prices

    df[
        "bull_age_years"
    ] = bull_age_years

    df[
        "bull_return"
    ] = bull_return

    return df


# ============================================================
# 10. CONTAGEM DE DETERIORAÇÃO MACRO
# ============================================================

def macro_deterioration_count(
    labor,
    industrial,
    monetary,
    inflation,
    curve,
):

    count = 0

    if labor in [
        "DETERIORATING",
        "RECESSION_SIGNAL",
    ]:
        count += 1

    if industrial in [
        "CONTRACTION",
        "STRONG_CONTRACTION",
    ]:
        count += 1

    if monetary == "TIGHTENING":
        count += 1

    if inflation in [
        "HIGH_RISING",
        "REACCELERATING",
    ]:
        count += 1

    if curve == "INVERTED":
        count += 1

    return count


# ============================================================
# 11. CONTAGEM DE DETERIORAÇÃO DE MERCADO
# ============================================================

def market_deterioration_count(
    momentum,
    drawdown_regime,
):

    count = 0

    if momentum in [
        "NEGATIVE",
        "SEVERE_NEGATIVE",
    ]:
        count += 1

    if drawdown_regime == "WARNING":
        count += 1

    if drawdown_regime in [
        "STRUCTURAL_STRESS",
        "DEEP_STRESS",
        "SEVERE_STRESS",
    ]:
        count += 2

    return count


# ============================================================
# 12. REGIME DE MERCADO
# ============================================================

def classify_market_regime(
    drawdown,
    momentum,
):

    dd = _safe_float(
        drawdown
    )

    if not _valid(dd):
        return CYCLE_TRANSITION

    # --------------------------------------------------------
    # Bear confirmado por preço
    # --------------------------------------------------------

    if dd <= BEAR_THRESHOLD:
        return CYCLE_BEAR

    # --------------------------------------------------------
    # Correção relevante mas ainda não bear
    # --------------------------------------------------------

    if (
        dd <= DRAWDOWN_STRUCTURAL
        and
        momentum in [
            "NEGATIVE",
            "SEVERE_NEGATIVE",
        ]
    ):
        return CYCLE_TRANSITION

    return CYCLE_BULL


# ============================================================
# 13. FASE DO CICLO
# ============================================================

def classify_cycle_phase(
    market_regime,
    valuation,
    momentum,
    labor,
    industrial,
    drawdown_regime,
    bull_age_years,
):

    # --------------------------------------------------------
    # Stress
    # --------------------------------------------------------

    if market_regime == CYCLE_BEAR:

        if drawdown_regime in [
            "DEEP_STRESS",
            "SEVERE_STRESS",
        ]:
            return PHASE_STRUCTURAL_STRESS

        return PHASE_DETERIORATION

    # --------------------------------------------------------
    # Transição
    # --------------------------------------------------------

    if market_regime == CYCLE_TRANSITION:
        return PHASE_DETERIORATION

    # --------------------------------------------------------
    # Bull + valuation extremo
    # --------------------------------------------------------

    if (
        market_regime == CYCLE_BULL
        and
        valuation in [
            "EXTREME_TOP_1",
            "EXTREME_TOP_5",
            "ULTRA_EXTREME",
            "EXTREME",
        ]
        and
        momentum in [
            "POSITIVE",
            "STRONG_POSITIVE",
        ]
        and
        labor == "STABLE"
        and
        industrial in [
            "EXPANSION",
            "STRONG_EXPANSION",
        ]
    ):

        return (
            PHASE_LATE_EXPANSION_EXTREME
        )

    # --------------------------------------------------------
    # Bull mais maduro
    # --------------------------------------------------------

    if (
        _valid(bull_age_years)
        and
        bull_age_years >= 4.0
    ):

        return PHASE_LATE_EXPANSION

    # --------------------------------------------------------
    # Bull normal
    # --------------------------------------------------------

    if (
        market_regime == CYCLE_BULL
        and
        momentum in [
            "POSITIVE",
            "STRONG_POSITIVE",
        ]
    ):

        return PHASE_EXPANSION

    return PHASE_RECOVERY


# ============================================================
# 14. RISCO ESTRUTURAL
# ============================================================

def classify_structural_risk(
    valuation,
    inflation,
    curve,
    labor,
    industrial,
    drawdown_regime,
    monetary,
):

    score = 0

    # --------------------------------------------------------
    # Valuation
    # --------------------------------------------------------

    if valuation in [
        "EXTREME_TOP_1",
        "ULTRA_EXTREME",
    ]:
        score += 3

    elif valuation in [
        "EXTREME_TOP_5",
        "EXTREME",
    ]:
        score += 2

    elif valuation in [
        "VERY_HIGH",
        "HIGH",
    ]:
        score += 1

    # --------------------------------------------------------
    # Inflação
    # --------------------------------------------------------

    if inflation == "HIGH_RISING":
        score += 2

    elif inflation == "REACCELERATING":
        score += 1

    # --------------------------------------------------------
    # Curva
    # --------------------------------------------------------

    if curve == "INVERTED":
        score += 2

    elif curve == "FLAT_POSITIVE":
        score += 1

    # --------------------------------------------------------
    # Trabalho
    # --------------------------------------------------------

    if labor == "RECESSION_SIGNAL":
        score += 3

    elif labor == "DETERIORATING":
        score += 1

    # --------------------------------------------------------
    # Produção
    # --------------------------------------------------------

    if industrial == "STRONG_CONTRACTION":
        score += 2

    elif industrial == "CONTRACTION":
        score += 1

    # --------------------------------------------------------
    # Drawdown
    # --------------------------------------------------------

    if drawdown_regime in [
        "DEEP_STRESS",
        "SEVERE_STRESS",
    ]:
        score += 3

    elif drawdown_regime == "STRUCTURAL_STRESS":
        score += 2

    elif drawdown_regime == "WARNING":
        score += 1

    # --------------------------------------------------------
    # Política monetária
    # --------------------------------------------------------

    if monetary == "TIGHTENING":
        score += 1

    # --------------------------------------------------------
    # Classificação
    # --------------------------------------------------------

    if score >= 8:
        return RISK_VERY_HIGH

    if score >= 4:
        return RISK_HIGH

    if score >= 2:
        return RISK_MODERATE

    return RISK_LOW


# ============================================================
# 15. TIMING DE TOPO
# ============================================================
#
# IMPORTANTE:
# Não é previsão de topo.
#
# Mede apenas QUANTOS sinais de deterioração estão presentes.
# ============================================================

def classify_top_timing(
    momentum,
    drawdown_regime,
    labor,
    industrial,
    monetary,
    curve,
):

    confirmations = 0

    if momentum in [
        "NEGATIVE",
        "SEVERE_NEGATIVE",
    ]:
        confirmations += 1

    if drawdown_regime in [
        "WARNING",
        "STRUCTURAL_STRESS",
        "DEEP_STRESS",
        "SEVERE_STRESS",
    ]:
        confirmations += 1

    if labor in [
        "DETERIORATING",
        "RECESSION_SIGNAL",
    ]:
        confirmations += 1

    if industrial in [
        "CONTRACTION",
        "STRONG_CONTRACTION",
    ]:
        confirmations += 1

    if monetary == "TIGHTENING":
        confirmations += 1

    if curve == "INVERTED":
        confirmations += 1

    if confirmations >= 4:
        return TOP_STRONG

    if confirmations >= 2:
        return TOP_PARTIAL

    return TOP_NOT_CONFIRMED


# ============================================================
# 16. REGIME OPERACIONAL
# ============================================================

def classify_operational_regime(
    drawdown,
    drawdown_regime,
    momentum,
    valuation,
    labor,
    industrial,
    monetary,
    inflation,
    curve,
):

    dd = _safe_float(
        drawdown
    )

    macro_count = (
        macro_deterioration_count(
            labor=labor,
            industrial=industrial,
            monetary=monetary,
            inflation=inflation,
            curve=curve,
        )
    )

    market_count = (
        market_deterioration_count(
            momentum=momentum,
            drawdown_regime=drawdown_regime,
        )
    )

    # --------------------------------------------------------
    # RED
    #
    # Drawdown estrutural + macro deteriorado
    # --------------------------------------------------------

    if (
        _valid(dd)
        and
        dd <= DRAWDOWN_STRUCTURAL
        and
        macro_count >= 2
    ):

        return (
            REGIME_RED,
            macro_count,
            market_count,
        )

    # --------------------------------------------------------
    # BLUE
    #
    # Drawdown estrutural sem deterioração ampla
    # --------------------------------------------------------

    if (
        _valid(dd)
        and
        dd <= DRAWDOWN_STRUCTURAL
        and
        macro_count <= 1
    ):

        return (
            REGIME_BLUE,
            macro_count,
            market_count,
        )

    # --------------------------------------------------------
    # ORANGE
    # --------------------------------------------------------

    if (
        macro_count >= 2
        and
        market_count >= 1
    ):

        return (
            REGIME_ORANGE,
            macro_count,
            market_count,
        )

    # --------------------------------------------------------
    # YELLOW
    #
    # Bull ainda forte + valuation extremo
    # --------------------------------------------------------

    if (
        valuation in [
            "EXTREME_TOP_1",
            "EXTREME_TOP_5",
            "ULTRA_EXTREME",
            "EXTREME",
        ]
        and
        momentum in [
            "POSITIVE",
            "STRONG_POSITIVE",
        ]
        and
        labor == "STABLE"
        and
        industrial in [
            "EXPANSION",
            "STRONG_EXPANSION",
        ]
    ):

        return (
            REGIME_YELLOW,
            macro_count,
            market_count,
        )

    # --------------------------------------------------------
    # GREEN
    # --------------------------------------------------------

    if (
        momentum in [
            "POSITIVE",
            "STRONG_POSITIVE",
        ]
        and
        macro_count <= 1
    ):

        return (
            REGIME_GREEN,
            macro_count,
            market_count,
        )

    # --------------------------------------------------------
    # NEUTRAL
    # --------------------------------------------------------

    return (
        REGIME_NEUTRAL,
        macro_count,
        market_count,
    )


# ============================================================
# 17. POLÍTICA DE APORTE
# ============================================================

def get_contribution_policy(
    operational_regime,
):

    policy = (
        CONTRIBUTION_POLICY
        .get(
            operational_regime,
            {
                "equity": 0.90,
                "reserve": 0.10,
            }
        )
    )

    return {
        "existing_position":
            DEFAULT_EXISTING_POSITION,

        "new_contribution_equity":
            policy["equity"],

        "new_contribution_reserve":
            policy["reserve"],
    }


# ============================================================
# 17B. POLÍTICA DE UTILIZAÇÃO DA RESERVA
# ============================================================
#
# Resultado do estudo histórico:
#
# -15% -> 40%
# -20% -> +30%
# -30% -> +20%
# -35% -> +10%
#
# Regra de confirmação:
#
# se o regime estiver em RED_STRUCTURAL_STRESS,
# a tranche NÃO é executada imediatamente;
# ela fica PENDING até o regime deixar RED.
#
# IMPORTANTE:
# Esta função classifica o estado operacional corrente.
# O controle persistente de "já executado / ainda pendente"
# deve ser feito pelo estado do episódio entre execuções.
# ============================================================

def get_reserve_deployment_policy(
    drawdown,
    operational_regime,
):
    dd = _safe_float(drawdown)

    if not _valid(dd):
        return {
            "reserve_stage": 0,
            "reserve_stage_fraction": 0.0,
            "reserve_cumulative_fraction": 0.0,
            "reserve_deployment_status": "NOT_ACTIVE",
            "reserve_pending": False,
            "reserve_blocked_by_regime": False,
        }

    levels = sorted(
        [
            (float(threshold), float(fraction))
            for threshold, fraction in RESERVE_DEPLOYMENT.items()
        ],
        key=lambda x: x[0],
        reverse=True,
    )

    stage = 0
    stage_fraction = 0.0
    cumulative_fraction = 0.0

    for idx, (threshold, fraction) in enumerate(levels, start=1):
        if dd <= threshold:
            stage = idx
            stage_fraction = fraction
            cumulative_fraction += fraction

    if stage == 0:
        return {
            "reserve_stage": 0,
            "reserve_stage_fraction": 0.0,
            "reserve_cumulative_fraction": 0.0,
            "reserve_deployment_status": "NOT_ACTIVE",
            "reserve_pending": False,
            "reserve_blocked_by_regime": False,
        }

    if operational_regime == REGIME_RED:
        return {
            "reserve_stage": stage,
            "reserve_stage_fraction": stage_fraction,
            "reserve_cumulative_fraction": cumulative_fraction,
            "reserve_deployment_status": "PENDING_REGIME_CONFIRMATION",
            "reserve_pending": True,
            "reserve_blocked_by_regime": True,
        }

    return {
        "reserve_stage": stage,
        "reserve_stage_fraction": stage_fraction,
        "reserve_cumulative_fraction": cumulative_fraction,
        "reserve_deployment_status": "DEPLOYMENT_ALLOWED",
        "reserve_pending": False,
        "reserve_blocked_by_regime": False,
    }


# ============================================================
# 18. CLASSIFICAR UMA LINHA
# ============================================================

def classify_row(
    row,
):

    valuation = classify_valuation(
        cape=row.get("cape"),
        cape_percentile=row.get(
            "cape_percentile"
        ),
    )

    momentum = classify_momentum(
        row.get("return_12m")
    )

    drawdown_regime = (
        classify_drawdown(
            row.get("drawdown")
        )
    )

    labor = classify_labor(
        row.get("sahm_indicator")
    )

    industrial = classify_industrial(
        row.get(
            "industrial_production_yoy"
        )
    )

    inflation = classify_inflation(
        inflation_yoy=row.get(
            "inflation_yoy"
        ),
        inflation_change_6m=row.get(
            "inflation_change_6m"
        ),
    )

    monetary = classify_monetary(
        row.get("fed_change_12m")
    )

    curve = classify_curve(
        row.get(
            "yield_curve_10y_2y"
        )
    )

    market_regime = (
        classify_market_regime(
            drawdown=row.get(
                "drawdown"
            ),
            momentum=momentum,
        )
    )

    bull_age = row.get(
        "bull_age_years"
    )

    phase = classify_cycle_phase(
        market_regime=market_regime,
        valuation=valuation,
        momentum=momentum,
        labor=labor,
        industrial=industrial,
        drawdown_regime=drawdown_regime,
        bull_age_years=bull_age,
    )

    structural_risk = (
        classify_structural_risk(
            valuation=valuation,
            inflation=inflation,
            curve=curve,
            labor=labor,
            industrial=industrial,
            drawdown_regime=drawdown_regime,
            monetary=monetary,
        )
    )

    top_timing = (
        classify_top_timing(
            momentum=momentum,
            drawdown_regime=drawdown_regime,
            labor=labor,
            industrial=industrial,
            monetary=monetary,
            curve=curve,
        )
    )

    (
        operational_regime,
        macro_count,
        market_count,
    ) = classify_operational_regime(

        drawdown=row.get(
            "drawdown"
        ),

        drawdown_regime=drawdown_regime,

        momentum=momentum,

        valuation=valuation,

        labor=labor,

        industrial=industrial,

        monetary=monetary,

        inflation=inflation,

        curve=curve,
    )

    policy = get_contribution_policy(
        operational_regime
    )

    reserve_policy = get_reserve_deployment_policy(
        drawdown=row.get("drawdown"),
        operational_regime=operational_regime,
    )

    return pd.Series({

        "valuation_regime":
            valuation,

        "momentum_regime":
            momentum,

        "drawdown_regime":
            drawdown_regime,

        "labor_regime":
            labor,

        "industrial_regime":
            industrial,

        "inflation_regime":
            inflation,

        "monetary_regime":
            monetary,

        "curve_regime":
            curve,

        "market_regime":
            market_regime,

        "cycle_phase":
            phase,

        "structural_risk":
            structural_risk,

        "top_timing":
            top_timing,

        "macro_deterioration_count":
            macro_count,

        "market_deterioration_count":
            market_count,

        "operational_regime":
            operational_regime,

        "existing_position":
            policy[
                "existing_position"
            ],

        "new_contribution_equity":
            policy[
                "new_contribution_equity"
            ],

        "new_contribution_reserve":
            policy[
                "new_contribution_reserve"
            ],

        "reserve_stage":
            reserve_policy[
                "reserve_stage"
            ],

        "reserve_stage_fraction":
            reserve_policy[
                "reserve_stage_fraction"
            ],

        "reserve_cumulative_fraction":
            reserve_policy[
                "reserve_cumulative_fraction"
            ],

        "reserve_deployment_status":
            reserve_policy[
                "reserve_deployment_status"
            ],

        "reserve_pending":
            reserve_policy[
                "reserve_pending"
            ],

        "reserve_blocked_by_regime":
            reserve_policy[
                "reserve_blocked_by_regime"
            ],
    })


# ============================================================
# 19. EXECUTAR ENGINE COMPLETO
# ============================================================

def run_cycle_engine(
    master: pd.DataFrame,
) -> pd.DataFrame:

    if master is None or master.empty:

        raise ValueError(
            "Master dataset vazio."
        )

    df = master.copy()

    df = calculate_bull_state(
        df
    )

    classifications = df.apply(
        classify_row,
        axis=1,
    )

    result = pd.concat(
        [
            df,
            classifications,
        ],
        axis=1,
    )

    return result


# ============================================================
# 20. ÚLTIMO ESTADO
# ============================================================

def get_current_cycle_state(
    classified: pd.DataFrame,
) -> dict:

    if (
        classified is None
        or
        classified.empty
    ):

        raise ValueError(
            "Dataset classificado vazio."
        )

    latest = (
        classified
        .sort_values("date")
        .iloc[-1]
    )

    fields = [

        "date",
        "sp500",

        "drawdown",
        "return_12m",

        "cape",
        "cape_percentile",

        "bull_start_date",
        "bull_start_price",
        "bull_age_years",
        "bull_return",

        "fed_funds",
        "fed_change_12m",

        "yield_curve_10y_2y",

        "inflation_yoy",
        "inflation_change_6m",

        "unemployment",
        "sahm_indicator",

        "industrial_production_yoy",

        "valuation_regime",
        "momentum_regime",
        "drawdown_regime",

        "labor_regime",
        "industrial_regime",

        "inflation_regime",
        "monetary_regime",
        "curve_regime",

        "market_regime",
        "cycle_phase",

        "structural_risk",
        "top_timing",

        "macro_deterioration_count",
        "market_deterioration_count",

        "operational_regime",

        "existing_position",

        "new_contribution_equity",
        "new_contribution_reserve",

        "reserve_stage",
        "reserve_stage_fraction",
        "reserve_cumulative_fraction",
        "reserve_deployment_status",
        "reserve_pending",
        "reserve_blocked_by_regime",
    ]

    state = {}

    for field in fields:

        if field in latest.index:

            value = latest[field]

            if isinstance(
                value,
                pd.Timestamp
            ):

                value = (
                    value.strftime(
                        "%Y-%m-%d"
                    )
                )

            elif isinstance(
                value,
                np.generic
            ):

                value = value.item()

            state[field] = value

    return state


# ============================================================
# 21. EVIDENCE SCORECARD
# ============================================================

def build_evidence_scorecard(
    current_state: dict,
) -> pd.DataFrame:

    rows = []

    # --------------------------------------------------------
    # Trend
    # --------------------------------------------------------

    market = current_state.get(
        "market_regime"
    )

    if market == CYCLE_BULL:

        rows.append({
            "dimension": "TREND",
            "status": "BULL",
            "signal": "CONSTRUCTIVE",
            "strength": "STRONG",
        })

    elif market == CYCLE_BEAR:

        rows.append({
            "dimension": "TREND",
            "status": "BEAR",
            "signal": "RISK",
            "strength": "STRONG",
        })

    else:

        rows.append({
            "dimension": "TREND",
            "status": "TRANSITION",
            "signal": "NEUTRAL",
            "strength": "STRONG",
        })

    # --------------------------------------------------------
    # Valuation
    # --------------------------------------------------------

    valuation = current_state.get(
        "valuation_regime"
    )

    if valuation in [
        "EXTREME_TOP_1",
        "EXTREME_TOP_5",
        "ULTRA_EXTREME",
        "EXTREME",
    ]:

        signal = "RISK"

    elif valuation in [
        "VERY_HIGH",
        "HIGH",
    ]:

        signal = "NEUTRAL"

    else:

        signal = "CONSTRUCTIVE"

    rows.append({
        "dimension": "VALUATION",
        "status": valuation,
        "signal": signal,
        "strength": "STRONG",
    })

    # --------------------------------------------------------
    # Momentum
    # --------------------------------------------------------

    momentum = current_state.get(
        "momentum_regime"
    )

    rows.append({
        "dimension": "MOMENTUM",
        "status": momentum,
        "signal":
            "CONSTRUCTIVE"
            if momentum in [
                "POSITIVE",
                "STRONG_POSITIVE",
            ]
            else "RISK",
        "strength": "MODERATE",
    })

    # --------------------------------------------------------
    # Labor
    # --------------------------------------------------------

    labor = current_state.get(
        "labor_regime"
    )

    rows.append({
        "dimension": "LABOR",
        "status": labor,
        "signal":
            "CONSTRUCTIVE"
            if labor == "STABLE"
            else "RISK",
        "strength": "STRONG",
    })

    # --------------------------------------------------------
    # Industrial
    # --------------------------------------------------------

    industrial = current_state.get(
        "industrial_regime"
    )

    rows.append({
        "dimension": "INDUSTRIAL",
        "status": industrial,
        "signal":
            "CONSTRUCTIVE"
            if industrial in [
                "EXPANSION",
                "STRONG_EXPANSION",
            ]
            else "RISK",
        "strength": "MODERATE",
    })

    # --------------------------------------------------------
    # Inflation
    # --------------------------------------------------------

    inflation = current_state.get(
        "inflation_regime"
    )

    rows.append({
        "dimension": "INFLATION",
        "status": inflation,
        "signal":
            "RISK"
            if inflation in [
                "HIGH_RISING",
                "REACCELERATING",
            ]
            else "NEUTRAL",
        "strength": "MODERATE",
    })

    # --------------------------------------------------------
    # Monetary
    # --------------------------------------------------------

    monetary = current_state.get(
        "monetary_regime"
    )

    rows.append({
        "dimension": "MONETARY",
        "status": monetary,
        "signal":
            "RISK"
            if monetary == "TIGHTENING"
            else "CONSTRUCTIVE",
        "strength": "MODERATE",
    })

    # --------------------------------------------------------
    # Curve
    # --------------------------------------------------------

    curve = current_state.get(
        "curve_regime"
    )

    rows.append({
        "dimension": "YIELD_CURVE",
        "status": curve,
        "signal":
            "RISK"
            if curve == "INVERTED"
            else "NEUTRAL",
        "strength": "MODERATE",
    })

    return pd.DataFrame(rows)


# ============================================================
# TESTE ISOLADO
# ============================================================

if __name__ == "__main__":

    from market_data import (
        build_master_dataset
    )

    print("=" * 80)
    print("TESTE — CYCLE ENGINE")
    print("=" * 80)

    master = build_master_dataset()

    classified = run_cycle_engine(
        master
    )

    state = get_current_cycle_state(
        classified
    )

    print("")
    print("=" * 80)
    print("ESTADO ATUAL")
    print("=" * 80)

    for key, value in state.items():

        print(
            f"{key:32s}: "
            f"{value}"
        )

    scorecard = (
        build_evidence_scorecard(
            state
        )
    )

    print("")
    print("=" * 80)
    print("EVIDENCE SCORECARD")
    print("=" * 80)

    print(
        scorecard.to_string(
            index=False
        )
    )

    print("")
    print(
        "✅ cycle_engine.py executado."
    )
