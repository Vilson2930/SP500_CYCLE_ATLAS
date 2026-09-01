# ============================================================
# SP500 CYCLE ATLAS
# ai_auditor.py
# ============================================================
#
# Auditoria independente por Inteligência Artificial.
#
# IMPORTANTE:
#
# - NÃO classifica o ciclo.
# - NÃO altera o regime do engine.
# - NÃO prevê preço.
# - NÃO prevê topo.
# - NÃO prevê fundo.
# - NÃO altera política de aporte.
# - NÃO altera política de reserva.
#
# Sua função é exclusivamente AUDITAR:
#
# 1. integridade / qualidade dos dados
# 2. coerência das classificações
# 3. coerência do regime operacional
# 4. coerência da política de aporte
# 5. coerência da política de utilização da reserva
# 6. contradições entre evidências
#
# Saída:
#
# data/ai_audit.json
#
# Secret esperado:
#
# NVIDIA_API_KEY
#
# Variável opcional:
#
# AI_AUDIT_MODEL
#
# ============================================================

from __future__ import annotations

import json
import os
import re

from pathlib import Path
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from openai import OpenAI

from settings import (

    # Projeto
    PROJECT_NAME,
    VERSION,

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

    # Regimes
    REGIME_GREEN,
    REGIME_YELLOW,
    REGIME_ORANGE,
    REGIME_RED,
    REGIME_BLUE,
    REGIME_NEUTRAL,

    # Política
    CONTRIBUTION_POLICY,
    DEFAULT_EXISTING_POSITION,

    # Reserva
    RESERVE_DEPLOYMENT,
    RESERVE_BLOCKED_REGIME,
    RESERVE_PENDING_IN_RED,
    RESERVE_EPISODE_RESET_DRAWDOWN,

    RESERVE_SELL_EXISTING_POSITION,
    RESERVE_CAPE_IS_SELL_SIGNAL,
    RESERVE_PREDICT_TOP,
    RESERVE_PREDICT_BOTTOM,
)


# ============================================================
# CAMINHOS
# ============================================================

DATA_DIR = Path("data")

AI_AUDIT_FILE = (
    DATA_DIR
    /
    "ai_audit.json"
)


# ============================================================
# MODELO
# ============================================================

DEFAULT_AI_MODEL = (
    "nvidia/nemotron-3-super-120b-a12b"
)

NVIDIA_BASE_URL = (
    "https://integrate.api.nvidia.com/v1"
)


# ============================================================
# STATUS PERMITIDOS
# ============================================================

VALID_AUDIT_STATUS = {

    "CONFIRMED",

    "CONFIRMED_WITH_WARNINGS",

    "REVIEW_REQUIRED",

    "DATA_INSUFFICIENT",
}


# ============================================================
# UTILITÁRIOS
# ============================================================

def _valid(value) -> bool:

    try:

        return (
            value is not None
            and
            not pd.isna(value)
        )

    except Exception:

        return value is not None


def _safe_float(
    value,
    default=None,
):

    try:

        if not _valid(value):
            return default

        return float(value)

    except Exception:

        return default


def _json_safe(value):

    if isinstance(
        value,
        (
            np.integer,
        ),
    ):

        return int(value)

    if isinstance(
        value,
        (
            np.floating,
        ),
    ):

        if np.isnan(value):
            return None

        return float(value)

    if isinstance(
        value,
        (
            np.bool_,
        ),
    ):

        return bool(value)

    if isinstance(
        value,
        (
            pd.Timestamp,
            datetime,
        ),
    ):

        return value.isoformat()

    if isinstance(
        value,
        dict,
    ):

        return {
            str(k): _json_safe(v)
            for k, v in value.items()
        }

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):

        return [
            _json_safe(v)
            for v in value
        ]

    try:

        if pd.isna(value):
            return None

    except Exception:

        pass

    return value


def _dataframe_to_records(
    dataframe,
):

    if dataframe is None:
        return []

    if not isinstance(
        dataframe,
        pd.DataFrame,
    ):
        return []

    if dataframe.empty:
        return []

    records = (
        dataframe
        .replace(
            {
                np.nan: None,
            }
        )
        .to_dict(
            orient="records"
        )
    )

    return _json_safe(
        records
    )


# ============================================================
# SECRET
# ============================================================

def _get_nvidia_api_key():

    api_key = (
        os.getenv(
            "NVIDIA_API_KEY",
            ""
        )
        .strip()
    )

    if not api_key:

        raise RuntimeError(
            "NVIDIA_API_KEY não encontrada. "
            "Crie o secret NVIDIA_API_KEY no GitHub."
        )

    return api_key


# ============================================================
# MODELO
# ============================================================

def _get_ai_model():

    model = (
        os.getenv(
            "AI_AUDIT_MODEL",
            DEFAULT_AI_MODEL,
        )
        .strip()
    )

    if not model:

        model = DEFAULT_AI_MODEL

    return model


# ============================================================
# REGRAS OFICIAIS DO ATLAS
# ============================================================

def build_atlas_rules() -> dict:

    contribution_policy = {}

    for regime, policy in (
        CONTRIBUTION_POLICY.items()
    ):

        contribution_policy[
            str(regime)
        ] = {

            "equity":
                _safe_float(
                    policy.get(
                        "equity"
                    )
                ),

            "reserve":
                _safe_float(
                    policy.get(
                        "reserve"
                    )
                ),

            "existing_position":
                policy.get(
                    "existing_position",
                    DEFAULT_EXISTING_POSITION,
                ),
        }

    reserve_deployment = {

        str(threshold):
            fraction

        for threshold, fraction
        in RESERVE_DEPLOYMENT.items()
    }

    return {

        "project": {
            "name": PROJECT_NAME,
            "version": VERSION,
        },

        "governance": {

            "classifies_regime":
                True,

            "predicts_price":
                False,

            "predicts_top":
                bool(
                    RESERVE_PREDICT_TOP
                ),

            "predicts_bottom":
                bool(
                    RESERVE_PREDICT_BOTTOM
                ),

            "cape_is_sell_signal":
                bool(
                    RESERVE_CAPE_IS_SELL_SIGNAL
                ),

            "sell_existing_position":
                bool(
                    RESERVE_SELL_EXISTING_POSITION
                ),
        },

        "drawdown": {

            "warning":
                DRAWDOWN_WARNING,

            "structural":
                DRAWDOWN_STRUCTURAL,

            "deep":
                DRAWDOWN_DEEP,

            "severe":
                DRAWDOWN_SEVERE,
        },

        "momentum_12m": {

            "severe_negative":
                MOMENTUM_SEVERE_NEGATIVE,

            "negative":
                MOMENTUM_NEGATIVE,

            "strong":
                MOMENTUM_STRONG,
        },

        "cape": {

            "high":
                CAPE_HIGH,

            "extreme":
                CAPE_EXTREME,

            "ultra_extreme":
                CAPE_ULTRA_EXTREME,

            "percentile_high":
                CAPE_PERCENTILE_HIGH,

            "percentile_extreme":
                CAPE_PERCENTILE_EXTREME,

            "percentile_ultra":
                CAPE_PERCENTILE_ULTRA,
        },

        "sahm": {

            "warning":
                SAHM_WARNING,

            "recession":
                SAHM_RECESSION,
        },

        "industrial": {

            "contraction":
                INDUSTRIAL_CONTRACTION,

            "strong_contraction":
                INDUSTRIAL_STRONG_CONTRACTION,
        },

        "inflation": {

            "high":
                INFLATION_HIGH,

            "reacceleration_level":
                INFLATION_REACCELERATION_LEVEL,

            "acceleration_threshold":
                INFLATION_ACCELERATION_THRESHOLD,
        },

        "fed": {

            "easing":
                FED_EASING_THRESHOLD,

            "tightening":
                FED_TIGHTENING_THRESHOLD,
        },

        "yield_curve": {

            "inverted":
                CURVE_INVERTED,

            "flat_max":
                CURVE_FLAT_MAX,
        },

        "operational_regimes": [

            REGIME_GREEN,
            REGIME_YELLOW,
            REGIME_ORANGE,
            REGIME_RED,
            REGIME_BLUE,
            REGIME_NEUTRAL,
        ],

        "contribution_policy":
            contribution_policy,

        "reserve_policy": {

            "deployment":
                reserve_deployment,

            "blocked_regime":
                RESERVE_BLOCKED_REGIME,

            "pending_in_red":
                RESERVE_PENDING_IN_RED,

            "episode_reset_drawdown":
                RESERVE_EPISODE_RESET_DRAWDOWN,
        },
    }


# ============================================================
# AUDITORIA DETERMINÍSTICA DA POLÍTICA
# ============================================================

def audit_policy_deterministically(
    current_state: dict,
) -> dict:

    regime = (
        current_state.get(
            "operational_regime"
        )
    )

    expected_policy = (
        CONTRIBUTION_POLICY
        .get(
            regime
        )
    )

    if expected_policy is None:

        return {

            "valid":
                False,

            "reason":
                (
                    "Regime operacional não encontrado "
                    "em CONTRIBUTION_POLICY."
                ),

            "expected":
                None,

            "observed":
                None,
        }

    expected_equity = (
        _safe_float(
            expected_policy.get(
                "equity"
            )
        )
    )

    expected_reserve = (
        _safe_float(
            expected_policy.get(
                "reserve"
            )
        )
    )

    observed_equity = (
        _safe_float(
            current_state.get(
                "new_contribution_equity"
            )
        )
    )

    observed_reserve = (
        _safe_float(
            current_state.get(
                "new_contribution_reserve"
            )
        )
    )

    observed_position = (
        current_state.get(
            "existing_position"
        )
    )

    expected_position = (
        expected_policy.get(
            "existing_position",
            DEFAULT_EXISTING_POSITION,
        )
    )

    tolerance = 1e-9

    equity_ok = (
        observed_equity is not None
        and
        abs(
            observed_equity
            -
            expected_equity
        )
        <= tolerance
    )

    reserve_ok = (
        observed_reserve is not None
        and
        abs(
            observed_reserve
            -
            expected_reserve
        )
        <= tolerance
    )

    position_ok = (
        str(observed_position)
        ==
        str(expected_position)
    )

    return {

        "valid":
            bool(
                equity_ok
                and
                reserve_ok
                and
                position_ok
            ),

        "expected": {

            "equity":
                expected_equity,

            "reserve":
                expected_reserve,

            "existing_position":
                expected_position,
        },

        "observed": {

            "equity":
                observed_equity,

            "reserve":
                observed_reserve,

            "existing_position":
                observed_position,
        },

        "equity_ok":
            equity_ok,

        "reserve_ok":
            reserve_ok,

        "position_ok":
            position_ok,
    }


# ============================================================
# PAYLOAD
# ============================================================

def build_audit_payload(
    current_state: dict,
    scorecard=None,
    freshness_audit=None,
) -> dict:

    return {

        "atlas_rules":
            build_atlas_rules(),

        "current_state":
            _json_safe(
                current_state
            ),

        "evidence_scorecard":
            _dataframe_to_records(
                scorecard
            ),

        "freshness_audit":
            _dataframe_to_records(
                freshness_audit
            ),

        "deterministic_policy_check":
            audit_policy_deterministically(
                current_state
            ),
    }


# ============================================================
# SYSTEM PROMPT
# ============================================================

def build_system_prompt() -> str:

    return """
Você é o AUDITOR INDEPENDENTE do SP500 CYCLE ATLAS.

Sua função NÃO é analisar o mercado livremente.
Sua função NÃO é substituir o motor quantitativo.
Sua função NÃO é criar uma segunda estratégia.

Você deve exclusivamente AUDITAR a consistência interna
da conclusão produzida pelo SP500 CYCLE ATLAS.

REGRAS INVIOLÁVEIS:

1. NÃO prever preço futuro do S&P 500.
2. NÃO prever topo.
3. NÃO prever fundo.
4. NÃO recomendar venda da posição estrutural.
5. NÃO transformar CAPE isoladamente em sinal de venda.
6. NÃO alterar thresholds fornecidos.
7. NÃO alterar política de aporte.
8. NÃO alterar política de reserva.
9. NÃO substituir o regime operacional calculado pelo engine.
10. NÃO criar dados que não foram fornecidos.
11. NÃO usar conhecimento externo para sobrescrever o motor.
12. NÃO inventar probabilidades.
13. NÃO apresentar retorno esperado futuro.
14. NÃO emitir recomendação de compra ou venda fora da política do Atlas.

Você deve verificar:

A. DATA INTEGRITY
- dados ausentes;
- dados potencialmente defasados;
- campos UNKNOWN;
- inconsistências aparentes.

B. RULE CONSISTENCY
- verificar se classificações e resultados são compatíveis
  com as regras fornecidas.

C. REGIME CONSISTENCY
- verificar se o regime operacional é logicamente compatível
  com as evidências entregues.

D. POLICY CONSISTENCY
- verificar se equity/reserve/existing_position correspondem
  exatamente à política do regime.

E. RESERVE CONSISTENCY
- verificar estágio, status e bloqueio da reserva.

F. CROSS-EVIDENCE CONSISTENCY
- identificar contradições materiais entre valuation,
  momentum, drawdown, trabalho, produção industrial,
  inflação, política monetária, curva de juros,
  fase do ciclo, risco estrutural e timing de topo.

A divergência da IA NÃO muda o regime.
Ela apenas indica necessidade de revisão humana.

STATUS PERMITIDOS:

CONFIRMED
CONFIRMED_WITH_WARNINGS
REVIEW_REQUIRED
DATA_INSUFFICIENT

REGRAS PARA STATUS:

CONFIRMED:
nenhuma inconsistência material.

CONFIRMED_WITH_WARNINGS:
regime permanece coerente, porém há alertas relevantes.

REVIEW_REQUIRED:
há inconsistência material entre regras, evidências,
política ou conclusão do motor.

DATA_INSUFFICIENT:
os dados fornecidos são insuficientes para uma auditoria confiável.

Você deve devolver SOMENTE JSON válido.
Nenhum markdown.
Nenhum texto antes ou depois do JSON.

Use exatamente esta estrutura:

{
  "audit_status": "CONFIRMED",
  "engine_consistency_score": 0,
  "data_quality_score": 0,
  "ai_dissent": false,
  "regime_audit": {
    "engine_regime": "",
    "assessment": "",
    "reason": ""
  },
  "data_integrity": {
    "assessment": "",
    "issues": []
  },
  "rule_consistency": {
    "assessment": "",
    "issues": []
  },
  "policy_consistency": {
    "assessment": "",
    "issues": []
  },
  "reserve_consistency": {
    "assessment": "",
    "issues": []
  },
  "cross_evidence": {
    "assessment": "",
    "contradictions": []
  },
  "warnings": [],
  "strengths": [],
  "manual_review_points": [],
  "final_opinion": ""
}

REGRAS DOS SCORES:

engine_consistency_score:
0 a 100.

data_quality_score:
0 a 100.

Nunca use score acima de 100 ou abaixo de 0.

O campo final_opinion deve ser objetivo,
profissional e limitado a aproximadamente 120 palavras.

Não repita todo o relatório.
Não produza análise genérica.
Concentre-se exclusivamente na auditoria.
""".strip()


# ============================================================
# EXTRAÇÃO DE JSON
# ============================================================

def _extract_json(
    text: str,
) -> dict:

    if not text:

        raise RuntimeError(
            "Resposta vazia da IA."
        )

    text = (
        text
        .strip()
    )

    # --------------------------------------------------------
    # Caso perfeito
    # --------------------------------------------------------

    try:

        return json.loads(
            text
        )

    except Exception:
        pass

    # --------------------------------------------------------
    # Remove bloco ```json
    # --------------------------------------------------------

    cleaned = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    cleaned = re.sub(
        r"^```\s*",
        "",
        cleaned,
    )

    cleaned = re.sub(
        r"\s*```$",
        "",
        cleaned,
    )

    try:

        return json.loads(
            cleaned
        )

    except Exception:
        pass

    # --------------------------------------------------------
    # Extrair primeiro objeto JSON
    # --------------------------------------------------------

    start = (
        cleaned.find(
            "{"
        )
    )

    end = (
        cleaned.rfind(
            "}"
        )
    )

    if (
        start >= 0
        and
        end > start
    ):

        candidate = (
            cleaned[
                start:
                end + 1
            ]
        )

        try:

            return json.loads(
                candidate
            )

        except Exception as error:

            raise RuntimeError(
                "A IA retornou conteúdo que parece JSON, "
                f"mas não pôde ser interpretado: {error}"
            ) from error

    raise RuntimeError(
        "Nenhum JSON válido encontrado "
        "na resposta da IA."
    )


# ============================================================
# VALIDAÇÃO DA RESPOSTA
# ============================================================

def validate_ai_audit(
    audit: dict,
    current_state: dict,
) -> dict:

    if not isinstance(
        audit,
        dict,
    ):

        raise RuntimeError(
            "Auditoria IA não é um objeto JSON."
        )

    status = (
        str(
            audit.get(
                "audit_status",
                ""
            )
        )
        .strip()
        .upper()
    )

    if status not in VALID_AUDIT_STATUS:

        raise RuntimeError(
            "audit_status inválido: "
            f"{status}"
        )

    audit[
        "audit_status"
    ] = status

    # --------------------------------------------------------
    # Score consistência
    # --------------------------------------------------------

    engine_score = (
        _safe_float(
            audit.get(
                "engine_consistency_score"
            ),
            0,
        )
    )

    engine_score = max(
        0,
        min(
            100,
            engine_score,
        )
    )

    audit[
        "engine_consistency_score"
    ] = round(
        engine_score,
        1,
    )

    # --------------------------------------------------------
    # Score dados
    # --------------------------------------------------------

    data_score = (
        _safe_float(
            audit.get(
                "data_quality_score"
            ),
            0,
        )
    )

    data_score = max(
        0,
        min(
            100,
            data_score,
        )
    )

    audit[
        "data_quality_score"
    ] = round(
        data_score,
        1,
    )

    # --------------------------------------------------------
    # Dissent
    # --------------------------------------------------------

    audit[
        "ai_dissent"
    ] = bool(
        audit.get(
            "ai_dissent",
            False,
        )
    )

    # --------------------------------------------------------
    # Regime deve continuar sendo o regime do engine
    # --------------------------------------------------------

    engine_regime = (
        current_state.get(
            "operational_regime"
        )
    )

    regime_audit = (
        audit.get(
            "regime_audit"
        )
    )

    if not isinstance(
        regime_audit,
        dict,
    ):

        regime_audit = {}

    regime_audit[
        "engine_regime"
    ] = engine_regime

    audit[
        "regime_audit"
    ] = regime_audit

    # --------------------------------------------------------
    # Garantir listas
    # --------------------------------------------------------

    list_fields = [

        "warnings",
        "strengths",
        "manual_review_points",
    ]

    for field in list_fields:

        value = (
            audit.get(
                field
            )
        )

        if not isinstance(
            value,
            list,
        ):

            audit[
                field
            ] = []

    nested_list_fields = {

        "data_integrity":
            "issues",

        "rule_consistency":
            "issues",

        "policy_consistency":
            "issues",

        "reserve_consistency":
            "issues",

        "cross_evidence":
            "contradictions",
    }

    for section, field in (
        nested_list_fields.items()
    ):

        section_value = (
            audit.get(
                section
            )
        )

        if not isinstance(
            section_value,
            dict,
        ):

            section_value = {}

        if not isinstance(
            section_value.get(
                field
            ),
            list,
        ):

            section_value[
                field
            ] = []

        audit[
            section
        ] = section_value

    return audit


# ============================================================
# FALLBACK
# ============================================================

def build_fallback_audit(
    current_state: dict,
    error,
) -> dict:

    regime = (
        current_state.get(
            "operational_regime",
            "UNKNOWN",
        )
    )

    return {

        "audit_status":
            "DATA_INSUFFICIENT",

        "engine_consistency_score":
            0,

        "data_quality_score":
            0,

        "ai_dissent":
            False,

        "regime_audit": {

            "engine_regime":
                regime,

            "assessment":
                "AUDITORIA IA INDISPONÍVEL",

            "reason":
                (
                    "O motor quantitativo foi preservado, "
                    "mas a camada independente de IA "
                    "não conseguiu concluir a auditoria."
                ),
        },

        "data_integrity": {

            "assessment":
                "NÃO AUDITADO",

            "issues": [],
        },

        "rule_consistency": {

            "assessment":
                "NÃO AUDITADO",

            "issues": [],
        },

        "policy_consistency": {

            "assessment":
                "NÃO AUDITADO",

            "issues": [],
        },

        "reserve_consistency": {

            "assessment":
                "NÃO AUDITADO",

            "issues": [],
        },

        "cross_evidence": {

            "assessment":
                "NÃO AUDITADO",

            "contradictions": [],
        },

        "warnings": [

            (
                "Falha na camada de auditoria por IA. "
                "A conclusão original do Cycle Atlas "
                "não foi alterada."
            )
        ],

        "strengths": [],

        "manual_review_points": [

            "Verificar disponibilidade da API de IA."
        ],

        "final_opinion":
            (
                "A auditoria independente por IA não pôde ser "
                "concluída nesta execução. O resultado quantitativo "
                "original do SP500 Cycle Atlas permanece intacto "
                "e deve ser interpretado sem validação adicional "
                "da camada de IA."
            ),

        "audit_error":
            (
                f"{type(error).__name__}: "
                f"{error}"
            ),
    }


# ============================================================
# SALVAR
# ============================================================

def save_ai_audit(
    audit: dict,
    model: str,
) -> Path:

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = {

        "generated_at":
            datetime.now().isoformat(),

        "model":
            model,

        "audit":
            _json_safe(
                audit
            ),
    }

    AI_AUDIT_FILE.write_text(

        json.dumps(
            output,
            ensure_ascii=False,
            indent=2,
        ),

        encoding="utf-8",
    )

    return AI_AUDIT_FILE


# ============================================================
# AUDITORIA PRINCIPAL
# ============================================================

def run_ai_audit(
    current_state: dict,
    scorecard=None,
    freshness_audit=None,
    fail_safe: bool = True,
) -> dict:

    print("")
    print("=" * 72)
    print(
        "SP500 CYCLE ATLAS — AUDITORIA NVIDIA NEMOTRON"
    )
    print("=" * 72)

    model = (
        _get_ai_model()
    )

    print(
        f"Modelo: {model}"
    )

    payload = (
        build_audit_payload(
            current_state=current_state,
            scorecard=scorecard,
            freshness_audit=freshness_audit,
        )
    )

    try:

        api_key = (
            _get_nvidia_api_key()
        )

        client = OpenAI(
            base_url=NVIDIA_BASE_URL,
            api_key=api_key,
        )

        print(
            "→ Enviando estado do Atlas para NVIDIA Nemotron..."
        )

        completion = (
            client.chat.completions.create(

                model=model,

                messages=[

                    {
                        "role":
                            "system",

                        "content":
                            build_system_prompt(),
                    },

                    {
                        "role":
                            "user",

                        "content":
                            (
                                "Audite a execução atual do "
                                "SP500 CYCLE ATLAS.\n\n"
                                "DADOS E REGRAS:\n"
                                +
                                json.dumps(
                                    payload,
                                    ensure_ascii=False,
                                    indent=2,
                                )
                            ),
                    },
                ],

                temperature=1.0,

                top_p=0.95,

                max_tokens=8192,

                extra_body={
                    "chat_template_kwargs": {
                        "enable_thinking": True
                    },
                    "reasoning_budget": 4096,
                },

                stream=False,
            )
        )

        raw_text = (
            completion
            .choices[0]
            .message
            .content
        )

        audit = (
            _extract_json(
                raw_text
            )
        )

        audit = (
            validate_ai_audit(
                audit=audit,
                current_state=current_state,
            )
        )

        output_path = (
            save_ai_audit(
                audit=audit,
                model=model,
            )
        )

        print("")
        print(
            "✅ Auditoria NVIDIA concluída."
        )

        print(
            f"Status: "
            f"{audit.get('audit_status')}"
        )

        print(
            f"Consistência: "
            f"{audit.get('engine_consistency_score')}/100"
        )

        print(
            f"Qualidade dos dados: "
            f"{audit.get('data_quality_score')}/100"
        )

        print(
            f"Divergência IA: "
            f"{audit.get('ai_dissent')}"
        )

        print(
            f"Arquivo: {output_path}"
        )

        return audit

    except Exception as error:

        print("")
        print(
            "⚠️ Falha na auditoria NVIDIA."
        )

        print(
            f"{type(error).__name__}: "
            f"{error}"
        )

        if not fail_safe:

            raise

        print(
            "→ Fail-safe ativado."
        )

        print(
            "→ O regime original do Atlas será preservado."
        )

        fallback = (
            build_fallback_audit(
                current_state=current_state,
                error=error,
            )
        )

        output_path = (
            save_ai_audit(
                audit=fallback,
                model=model,
            )
        )

        print(
            f"→ Fallback salvo em: "
            f"{output_path}"
        )

        return fallback


# ============================================================
# EXECUÇÃO DIRETA
# ============================================================

if __name__ == "__main__":

    raise RuntimeError(
        "ai_auditor.py não deve ser executado isoladamente. "
        "Ele deve ser chamado pelo main.py após o cycle_engine."
    )
