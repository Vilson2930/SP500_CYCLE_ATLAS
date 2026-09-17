# ============================================================
# SP500 CYCLE ATLAS
# agent_export.py
# ============================================================
#
# Exporta o resultado institucional do Atlas para consumo
# externo pelo INVESTMENT CIO AGENT.
#
# NÃO recalcula indicadores.
# NÃO altera decisões do Atlas.
#
# ============================================================

import json
from pathlib import Path
from datetime import datetime, timezone


OUTPUT_DIR = Path("outputs")
OUTPUT_FILE = OUTPUT_DIR / "agent_output_raw.json"


def _json_safe(value):

    if value is None:
        return None

    # Tipos simples já compatíveis com JSON
    if isinstance(
        value,
        (str, int, float, bool)
    ):
        return value

    # Datas / timestamps
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass

    # Tipos NumPy / Pandas escalares
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass

    return str(value)


def export_agent_output(
    current_state,
    ai_audit
):

    if not isinstance(current_state, dict):
        raise TypeError(
            "current_state deve ser um dicionário."
        )

    if not isinstance(ai_audit, dict):
        ai_audit = {}

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    state = {
        key: _json_safe(value)
        for key, value in current_state.items()
    }

    audit = {
        key: _json_safe(value)
        for key, value in ai_audit.items()
    }

    payload = {

        "source_system": "SP500_CYCLE_ATLAS",

        "export_version": "1.0",

        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "current_state": state,

        "ai_audit": audit
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            payload,
            file,
            ensure_ascii=False,
            indent=2
        )

    return str(OUTPUT_FILE)
