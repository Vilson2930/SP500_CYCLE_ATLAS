# ============================================================
# SP500 CYCLE ATLAS
# main.py
# ============================================================
#
# Fluxo principal:
#
# market_data.py
# ↓
# cycle_engine.py
# ↓
# ai_auditor.py
# ↓
# report.py
#
# ============================================================

import sys
import traceback
from datetime import datetime

from market_data import (
    build_master_dataset,
    freshness_audit,
)

from cycle_engine import (
    run_cycle_engine,
    get_current_cycle_state,
    build_evidence_scorecard,
)

from report import (
    generate_report,
)

from ai_auditor import (
    run_ai_audit,
)

from settings import (
    PROJECT_NAME,
    VERSION,
    REPORT_SEPARATOR,
)


def main():

    print(REPORT_SEPARATOR)
    print(PROJECT_NAME)
    print(f"Versão: {VERSION}")
    print(REPORT_SEPARATOR)

    print(
        f"Início da execução: "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    # ========================================================
    # 1. DADOS
    # ========================================================

    print("")
    print(REPORT_SEPARATOR)
    print("ETAPA 1 — COLETA DE DADOS")
    print(REPORT_SEPARATOR)

    master = build_master_dataset()

    if master is None or master.empty:
        raise RuntimeError(
            "Master dataset vazio."
        )

    # ========================================================
    # 2. AUDITORIA DE FRESCOR
    # ========================================================

    print("")
    print(REPORT_SEPARATOR)
    print("ETAPA 2 — AUDITORIA DE FRESCOR")
    print(REPORT_SEPARATOR)

    audit = freshness_audit(
        master
    )

    if audit is not None and not audit.empty:

        print(
            audit.to_string(
                index=False
            )
        )

    else:

        print(
            "⚠️ Auditoria de frescor indisponível."
        )

    # ========================================================
    # 3. ENGINE
    # ========================================================

    print("")
    print(REPORT_SEPARATOR)
    print("ETAPA 3 — CLASSIFICAÇÃO DO CICLO")
    print(REPORT_SEPARATOR)

    classified = run_cycle_engine(
        master
    )

    if classified is None or classified.empty:
        raise RuntimeError(
            "Cycle engine retornou dataset vazio."
        )

    # ========================================================
    # 4. ESTADO ATUAL
    # ========================================================

    current_state = (
        get_current_cycle_state(
            classified
        )
    )

    print("")
    print("Estado atual detectado:")

    important_fields = [

        "date",
        "sp500",
        "drawdown",

        # Diagnóstico CAPE
        "cape",
        "cape_percentile",
        "valuation_regime",

        "market_regime",
        "cycle_phase",

        "structural_risk",
        "top_timing",

        "operational_regime",

        "momentum_regime",

        "labor_regime",
        "industrial_regime",

        "inflation_regime",
        "monetary_regime",
        "curve_regime",

        # Política de aporte
        "existing_position",
        "new_contribution_equity",
        "new_contribution_reserve",

        # Estudo da reserva
        "reserve_stage",
        "reserve_stage_fraction",
        "reserve_cumulative_fraction",
        "reserve_deployment_status",
        "reserve_pending",
        "reserve_blocked_by_regime",
    ]

    for field in important_fields:

        if field in current_state:

            print(
                f"{field:32s}: "
                f"{current_state[field]}"
            )

    # ========================================================
    # 4B. DIAGNÓSTICO CAPE
    # ========================================================

    print("")
    print(REPORT_SEPARATOR)
    print("DIAGNÓSTICO CAPE")
    print(REPORT_SEPARATOR)

    cape_value = (
        current_state.get(
            "cape"
        )
    )

    cape_percentile = (
        current_state.get(
            "cape_percentile"
        )
    )

    valuation_regime = (
        current_state.get(
            "valuation_regime"
        )
    )

    print(
        f"CAPE bruto                 : "
        f"{cape_value!r}"
    )

    print(
        f"CAPE percentile bruto      : "
        f"{cape_percentile!r}"
    )

    if cape_percentile is not None:

        try:

            cape_percentile_float = float(
                cape_percentile
            )

            print(
                f"CAPE percentile 8 casas    : "
                f"{cape_percentile_float:.8f}"
            )

            if cape_percentile_float <= 1.0:

                print(
                    f"CAPE percentile em %        : "
                    f"{cape_percentile_float * 100:.6f}%"
                )

            else:

                print(
                    f"CAPE percentile em %        : "
                    f"{cape_percentile_float:.6f}%"
                )

        except Exception:

            print(
                "CAPE percentile formatado   : "
                "indisponível"
            )

    print(
        f"Valuation classificado     : "
        f"{valuation_regime}"
    )

    # ========================================================
    # 5. SCORECARD
    # ========================================================

    print("")
    print(REPORT_SEPARATOR)
    print("ETAPA 4 — EVIDENCE SCORECARD")
    print(REPORT_SEPARATOR)

    scorecard = (
        build_evidence_scorecard(
            current_state
        )
    )

    if scorecard is not None and not scorecard.empty:

        print(
            scorecard.to_string(
                index=False
            )
        )

    else:

        print(
            "⚠️ Evidence scorecard indisponível."
        )

    # ========================================================
    # 6. AUDITORIA INDEPENDENTE POR IA
    # ========================================================

    print("")
    print(REPORT_SEPARATOR)
    print("ETAPA 5 — AUDITORIA NVIDIA NEMOTRON")
    print(REPORT_SEPARATOR)

    ai_audit = (
        run_ai_audit(
            current_state=current_state,
            scorecard=scorecard,
            freshness_audit=audit,
            fail_safe=True,
        )
    )

    print("")
    print(
        f"Status auditoria IA        : "
        f"{ai_audit.get('audit_status')}"
    )

    print(
        f"Consistência do engine     : "
        f"{ai_audit.get('engine_consistency_score')}/100"
    )

    print(
        f"Qualidade dos dados        : "
        f"{ai_audit.get('data_quality_score')}/100"
    )

    print(
        f"Divergência da IA          : "
        f"{ai_audit.get('ai_dissent')}"
    )

    # ========================================================
    # 7. RELATÓRIO
    # ========================================================

    print("")
    print(REPORT_SEPARATOR)
    print("ETAPA 6 — RELATÓRIO")
    print(REPORT_SEPARATOR)

    report_result = (
        generate_report(
            current_state=current_state,
            scorecard=scorecard,
        )
    )

    print("")
    print(
        report_result[
            "report_text"
        ]
    )

    # ========================================================
    # 8. MUDANÇA DE REGIME
    # ========================================================

    regime_change = (
        report_result.get(
            "regime_change"
        )
    )

    if regime_change:

        if regime_change.get(
            "changed"
        ):

            print("")
            print(REPORT_SEPARATOR)
            print("⚠️ ALERTA — MUDANÇA DE REGIME")
            print(REPORT_SEPARATOR)

            print(
                f"{regime_change.get('previous')} "
                f"→ "
                f"{regime_change.get('current')}"
            )

    # ========================================================
    # 9. PAINEL OPERACIONAL DA RESERVA
    # ========================================================

    print("")
    print(REPORT_SEPARATOR)
    print("PAINEL OPERACIONAL DA RESERVA")
    print(REPORT_SEPARATOR)

    contribution_equity = (
        current_state.get(
            "new_contribution_equity"
        )
    )

    contribution_reserve = (
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

    reserve_status = (
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

    print(
        f"Regime operacional        : "
        f"{current_state.get('operational_regime')}"
    )

    print(
        f"Posição existente         : "
        f"{current_state.get('existing_position')}"
    )

    if contribution_equity is not None:

        print(
            f"Novo aporte S&P           : "
            f"{float(contribution_equity) * 100:.0f}%"
        )

    if contribution_reserve is not None:

        print(
            f"Nova reserva              : "
            f"{float(contribution_reserve) * 100:.0f}%"
        )

    print(
        f"Estágio de deployment     : "
        f"{reserve_stage}"
    )

    if reserve_stage and reserve_stage_fraction is not None:

        print(
            f"Tranche do estágio        : "
            f"{float(reserve_stage_fraction) * 100:.0f}%"
        )

        print(
            f"Tranche acumulada         : "
            f"{float(reserve_cumulative_fraction) * 100:.0f}%"
        )

    print(
        f"Status da reserva         : "
        f"{reserve_status}"
    )

    if reserve_pending:

        print(
            "Ação operacional          : "
            "manter tranche(s) pendente(s) até sair de RED."
        )

    elif reserve_status == "DEPLOYMENT_ALLOWED":

        print(
            "Ação operacional          : "
            "deployment permitido conforme política 40/30/20/10."
        )

    else:

        print(
            "Ação operacional          : "
            "continuar formando reserva conforme o regime."
        )

    # ========================================================
    # 10. ENCERRAMENTO
    # ========================================================

    print("")
    print(REPORT_SEPARATOR)
    print("EXECUÇÃO CONCLUÍDA")
    print(REPORT_SEPARATOR)

    print(
        f"Regime atual: "
        f"{current_state.get('operational_regime')}"
    )

    print(
        f"Fase do ciclo: "
        f"{current_state.get('cycle_phase')}"
    )

    print(
        f"Risco estrutural: "
        f"{current_state.get('structural_risk')}"
    )

    print(
        f"Timing de topo: "
        f"{current_state.get('top_timing')}"
    )

    print(
        f"Status da reserva: "
        f"{current_state.get('reserve_deployment_status', 'NOT_ACTIVE')}"
    )

    print("")
    print(
        "✅ SP500 CYCLE ATLAS executado com sucesso."
    )

    return 0


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":

    try:

        exit_code = main()

        sys.exit(
            exit_code
        )

    except Exception as error:

        print("")
        print(REPORT_SEPARATOR)
        print("❌ ERRO NA EXECUÇÃO")
        print(REPORT_SEPARATOR)

        print(
            f"{type(error).__name__}: "
            f"{error}"
        )

        print("")
        print("TRACEBACK:")
        print("")

        traceback.print_exc()

        sys.exit(1)
