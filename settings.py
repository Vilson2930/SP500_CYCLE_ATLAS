# ============================================================
# SP500 CYCLE ATLAS
# settings.py
# ============================================================
#
# Configurações centrais do projeto.
#
# Este arquivo contém:
#
# - fontes de dados
# - séries utilizadas
# - thresholds validados no estudo
# - parâmetros de classificação
# - caminhos dos arquivos
#
# IMPORTANTE:
# O projeto classifica REGIME.
# Não prevê preço, topo ou retorno futuro.
# ============================================================

from pathlib import Path


# ============================================================
# PROJETO
# ============================================================

PROJECT_NAME = "SP500_CYCLE_ATLAS"

VERSION = "1.1.0"


# ============================================================
# DIRETÓRIOS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"

CURRENT_STATE_FILE = DATA_DIR / "current_state.csv"

CYCLE_HISTORY_FILE = DATA_DIR / "cycle_history.csv"

RESERVE_STATE_FILE = DATA_DIR / "reserve_state.json"


# ============================================================
# MERCADO
# ============================================================

SP500_TICKER = "^GSPC"

MARKET_START_DATE = "1927-01-01"


# ============================================================
# SHILLER
# ============================================================
#
# Utilizado principalmente para:
#
# - CAPE
# - histórico longo
#
# Mantemos duas URLs para redundância.
# ============================================================

SHILLER_URLS = [

    "http://www.econ.yale.edu/~shiller/data/ie_data.xls",

    "https://www.econ.yale.edu/~shiller/data/ie_data.xls",
]


# ============================================================
# FRED SERIES
# ============================================================

FRED_SERIES = {

    # --------------------------------------------------------
    # Política monetária
    # --------------------------------------------------------

    "fed_funds": "FEDFUNDS",

    # --------------------------------------------------------
    # Treasury
    # --------------------------------------------------------

    "treasury_10y": "GS10",

    "treasury_2y": "GS2",

    # --------------------------------------------------------
    # Inflação
    # --------------------------------------------------------

    "cpi": "CPIAUCSL",

    # --------------------------------------------------------
    # Mercado de trabalho
    # --------------------------------------------------------

    "unemployment": "UNRATE",

    # Sahm Rule oficial
    "sahm": "SAHMREALTIME",

    # --------------------------------------------------------
    # Atividade econômica
    # --------------------------------------------------------

    "industrial_production": "INDPRO",
}


FRED_START_DATE = "1950-01-01"


# ============================================================
# DRAWDOWN
# ============================================================
#
# O estudo mostrou maior robustez para ~ -15%.
#
# Não é sinal automático de compra ou venda.
# É uma região estrutural de stress.
# ============================================================

DRAWDOWN_WARNING = -0.10

DRAWDOWN_STRUCTURAL = -0.15

DRAWDOWN_DEEP = -0.20

DRAWDOWN_SEVERE = -0.30


# ============================================================
# MOMENTUM 12 MESES
# ============================================================

MOMENTUM_SEVERE_NEGATIVE = -0.10

MOMENTUM_NEGATIVE = 0.00

MOMENTUM_STRONG = 0.15


# ============================================================
# CAPE
# ============================================================
#
# CAPE regula valuation.
#
# NÃO é usado como market timing.
# ============================================================

CAPE_HIGH = 30.0

CAPE_EXTREME = 35.0

CAPE_ULTRA_EXTREME = 40.0


# ============================================================
# PERCENTIL CAPE
# ============================================================

CAPE_PERCENTILE_HIGH = 0.90

CAPE_PERCENTILE_EXTREME = 0.95

CAPE_PERCENTILE_ULTRA = 0.99


# ============================================================
# SAHM
# ============================================================

SAHM_WARNING = 0.30

SAHM_RECESSION = 0.50


# ============================================================
# PRODUÇÃO INDUSTRIAL
# ============================================================

INDUSTRIAL_CONTRACTION = 0.00

INDUSTRIAL_STRONG_CONTRACTION = -2.00


# ============================================================
# INFLAÇÃO
# ============================================================

INFLATION_HIGH = 4.0

INFLATION_REACCELERATION_LEVEL = 3.0

INFLATION_ACCELERATION_THRESHOLD = 0.50


# ============================================================
# POLÍTICA MONETÁRIA
# ============================================================
#
# Padronização final do estudo.
#
# Fed change 12m:
#
# <= -0.50 → easing
# >= +0.50 → tightening
# restante → neutral
# ============================================================

FED_EASING_THRESHOLD = -0.50

FED_TIGHTENING_THRESHOLD = 0.50


# ============================================================
# YIELD CURVE 10Y - 2Y
# ============================================================

CURVE_INVERTED = 0.00

CURVE_FLAT_MAX = 0.50


# ============================================================
# BULL MARKET
# ============================================================
#
# Definição histórica utilizada no estudo:
#
# bear:
# queda >=20%
#
# bull:
# recuperação relevante após fundo.
#
# No monitor operacional,
# o drawdown e a tendência têm prioridade.
# ============================================================

BEAR_THRESHOLD = -0.20


# ============================================================
# REGIMES OPERACIONAIS
# ============================================================

REGIME_GREEN = "GREEN_EXPANSION"

REGIME_YELLOW = "YELLOW_EXPENSIVE_BULL"

REGIME_ORANGE = "ORANGE_DETERIORATION"

REGIME_RED = "RED_STRUCTURAL_STRESS"

REGIME_BLUE = "BLUE_REASSESS_ACCUMULATION"

REGIME_NEUTRAL = "NEUTRAL_UNCERTAIN"


# ============================================================
# CLASSIFICAÇÃO DO CICLO
# ============================================================

CYCLE_BULL = "BULL MARKET"

CYCLE_BEAR = "BEAR MARKET"

CYCLE_TRANSITION = "TRANSITION"


# ============================================================
# FASES
# ============================================================

PHASE_EXPANSION = "EXPANSION"

PHASE_LATE_EXPANSION = "LATE_EXPANSION"

PHASE_LATE_EXPANSION_EXTREME = (
    "LATE_EXPANSION / VALUATION_EXTREME"
)

PHASE_DETERIORATION = "DETERIORATION"

PHASE_STRUCTURAL_STRESS = "STRUCTURAL_STRESS"

PHASE_RECOVERY = "RECOVERY"


# ============================================================
# RISCO ESTRUTURAL
# ============================================================

RISK_LOW = "LOW"

RISK_MODERATE = "MODERATE"

RISK_HIGH = "HIGH"

RISK_VERY_HIGH = "VERY_HIGH"


# ============================================================
# TIMING DE TOPO
# ============================================================

TOP_NOT_CONFIRMED = "NOT_CONFIRMED"

TOP_PARTIAL = "PARTIAL_CONFIRMATION"

TOP_STRONG = "STRONG_CONFIRMATION"


# ============================================================
# POLÍTICA OPERACIONAL
# ============================================================
#
# Resultado prático do estudo:
#
# posição estrutural não é vendida apenas porque
# o valuation está elevado.
#
# ============================================================

DEFAULT_EXISTING_POSITION = "HOLD"


# ============================================================
# APORTE / RESERVA
# ============================================================
#
# Valores NÃO representam previsão.
#
# São apenas política operacional de acompanhamento.
#
# Política operacional definida a partir do estudo:
#
# - valuation regula a agressividade dos NOVOS aportes;
# - posição estrutural permanece HOLD;
# - deterioração confirmada aumenta a reserva;
# - stress sem deterioração macro ampla favorece acumulação;
# - reserva acumulada pode ser utilizada gradualmente.
# ============================================================

CONTRIBUTION_POLICY = {

    # --------------------------------------------------------
    # GREEN
    # Expansão saudável.
    # Novo aporte integralmente direcionado ao S&P 500.
    # --------------------------------------------------------

    REGIME_GREEN: {
        "equity": 1.00,
        "reserve": 0.00,
        "existing_position": "HOLD",
    },

    # --------------------------------------------------------
    # YELLOW
    # Bull market ainda ativo, porém valuation extremo.
    #
    # CAPE reduz a agressividade do NOVO aporte.
    # A posição existente permanece HOLD.
    # --------------------------------------------------------

    REGIME_YELLOW: {
        "equity": 0.60,
        "reserve": 0.40,
        "existing_position": "HOLD",
    },

    # --------------------------------------------------------
    # ORANGE
    # Deterioração confirmada em múltiplas dimensões.
    # --------------------------------------------------------

    REGIME_ORANGE: {
        "equity": 0.30,
        "reserve": 0.70,
        "existing_position": "HOLD",
    },

    # --------------------------------------------------------
    # RED
    # Stress estrutural + deterioração macro.
    #
    # Mantemos uma parcela de aporte para não depender
    # de acertar exatamente o fundo do mercado.
    # --------------------------------------------------------

    REGIME_RED: {
        "equity": 0.20,
        "reserve": 0.80,
        "existing_position": "HOLD",
    },

    # --------------------------------------------------------
    # BLUE
    # Drawdown estrutural sem deterioração macro ampla.
    #
    # Novo aporte volta integralmente ao S&P 500.
    # A reserva acumulada pode ser liberada gradualmente.
    # --------------------------------------------------------

    REGIME_BLUE: {
        "equity": 1.00,
        "reserve": 0.00,
        "existing_position": "HOLD_ACCUMULATE",
    },

    # --------------------------------------------------------
    # NEUTRAL
    # Evidência inconclusiva.
    # --------------------------------------------------------

    REGIME_NEUTRAL: {
        "equity": 0.50,
        "reserve": 0.50,
        "existing_position": "HOLD",
    },
}


# ============================================================
# DEPLOY DA RESERVA — ESTUDO FINAL 1977–2026
# ============================================================
#
# Regra validada no estudo de utilização da reserva:
#
# -15% -> 40% da reserva-base do episódio
# -20% -> +30%
# -30% -> +20%
# -35% -> +10%
#
# O drawdown cria o gatilho.
# O regime decide se a tranche pode ser executada.
#
# Se o regime atual for RED_STRUCTURAL_STRESS, a tranche
# fica PENDING e é liberada quando o Atlas deixar RED.
#
# A reserva-base do episódio deve ser congelada no primeiro
# estágio acionado para evitar recalcular percentuais sobre
# um saldo que muda ao longo da queda.
# ============================================================

RESERVE_DEPLOYMENT = {

    -0.15: 0.40,

    -0.20: 0.30,

    -0.30: 0.20,

    -0.35: 0.10,
}

# Ordem explícita dos estágios para o engine.
RESERVE_DEPLOYMENT_STAGES = (

    {
        "stage": 1,
        "drawdown_threshold": -0.15,
        "reserve_fraction": 0.40,
    },

    {
        "stage": 2,
        "drawdown_threshold": -0.20,
        "reserve_fraction": 0.30,
    },

    {
        "stage": 3,
        "drawdown_threshold": -0.30,
        "reserve_fraction": 0.20,
    },

    {
        "stage": 4,
        "drawdown_threshold": -0.35,
        "reserve_fraction": 0.10,
    },
)

# Regra vencedora da comparação:
# WAIT_FOR_NON_RED.
RESERVE_DEPLOYMENT_METHOD = (
    "DRAWDOWN_TRIGGER_PLUS_REGIME_CONFIRMATION"
)

# Enquanto RED, estágio acionado não é perdido:
# ele fica pendente.
RESERVE_BLOCKED_REGIME = REGIME_RED

RESERVE_PENDING_IN_RED = True

# Ao sair de RED, as tranches pendentes podem ser liberadas.
RESERVE_RELEASE_REGIMES = (
    REGIME_BLUE,
    REGIME_ORANGE,
    REGIME_NEUTRAL,
    REGIME_GREEN,
    REGIME_YELLOW,
)

# Encerramento de um episódio de stress.
# Quando o drawdown volta para melhor que -10%, o episódio
# é resetado e os quatro estágios são rearmados.
RESERVE_EPISODE_RESET_DRAWDOWN = -0.10

# Política estrutural do estudo.
RESERVE_SELL_EXISTING_POSITION = False
RESERVE_CAPE_IS_SELL_SIGNAL = False
RESERVE_PREDICT_TOP = False
RESERVE_PREDICT_BOTTOM = False


# ============================================================
# QUALIDADE DOS DADOS
# ============================================================

MAX_MACRO_LAG_MONTHS = 3

MAX_MONETARY_LAG_MONTHS = 2


# ============================================================
# HISTÓRICO
# ============================================================

HISTORY_COLUMNS = [

    "date",

    "sp500",

    "drawdown",

    "momentum_12m",

    "cape",

    "cape_percentile",

    "bull_age_years",

    "bull_return",

    "fed_funds",

    "fed_change_12m",

    "yield_curve",

    "inflation",

    "inflation_change_6m",

    "unemployment",

    "sahm",

    "industrial_production",

    "market_regime",

    "cycle_phase",

    "structural_risk",

    "top_timing",

    "operational_regime",

    # Estado operacional da reserva
    "new_contribution_equity_pct",

    "new_contribution_reserve_pct",

    "reserve_deployment_stage",

    "reserve_deployment_status",

    "reserve_pending_stages",
]


# ============================================================
# RELATÓRIO
# ============================================================

REPORT_SEPARATOR = "=" * 72


# ============================================================
# LOG
# ============================================================

VERBOSE = True
