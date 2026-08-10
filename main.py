# ============================================================
# SP500 CYCLE ATLAS
# main.py
# ============================================================
#
# Fluxo principal:
#
# market_data.py
#      ↓
# cycle_engine.py
#      ↓
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

        "market_regime",
        "cycle_phase",

        "structural_risk",
        "top_timing",

        "operational_regime",

        "valuation_regime",
        "momentum_regime",

        "labor_regime",
        "industrial_regime",

        "inflation_regime",
        "monetary_regime",
        "curve_regime",

    ]

    for field in important_fields:

        if field in current_state:

            print(
                f"{field:28s}: "
                f"{current_state[field]}"
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

    # ========================================================
    # 6. RELATÓRIO
    # ========================================================

    print("")
    print(REPORT_SEPARATOR)
    print("ETAPA 5 — RELATÓRIO")
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
    # 7. MUDANÇA DE REGIME
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
    # 8. ENCERRAMENTO
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
