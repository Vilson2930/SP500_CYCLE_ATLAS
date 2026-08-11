# ============================================================
# SP500 CYCLE ATLAS
# market_data.py
# ============================================================
#
# Responsável por:
#
# - S&P 500 via Yahoo Finance
# - CAPE via Robert J. Shiller
# - séries macroeconômicas via FRED
# - padronização mensal
# - cálculo das features básicas
# - auditoria de frescor
#
# IMPORTANTE:
# Este módulo NÃO classifica o ciclo.
# A classificação pertence ao cycle_engine.py.
# ============================================================

from __future__ import annotations

import io
import os
import re
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict

import numpy as np
import pandas as pd
import requests
import yfinance as yf

from settings import (
    SP500_TICKER,
    MARKET_START_DATE,
    SHILLER_URLS,
    FRED_SERIES,
    FRED_START_DATE,
)

warnings.filterwarnings("ignore")


# ============================================================
# CONFIGURAÇÕES DE REDE
# ============================================================

CONNECT_TIMEOUT = 10
READ_TIMEOUT = 20
SHILLER_READ_TIMEOUT = 25
HTTP_RETRIES = 2

# Yahoo Finance é uma fonte pública sujeita a falhas temporárias,
# rate-limit e respostas vazias em runners do GitHub Actions.
YAHOO_RETRIES = 3
YAHOO_RETRY_WAIT_SECONDS = 5
YAHOO_FALLBACK_RETRIES = 2


# ============================================================
# UTILITÁRIOS
# ============================================================

def _print(message: str = ""):
    """
    Print sem buffer.

    Fundamental para visualizar imediatamente
    em qual etapa o GitHub Actions está.
    """

    print(
        message,
        flush=True,
    )


def _safe_numeric(series):
    return pd.to_numeric(
        series,
        errors="coerce",
    )


def _http_get(
    url: str,
    read_timeout: int = READ_TIMEOUT,
):
    """
    GET com timeout e número limitado de tentativas.

    Evita deixar o GitHub Actions preso indefinidamente.
    """

    last_error = None

    headers = {
        "User-Agent":
            "Mozilla/5.0 "
            "(compatible; SP500-Cycle-Atlas/1.0)"
    }

    for attempt in range(
        1,
        HTTP_RETRIES + 1,
    ):

        try:

            _print(
                f"   tentativa {attempt}/{HTTP_RETRIES}"
            )

            response = requests.get(
                url,
                timeout=(
                    CONNECT_TIMEOUT,
                    read_timeout,
                ),
                headers=headers,
            )

            response.raise_for_status()

            return response

        except Exception as error:

            last_error = error

            _print(
                f"   ⚠️ {type(error).__name__}: "
                f"{error}"
            )

            if attempt < HTTP_RETRIES:
                time.sleep(1)

    raise RuntimeError(
        f"Falha após {HTTP_RETRIES} tentativas. "
        f"Último erro: {last_error}"
    )


# ============================================================
# S&P 500
# ============================================================

def download_sp500() -> pd.DataFrame:

    _print("")
    _print("=" * 80)
    _print("BAIXANDO S&P 500 — YAHOO FINANCE")
    _print("=" * 80)

    _print(f"Ticker: {SP500_TICKER}")
    _print(f"Início histórico: {MARKET_START_DATE}")

    # --------------------------------------------------------
    # TENTATIVA PRINCIPAL — yf.download
    # --------------------------------------------------------

    data = None
    last_error = None

    for attempt in range(1, YAHOO_RETRIES + 1):

        try:

            _print(
                f"→ Yahoo Finance | tentativa "
                f"{attempt}/{YAHOO_RETRIES}"
            )

            candidate = yf.download(
                SP500_TICKER,
                start=MARKET_START_DATE,
                auto_adjust=False,
                progress=False,
                threads=False,
                timeout=20,
            )

            if candidate is None or candidate.empty:
                raise RuntimeError(
                    "Yahoo Finance retornou dataset vazio."
                )

            data = candidate

            _print(
                "✅ Resposta válida recebida via yf.download."
            )

            break

        except Exception as error:

            last_error = error

            _print(
                f"⚠️ Yahoo tentativa {attempt}/{YAHOO_RETRIES} | "
                f"{type(error).__name__}: {error}"
            )

            if attempt < YAHOO_RETRIES:

                _print(
                    f"→ Aguardando "
                    f"{YAHOO_RETRY_WAIT_SECONDS}s antes de tentar novamente..."
                )

                time.sleep(
                    YAHOO_RETRY_WAIT_SECONDS
                )

    # --------------------------------------------------------
    # FALLBACK — Ticker.history
    # --------------------------------------------------------

    if data is None or data.empty:

        _print("")
        _print(
            "⚠️ yf.download não retornou dados válidos."
        )
        _print(
            "→ Ativando fallback Yahoo via Ticker.history..."
        )

        for attempt in range(1, YAHOO_FALLBACK_RETRIES + 1):

            try:

                _print(
                    f"→ Yahoo fallback | tentativa "
                    f"{attempt}/{YAHOO_FALLBACK_RETRIES}"
                )

                ticker = yf.Ticker(
                    SP500_TICKER
                )

                candidate = ticker.history(
                    start=MARKET_START_DATE,
                    auto_adjust=False,
                    actions=False,
                )

                if candidate is None or candidate.empty:
                    raise RuntimeError(
                        "Ticker.history retornou dataset vazio."
                    )

                data = candidate

                _print(
                    "✅ Resposta válida recebida via Ticker.history."
                )

                break

            except Exception as error:

                last_error = error

                _print(
                    f"⚠️ Yahoo fallback "
                    f"{attempt}/{YAHOO_FALLBACK_RETRIES} | "
                    f"{type(error).__name__}: {error}"
                )

                if attempt < YAHOO_FALLBACK_RETRIES:

                    _print(
                        f"→ Aguardando "
                        f"{YAHOO_RETRY_WAIT_SECONDS}s antes do novo fallback..."
                    )

                    time.sleep(
                        YAHOO_RETRY_WAIT_SECONDS
                    )

    # --------------------------------------------------------
    # FALHA FINAL
    # --------------------------------------------------------

    if data is None or data.empty:

        raise RuntimeError(
            "Não foi possível obter o histórico do S&P 500 "
            "após múltiplas tentativas no Yahoo Finance. "
            f"Último erro: {last_error}"
        )

    # --------------------------------------------------------
    # Corrigir MultiIndex do yfinance
    # --------------------------------------------------------

    if isinstance(data.columns, pd.MultiIndex):

        try:
            close = data["Close"][SP500_TICKER]
        except Exception:
            close = data["Close"].iloc[:, 0]

    else:

        if "Close" not in data.columns:
            raise RuntimeError(
                "Coluna Close não encontrada nos dados do Yahoo."
            )

        close = data["Close"]

    # --------------------------------------------------------
    # DataFrame diário
    # --------------------------------------------------------

    close_values = np.asarray(
        close
    ).reshape(-1)

    df = pd.DataFrame({
        "date": pd.to_datetime(close.index),
        "sp500": pd.to_numeric(
            close_values,
            errors="coerce",
        ),
    })

    # Ticker.history pode trazer timezone; o Atlas trabalha sem timezone.
    if getattr(df["date"].dt, "tz", None) is not None:
        df["date"] = df["date"].dt.tz_localize(None)

    df = (
        df
        .dropna(subset=["date", "sp500"])
        .sort_values("date")
        .drop_duplicates(subset="date", keep="last")
        .reset_index(drop=True)
    )

    if df.empty:
        raise RuntimeError(
            "S&P 500 ficou vazio após limpeza."
        )

    # --------------------------------------------------------
    # Validação mínima de sanidade
    # --------------------------------------------------------

    if len(df) < 1000:
        raise RuntimeError(
            "Histórico do S&P 500 retornou poucas observações "
            f"({len(df):,})."
        )

    if (
        not np.isfinite(df["sp500"].iloc[-1])
        or df["sp500"].iloc[-1] <= 0
    ):
        raise RuntimeError(
            "Último fechamento do S&P 500 é inválido."
        )

    # --------------------------------------------------------
    # Mensal
    # --------------------------------------------------------

    df = (
        df
        .set_index("date")
        .resample("MS")
        .last()
        .dropna()
        .reset_index()
    )

    _print(
        f"✅ S&P 500: "
        f"{df['date'].min().date()} "
        f"→ "
        f"{df['date'].max().date()}"
    )

    _print(
        f"✅ Observações mensais: {len(df):,}"
    )

    _print(
        f"✅ Último fechamento: "
        f"{df['sp500'].iloc[-1]:,.2f}"
    )

    return df


# ============================================================
# FRED — API OFICIAL
# ============================================================

FRED_API_URL = "https://api.stlouisfed.org/fred/series/observations"


def _get_fred_api_key() -> str:
    """
    Obtém a chave FRED da variável de ambiente FRED_API_KEY.
    """

    api_key = os.getenv("FRED_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError(
            "FRED_API_KEY não encontrada. "
            "Crie o secret FRED_API_KEY no GitHub e exponha-o "
            "na etapa 'Run SP500 Cycle Atlas'."
        )

    return api_key


def download_fred_series(
    series_id: str,
    name: str,
) -> pd.DataFrame:
    """
    Baixa uma série pela API oficial do FRED.
    """

    api_key = _get_fred_api_key()

    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": FRED_START_DATE,
    }

    headers = {
        "User-Agent": "SP500-Cycle-Atlas/1.0"
    }

    last_error = None

    for attempt in range(1, HTTP_RETRIES + 1):

        try:
            _print(
                f"→ {name} [{series_id}] | "
                f"tentativa {attempt}/{HTTP_RETRIES}"
            )

            response = requests.get(
                FRED_API_URL,
                params=params,
                timeout=(CONNECT_TIMEOUT, 30),
                headers=headers,
            )

            response.raise_for_status()
            payload = response.json()
            observations = payload.get("observations", [])

            if not observations:
                raise RuntimeError(
                    f"FRED não retornou observações para {series_id}."
                )

            df = pd.DataFrame(observations)

            if "date" not in df.columns or "value" not in df.columns:
                raise RuntimeError(
                    f"Resposta FRED inválida para {series_id}."
                )

            df = df[["date", "value"]].copy()
            df = df.rename(columns={"value": name})

            df["date"] = pd.to_datetime(
                df["date"],
                errors="coerce",
            )

            df[name] = pd.to_numeric(
                df[name],
                errors="coerce",
            )

            df = (
                df
                .dropna(subset=["date"])
                .sort_values("date")
                .drop_duplicates(subset="date", keep="last")
                .reset_index(drop=True)
            )

            valid = df.dropna(subset=[name])

            if valid.empty:
                raise RuntimeError(
                    f"Série {series_id} sem valores numéricos válidos."
                )

            _print(
                f"✅ {name:24s} "
                f"{valid['date'].min().date()} "
                f"→ {valid['date'].max().date()} "
                f"| {len(valid):,} obs."
            )

            return df

        except Exception as error:
            last_error = error

            _print(
                f"⚠️ {name} [{series_id}] | "
                f"{type(error).__name__}: {error}"
            )

            if attempt < HTTP_RETRIES:
                time.sleep(1)

    raise RuntimeError(
        f"Falha ao baixar {name} [{series_id}] pela API FRED. "
        f"Último erro: {last_error}"
    )


def download_all_fred() -> Dict[str, pd.DataFrame]:
    """
    Baixa as séries FRED em paralelo usando a API oficial.
    """

    _print("")
    _print("=" * 80)
    _print("BAIXANDO DADOS MACRO — FRED API OFICIAL")
    _print("=" * 80)

    _get_fred_api_key()

    items = list(FRED_SERIES.items())
    fred_data: Dict[str, pd.DataFrame] = {}

    max_workers = min(4, len(items))

    _print(
        f"→ Baixando {len(items)} séries "
        f"com até {max_workers} conexões simultâneas..."
    )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:

        future_map = {
            executor.submit(
                download_fred_series,
                series_id,
                name,
            ): (name, series_id)
            for name, series_id in items
        }

        for future in as_completed(future_map):

            name, series_id = future_map[future]

            try:
                fred_data[name] = future.result()

            except Exception as error:
                _print(
                    f"❌ Falha final em {name} [{series_id}]"
                )
                _print(
                    f"   {type(error).__name__}: {error}"
                )

                fred_data[name] = pd.DataFrame(
                    columns=["date", name]
                )

    fred_data = {
        name: fred_data.get(
            name,
            pd.DataFrame(columns=["date", name]),
        )
        for name in FRED_SERIES.keys()
    }

    success = sum(
        1
        for name, df in fred_data.items()
        if (
            df is not None
            and not df.empty
            and name in df.columns
            and df[name].notna().any()
        )
    )

    _print("")
    _print(
        f"✅ FRED concluído: "
        f"{success}/{len(items)} séries válidas."
    )

    if success == 0:
        raise RuntimeError(
            "Nenhuma série FRED foi obtida pela API oficial."
        )

    missing = [
        name
        for name, df in fred_data.items()
        if (
            df is None
            or df.empty
            or name not in df.columns
            or not df[name].notna().any()
        )
    ]

    if missing:
        raise RuntimeError(
            "FRED incompleto. Séries ausentes: "
            + ", ".join(missing)
        )

    return fred_data

# ============================================================
# SHILLER — CAPE
# ============================================================

HISTORY_OF_MARKET_CAPE_URL = "https://historyofmarket.com/api/sp500/pe.json"
MULTPL_CAPE_MONTHLY_URL = "https://www.multpl.com/shiller-pe/table/by-month"

# Cache local de segurança.
# É usado SOMENTE se todas as fontes CAPE falharem na execução atual.
CAPE_STATE_CACHE_FILE = "data/current_state.csv"
MAX_CACHED_CAPE_AGE_MONTHS = 3


def _load_cached_cape_state():
    """
    Lê o último CAPE válido já persistido pelo Atlas.

    Fail-safe:
    - não recalcula valuation;
    - não inventa dado;
    - só reutiliza o último CAPE + percentil já conhecidos;
    - rejeita cache excessivamente antigo.
    """

    cache_path = CAPE_STATE_CACHE_FILE

    if not os.path.exists(cache_path):
        return None

    try:

        cached = pd.read_csv(cache_path)

        if cached is None or cached.empty:
            return None

        row = cached.iloc[-1]

        cache_date = pd.to_datetime(
            row.get("date"),
            errors="coerce",
        )

        cache_cape = pd.to_numeric(
            row.get("cape"),
            errors="coerce",
        )

        cache_percentile = pd.to_numeric(
            row.get("cape_percentile"),
            errors="coerce",
        )

        if (
            pd.isna(cache_date)
            or pd.isna(cache_cape)
            or pd.isna(cache_percentile)
        ):
            return None

        if not (1 <= float(cache_cape) <= 100):
            return None

        if not (0 <= float(cache_percentile) <= 1):
            return None

        today_month = pd.Timestamp.today().to_period("M")
        cache_month = pd.Timestamp(cache_date).to_period("M")

        age_months = (
            (today_month.year - cache_month.year) * 12
            + (today_month.month - cache_month.month)
        )

        if age_months > MAX_CACHED_CAPE_AGE_MONTHS:
            _print(
                f"⚠️ Cache CAPE rejeitado: {age_months} meses de defasagem."
            )
            return None

        return {
            "date": pd.Timestamp(cache_date),
            "cape": float(cache_cape),
            "cape_percentile": float(cache_percentile),
            "age_months": int(age_months),
        }

    except Exception as error:

        _print(
            f"⚠️ Não foi possível ler cache CAPE: "
            f"{type(error).__name__}: {error}"
        )

        return None


def _parse_shiller_xls(content: bytes) -> pd.DataFrame:
    """
    Lê a planilha histórica de Robert Shiller.
    Corrige o cabeçalho exigindo que a primeira coluna seja 'Date'.
    """

    excel_data = io.BytesIO(content)

    raw = pd.read_excel(
        excel_data,
        sheet_name="Data",
        header=None,
        engine="xlrd",
    )

    _print(
        f"→ Planilha lida: "
        f"{raw.shape[0]:,} linhas × "
        f"{raw.shape[1]:,} colunas"
    )

    header_row = None

    for i in range(min(25, len(raw))):
        first_cell = str(raw.iloc[i, 0]).strip().lower()

        if first_cell == "date":
            header_row = i
            break

    if header_row is None:
        raise RuntimeError(
            "Cabeçalho principal do Shiller não localizado."
        )

    _print(
        f"→ Cabeçalho principal detectado na linha {header_row}"
    )

    header_values = [
        str(value).strip()
        if not pd.isna(value)
        else ""
        for value in raw.iloc[header_row].tolist()
    ]

    cape_index = None

    for idx, value in enumerate(header_values):
        normalized = value.lower()

        if normalized in {
            "cape",
            "p/e10",
            "p/e10 or cape",
        }:
            cape_index = idx
            break

    if cape_index is None and raw.shape[1] > 12:
        cape_index = 12

    if cape_index is None:
        raise RuntimeError(
            "Coluna CAPE não localizada na planilha Shiller."
        )

    _print(
        f"→ CAPE detectado na coluna física {cape_index}"
    )

    data = raw.iloc[
        header_row + 1:
    ].copy()

    date_numeric = pd.to_numeric(
        data.iloc[:, 0],
        errors="coerce",
    )

    cape_numeric = pd.to_numeric(
        data.iloc[:, cape_index],
        errors="coerce",
    )

    years = np.floor(date_numeric)

    months = np.rint(
        (date_numeric - years) * 100
    )

    months_series = pd.Series(
        months,
        index=data.index,
    )

    valid = (
        date_numeric.notna()
        & pd.Series(
            years,
            index=data.index,
        ).between(1800, 2200)
        & months_series.between(1, 12)
    )

    years_series = pd.Series(
        years,
        index=data.index,
    ).where(valid)

    months_series = months_series.where(valid)

    date_string = (
        years_series.astype("Int64").astype(str)
        + "-"
        + months_series.astype("Int64").astype(str).str.zfill(2)
        + "-01"
    )

    result = pd.DataFrame({
        "date": pd.to_datetime(
            date_string,
            errors="coerce",
        ),
        "cape": cape_numeric,
    })

    result = (
        result
        .dropna(
            subset=[
                "date",
                "cape",
            ]
        )
        .loc[
            lambda x:
            x["cape"].between(
                1,
                100,
            )
        ]
        .sort_values("date")
        .drop_duplicates(
            subset="date",
            keep="last",
        )
        .reset_index(drop=True)
    )

    if len(result) < 1000:
        raise RuntimeError(
            "Base CAPE Shiller retornou poucas observações: "
            f"{len(result)}"
        )

    return result


def _extract_cape_records_from_json(payload) -> pd.DataFrame:
    """
    Extrai registros de CAPE de diferentes formatos JSON.

    O endpoint History of Market é tratado de forma defensiva:
    aceita lista de registros ou dicionários aninhados contendo
    campos de data + valor/CAPE.
    """

    rows = []

    date_keys = {
        "date",
        "period",
        "datetime",
        "timestamp",
        "month",
    }

    value_keys = {
        "value",
        "cape",
        "pe10",
        "shiller_cape",
        "shiller_pe",
        "ratio",
    }

    def walk(obj):

        if isinstance(obj, dict):

            normalized = {
                str(k).strip().lower(): v
                for k, v in obj.items()
            }

            date_value = None
            cape_value = None

            for key in date_keys:
                if key in normalized:
                    date_value = normalized[key]
                    break

            for key in value_keys:
                if key in normalized:
                    cape_value = normalized[key]
                    break

            if date_value is not None and cape_value is not None:

                parsed_date = pd.to_datetime(
                    date_value,
                    errors="coerce",
                )

                parsed_cape = pd.to_numeric(
                    cape_value,
                    errors="coerce",
                )

                if (
                    not pd.isna(parsed_date)
                    and not pd.isna(parsed_cape)
                    and 1 <= float(parsed_cape) <= 100
                ):

                    rows.append({
                        "date": pd.Timestamp(
                            year=parsed_date.year,
                            month=parsed_date.month,
                            day=1,
                        ),
                        "cape": float(parsed_cape),
                    })

            for value in obj.values():
                walk(value)

        elif isinstance(obj, list):

            for item in obj:
                walk(item)

    walk(payload)

    if not rows:
        raise RuntimeError(
            "JSON de CAPE acessado, mas nenhum registro "
            "data/valor válido foi identificado."
        )

    result = pd.DataFrame(rows)

    result = (
        result
        .sort_values("date")
        .drop_duplicates(
            subset="date",
            keep="last",
        )
        .reset_index(drop=True)
    )

    return result


def download_current_cape_history_of_market() -> pd.DataFrame:
    """
    Fonte recente principal do CAPE.

    Usa o endpoint JSON público e estável do History of Market.
    """

    _print("")
    _print("→ Atualizando CAPE recente via JSON...")

    response = _http_get(
        url=HISTORY_OF_MARKET_CAPE_URL,
        read_timeout=20,
    )

    try:
        payload = response.json()

    except Exception as error:
        raise RuntimeError(
            f"Resposta CAPE não é JSON válido: {error}"
        ) from error

    recent = _extract_cape_records_from_json(
        payload
    )

    latest_date = recent["date"].max()

    latest_cape = recent.loc[
        recent["date"].idxmax(),
        "cape",
    ]

    if latest_date.year < 2025:
        raise RuntimeError(
            "Fonte JSON de CAPE está excessivamente desatualizada."
        )

    if not (10 <= float(latest_cape) <= 70):
        raise RuntimeError(
            "CAPE recente fora da faixa de sanidade."
        )

    _print(
        f"✅ CAPE JSON: "
        f"{recent['date'].min().date()} "
        f"→ {latest_date.date()} "
        f"| {len(recent):,} obs."
    )

    _print(
        f"✅ CAPE recente detectado: "
        f"{latest_cape:.2f}"
    )

    return recent


def download_current_cape_multpl() -> pd.DataFrame:
    """
    Fallback secundário.

    O Multpl pode entregar HTML sem a tabela para alguns runners,
    por isso não é mais a fonte recente principal.
    """

    _print("")
    _print("→ Tentando fallback CAPE via Multpl...")

    response = _http_get(
        url=MULTPL_CAPE_MONTHLY_URL,
        read_timeout=20,
    )

    html = response.text

    rows = []

    # Tenta extrair pares de data/valor diretamente do texto HTML.
    date_pattern = re.compile(
        r'([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})'
    )

    for match in date_pattern.finditer(html):

        date_text = match.group(1)

        tail = html[
            match.end():
            match.end() + 400
        ]

        value_match = re.search(
            r'([0-9]{1,3}(?:\.[0-9]+)?)',
            tail,
        )

        if value_match is None:
            continue

        date_value = pd.to_datetime(
            date_text,
            errors="coerce",
        )

        cape_value = pd.to_numeric(
            value_match.group(1),
            errors="coerce",
        )

        if (
            pd.isna(date_value)
            or pd.isna(cape_value)
            or not (1 <= float(cape_value) <= 100)
        ):
            continue

        rows.append({
            "date": pd.Timestamp(
                year=date_value.year,
                month=date_value.month,
                day=1,
            ),
            "cape": float(cape_value),
        })

    if not rows:
        raise RuntimeError(
            "Multpl acessado, mas nenhum CAPE válido foi extraído."
        )

    recent = pd.DataFrame(rows)

    recent = (
        recent
        .sort_values("date")
        .drop_duplicates(
            subset="date",
            keep="last",
        )
        .reset_index(drop=True)
    )

    return recent


def download_shiller() -> pd.DataFrame:

    _print("")
    _print("=" * 80)
    _print("BAIXANDO SHILLER CAPE")
    _print("=" * 80)

    historical = None
    last_error = None

    for source_number, url in enumerate(
        SHILLER_URLS,
        start=1,
    ):

        try:

            _print(
                f"[Fonte {source_number}/"
                f"{len(SHILLER_URLS)}]"
            )

            _print(
                f"→ {url}"
            )

            response = _http_get(
                url=url,
                read_timeout=SHILLER_READ_TIMEOUT,
            )

            content = response.content

            if len(content) < 10_000:
                raise RuntimeError(
                    "Arquivo Shiller muito pequeno."
                )

            _print(
                f"→ Arquivo recebido: "
                f"{len(content) / 1024:.1f} KB"
            )

            historical = _parse_shiller_xls(content)

            _print(
                f"✅ CAPE histórico: "
                f"{historical['date'].min().date()} "
                f"→ {historical['date'].max().date()}"
            )

            _print(
                f"✅ Observações históricas: "
                f"{len(historical):,}"
            )

            _print(
                f"✅ CAPE histórico mais recente: "
                f"{historical['cape'].iloc[-1]:.2f}"
            )

            break

        except Exception as error:

            last_error = error

            _print(
                f"⚠️ Fonte Shiller falhou: "
                f"{type(error).__name__}: {error}"
            )

    if historical is None or historical.empty:
        raise RuntimeError(
            "Nenhuma fonte Shiller histórica funcionou. "
            f"Último erro: {last_error}"
        )

    recent = None
    recent_errors = []

    # Fonte principal recente: JSON estável.
    try:

        recent = download_current_cape_history_of_market()

    except Exception as error:

        recent_errors.append(
            f"HistoryOfMarket: {type(error).__name__}: {error}"
        )

        _print(
            "⚠️ Fonte JSON de CAPE falhou."
        )

        _print(
            f"   {type(error).__name__}: {error}"
        )

    # Fallback secundário.
    if recent is None or recent.empty:

        try:

            recent = download_current_cape_multpl()

        except Exception as error:

            recent_errors.append(
                f"Multpl: {type(error).__name__}: {error}"
            )

            _print(
                "⚠️ Fallback Multpl de CAPE falhou."
            )

            _print(
                f"   {type(error).__name__}: {error}"
            )

    if recent is None or recent.empty:

        _print(
            "⚠️ Nenhuma fonte recente de CAPE funcionou; "
            "mantendo apenas Shiller histórico."
        )

        for message in recent_errors:
            _print(
                f"   {message}"
            )

        return historical

    historical_last_date = historical["date"].max()

    recent_extension = recent[
        recent["date"] >= historical_last_date
    ].copy()

    combined = pd.concat(
        [
            historical,
            recent_extension,
        ],
        ignore_index=True,
    )

    combined = (
        combined
        .sort_values("date")
        .drop_duplicates(
            subset="date",
            keep="last",
        )
        .reset_index(drop=True)
    )

    _print(
        f"✅ CAPE combinado: "
        f"{combined['date'].min().date()} "
        f"→ {combined['date'].max().date()}"
    )

    _print(
        f"✅ CAPE mais recente combinado: "
        f"{combined['cape'].iloc[-1]:.2f}"
    )

    return combined

# ============================================================
# MERGE DAS SÉRIES FRED
# ============================================================

def merge_fred_series(
    fred_data: Dict[
        str,
        pd.DataFrame
    ]
) -> pd.DataFrame:

    _print("")
    _print(
        "→ Consolidando séries FRED..."
    )

    merged = None

    for name, df in (
        fred_data.items()
    ):

        if (
            df is None
            or df.empty
            or name not in df.columns
        ):

            continue

        temp = df[
            [
                "date",
                name,
            ]
        ].copy()

        if merged is None:

            merged = temp

        else:

            merged = pd.merge(
                merged,
                temp,
                on="date",
                how="outer",
                validate="one_to_one",
            )

    if (
        merged is None
        or merged.empty
    ):

        raise RuntimeError(
            "Nenhuma série FRED disponível "
            "para consolidação."
        )

    merged = (
        merged
        .sort_values("date")
        .drop_duplicates(
            subset="date",
            keep="last",
        )
        .reset_index(drop=True)
    )

    _print(
        f"✅ Macro consolidado: "
        f"{merged['date'].min().date()} "
        f"→ "
        f"{merged['date'].max().date()}"
    )

    return merged


# ============================================================
# FEATURES DE MERCADO
# ============================================================

def calculate_market_features(
    market: pd.DataFrame
) -> pd.DataFrame:

    df = market.copy()

    df["ath"] = (
        df["sp500"]
        .cummax()
    )

    df["drawdown"] = (
        df["sp500"]
        /
        df["ath"]
        - 1
    )

    df[
        "distance_from_ath"
    ] = df["drawdown"]

    df["return_6m"] = (
        df["sp500"]
        .pct_change(
            periods=6,
            fill_method=None,
        )
    )

    df["return_12m"] = (
        df["sp500"]
        .pct_change(
            periods=12,
            fill_method=None,
        )
    )

    df["return_24m"] = (
        df["sp500"]
        .pct_change(
            periods=24,
            fill_method=None,
        )
    )

    return df


# ============================================================
# FEATURES MONETÁRIAS
# ============================================================

def calculate_monetary_features(
    df: pd.DataFrame
) -> pd.DataFrame:

    result = df.copy()

    if (
        "fed_funds"
        in result.columns
    ):

        result[
            "fed_change_6m"
        ] = (
            result["fed_funds"]
            .diff(6)
        )

        result[
            "fed_change_12m"
        ] = (
            result["fed_funds"]
            .diff(12)
        )

    if (
        "treasury_10y"
        in result.columns
        and
        "treasury_2y"
        in result.columns
    ):

        result[
            "yield_curve_10y_2y"
        ] = (

            result[
                "treasury_10y"
            ]

            -

            result[
                "treasury_2y"
            ]
        )

        result[
            "yield_curve_change_6m"
        ] = (

            result[
                "yield_curve_10y_2y"
            ]
            .diff(6)
        )

    return result


# ============================================================
# FEATURES DE INFLAÇÃO
# ============================================================

def calculate_inflation_features(
    df: pd.DataFrame
) -> pd.DataFrame:

    result = df.copy()

    if (
        "cpi"
        not in result.columns
    ):

        return result

    result[
        "inflation_yoy"
    ] = (

        result["cpi"]
        .pct_change(
            periods=12,
            fill_method=None,
        )
        *
        100
    )

    inflation_6m = (

        result["cpi"]
        .pct_change(
            periods=6,
            fill_method=None,
        )
    )

    result[
        "inflation_6m_annualized"
    ] = (

        (
            (1 + inflation_6m)
            ** 2
            - 1
        )

        *
        100
    )

    result[
        "inflation_change_6m"
    ] = (

        result[
            "inflation_yoy"
        ]
        .diff(6)
    )

    return result


# ============================================================
# FEATURES DO MERCADO DE TRABALHO
# ============================================================

def calculate_labor_features(
    df: pd.DataFrame
) -> pd.DataFrame:

    result = df.copy()

    if (
        "unemployment"
        in result.columns
    ):

        result[
            "unemployment_change_6m"
        ] = (

            result[
                "unemployment"
            ]
            .diff(6)
        )

        result[
            "unemployment_change_12m"
        ] = (

            result[
                "unemployment"
            ]
            .diff(12)
        )

    if (
        "sahm"
        in result.columns
    ):

        result[
            "sahm_indicator"
        ] = result["sahm"]

    return result


# ============================================================
# PRODUÇÃO INDUSTRIAL
# ============================================================

def calculate_industrial_features(
    df: pd.DataFrame
) -> pd.DataFrame:

    result = df.copy()

    if (
        "industrial_production"
        not in result.columns
    ):

        return result

    result[
        "industrial_production_yoy"
    ] = (

        result[
            "industrial_production"
        ]
        .pct_change(
            periods=12,
            fill_method=None,
        )

        *
        100
    )

    return result


# ============================================================
# CAPE PERCENTILE
# ============================================================

def calculate_cape_percentile(
    df: pd.DataFrame
) -> pd.DataFrame:

    result = df.copy()

    if (
        "cape"
        not in result.columns
    ):

        return result

    # --------------------------------------------------------
    # Percentil expanding.
    #
    # Não utiliza informações futuras.
    # --------------------------------------------------------

    def expanding_percentile(
        values
    ):

        s = pd.Series(
            values
        ).dropna()

        if len(s) < 60:

            return np.nan

        current = s.iloc[-1]

        return float(
            (
                s <= current
            ).mean()
        )

    result[
        "cape_percentile"
    ] = (

        result["cape"]
        .expanding(
            min_periods=60
        )
        .apply(
            expanding_percentile,
            raw=False,
        )
    )

    return result


# ============================================================
# MASTER DATASET
# ============================================================

def build_master_dataset() -> pd.DataFrame:

    _print("")
    _print("=" * 80)
    _print(
        "SP500 CYCLE ATLAS — DATA PIPELINE"
    )
    _print("=" * 80)

    start_time = time.time()

    # ========================================================
    # 1. MERCADO
    # ========================================================

    _print("")
    _print("[1/4] MERCADO")

    market = download_sp500()

    market = (
        calculate_market_features(
            market
        )
    )

    _print(
        "✅ Features de mercado calculadas."
    )

    # ========================================================
    # 2. FRED
    # ========================================================

    _print("")
    _print("[2/4] MACRO / FRED")

    fred_data = (
        download_all_fred()
    )

    macro = merge_fred_series(
        fred_data
    )

    macro = (
        calculate_monetary_features(
            macro
        )
    )

    macro = (
        calculate_inflation_features(
            macro
        )
    )

    macro = (
        calculate_labor_features(
            macro
        )
    )

    macro = (
        calculate_industrial_features(
            macro
        )
    )

    _print(
        "✅ Features macro calculadas."
    )

    # Guardar datas REAIS das fontes antes de qualquer ffill.
    source_last_dates = {}
    source_last_values = {}

    source_columns = [
        "fed_funds",
        "treasury_2y",
        "treasury_10y",
        "cpi",
        "unemployment",
        "sahm_indicator",
        "industrial_production",
    ]

    for column in source_columns:

        if column not in macro.columns:
            continue

        valid_source = macro[
            ["date", column]
        ].dropna()

        if valid_source.empty:
            continue

        source_last_dates[column] = pd.Timestamp(
            valid_source.iloc[-1]["date"]
        )

        source_last_values[column] = (
            valid_source.iloc[-1][column]
        )

    # ========================================================
    # 3. SHILLER
    # ========================================================

    _print("")
    _print("[3/4] VALUATION / SHILLER")

    cape_cache = None
    cape_cache_active = False

    try:

        shiller = (
            download_shiller()
        )

    except Exception as error:

        _print("")
        _print(
            "⚠️ CAPE indisponível nas fontes online desta execução."
        )

        _print(
            f"{type(error).__name__}: "
            f"{error}"
        )

        # ----------------------------------------------------
        # FAIL-SAFE — ÚLTIMO CAPE VÁLIDO PERSISTIDO
        # ----------------------------------------------------

        cape_cache = _load_cached_cape_state()

        if cape_cache is not None:

            cape_cache_active = True

            _print("")
            _print(
                "🛡️ FAIL-SAFE CAPE ATIVADO."
            )

            _print(
                f"→ Último CAPE válido: "
                f"{cape_cache['cape']:.2f}"
            )

            _print(
                f"→ Percentil CAPE preservado: "
                f"{cape_cache['cape_percentile'] * 100:.2f}%"
            )

            _print(
                f"→ Data do cache: "
                f"{cape_cache['date'].date()}"
            )

            _print(
                "→ O Atlas NÃO rebaixará valuation por ausência de dado."
            )

        else:

            _print("")
            _print(
                "❌ CAPE indisponível e nenhum cache válido foi encontrado."
            )

            _print(
                "❌ Execução interrompida para evitar mudança falsa de regime."
            )

            raise RuntimeError(
                "CAPE crítico indisponível e sem cache válido. "
                "Fail-safe bloqueou a classificação operacional."
            ) from error

        shiller = (
            pd.DataFrame(
                columns=[
                    "date",
                    "cape",
                ]
            )
        )

    if not shiller.empty:

        valid_cape_source = shiller[
            ["date", "cape"]
        ].dropna()

        if not valid_cape_source.empty:

            source_last_dates["cape"] = pd.Timestamp(
                valid_cape_source.iloc[-1]["date"]
            )

            source_last_values["cape"] = (
                valid_cape_source.iloc[-1]["cape"]
            )

    # ========================================================
    # 4. MERGE
    # ========================================================

    _print("")
    _print("[4/4] MASTER DATASET")

    master = pd.merge(
        market,
        macro,
        on="date",
        how="left",
        validate="one_to_one",
    )

    if not shiller.empty:

        master = pd.merge(
            master,
            shiller,
            on="date",
            how="left",
            validate="one_to_one",
        )

    else:

        master["cape"] = np.nan

    master = (
        master
        .sort_values("date")
        .drop_duplicates(
            subset="date",
            keep="last",
        )
        .reset_index(drop=True)
    )

    # --------------------------------------------------------
    # Forward-fill limitado
    # --------------------------------------------------------

    macro_columns = [

        "fed_funds",
        "fed_change_6m",
        "fed_change_12m",

        "treasury_10y",
        "treasury_2y",

        "yield_curve_10y_2y",
        "yield_curve_change_6m",

        "cpi",

        "inflation_yoy",

        "inflation_6m_annualized",

        "inflation_change_6m",

        "unemployment",

        "unemployment_change_6m",

        "unemployment_change_12m",

        "sahm",

        "sahm_indicator",

        "industrial_production",

        "industrial_production_yoy",
    ]

    for column in (
        macro_columns
    ):

        if (
            column
            in master.columns
        ):

            master[column] = (
                master[column]
                .ffill(
                    limit=3
                )
            )

    # --------------------------------------------------------
    # CAPE
    # --------------------------------------------------------

    if (
        "cape"
        in master.columns
    ):

        master[
            "cape"
        ] = (

            master["cape"]
            .ffill(
                limit=3
            )
        )

    master = (
        calculate_cape_percentile(
            master
        )
    )

    # --------------------------------------------------------
    # RESTAURAR CAPE/PERCENTIL DO CACHE NO ÚLTIMO MÊS
    # --------------------------------------------------------
    #
    # Se as fontes online falharam, o histórico CAPE desta execução
    # pode estar vazio. Nesse caso, preservamos apenas o último estado
    # validado anteriormente. Isso impede UNKNOWN -> GREEN por falta
    # de dado, sem inventar informação nova.
    # --------------------------------------------------------

    if cape_cache_active and cape_cache is not None:

        latest_idx = master["date"].idxmax()

        master.loc[
            latest_idx,
            "cape"
        ] = cape_cache["cape"]

        master.loc[
            latest_idx,
            "cape_percentile"
        ] = cape_cache["cape_percentile"]

        source_last_dates["cape"] = (
            cape_cache["date"]
        )

        source_last_values["cape"] = (
            cape_cache["cape"]
        )

        master.attrs["cape_fail_safe_active"] = True
        master.attrs["cape_cache_date"] = cape_cache["date"]

        _print("")
        _print(
            "🛡️ CAPE FAIL-SAFE APLICADO AO ESTADO ATUAL."
        )

        _print(
            f"✅ CAPE preservado: "
            f"{cape_cache['cape']:.2f}"
        )

        _print(
            f"✅ Percentil preservado: "
            f"{cape_cache['cape_percentile'] * 100:.2f}%"
        )

    else:

        master.attrs["cape_fail_safe_active"] = False

    elapsed = (
        time.time()
        -
        start_time
    )

    _print("")
    _print("=" * 80)
    _print("MASTER DATASET CONCLUÍDO")
    _print("=" * 80)

    _print(
        f"Período: "
        f"{master['date'].min().date()} "
        f"→ "
        f"{master['date'].max().date()}"
    )

    _print(
        f"Meses: "
        f"{len(master):,}"
    )

    _print(
        f"Tempo do pipeline: "
        f"{elapsed:.1f}s"
    )

    master.attrs["source_last_dates"] = source_last_dates
    master.attrs["source_last_values"] = source_last_values

    return master


# ============================================================
# AUDITORIA DE FRESCOR
# ============================================================

def freshness_audit(
    master: pd.DataFrame
) -> pd.DataFrame:

    columns = {
        "sp500": "S&P 500",
        "cape": "CAPE",
        "fed_funds": "Fed Funds",
        "treasury_2y": "Treasury 2Y",
        "treasury_10y": "Treasury 10Y",
        "cpi": "CPI",
        "unemployment": "Unemployment",
        "sahm_indicator": "Sahm",
        "industrial_production": "Industrial Production",
    }

    rows = []

    market_date = pd.Timestamp(
        master["date"].max()
    )

    source_last_dates = master.attrs.get(
        "source_last_dates",
        {},
    )

    source_last_values = master.attrs.get(
        "source_last_values",
        {},
    )

    for column, label in columns.items():

        if column not in master.columns:
            continue

        if column == "sp500":

            valid = master[
                ["date", column]
            ].dropna()

            if valid.empty:
                continue

            last_date = pd.Timestamp(
                valid.iloc[-1]["date"]
            )

            last_value = valid.iloc[-1][column]
            observations = len(valid)

        elif column in source_last_dates:

            last_date = pd.Timestamp(
                source_last_dates[column]
            )

            last_value = source_last_values.get(
                column,
                np.nan,
            )

            observations = np.nan

        else:

            valid = master[
                ["date", column]
            ].dropna()

            if valid.empty:
                continue

            last_date = pd.Timestamp(
                valid.iloc[-1]["date"]
            )

            last_value = valid.iloc[-1][column]
            observations = len(valid)

        lag_months = (
            (market_date.year - last_date.year) * 12
            +
            (market_date.month - last_date.month)
        )

        rows.append({
            "series": label,
            "last_valid_date": last_date,
            "last_value": last_value,
            "lag_months": lag_months,
            "observations": observations,
        })

    return pd.DataFrame(rows)

# ============================================================
# ÚLTIMO ESTADO DISPONÍVEL
# ============================================================

def get_latest_state(
    master: pd.DataFrame
) -> pd.Series:

    if (
        master is None
        or master.empty
    ):

        raise RuntimeError(
            "Master dataset vazio."
        )

    return (
        master
        .sort_values("date")
        .iloc[-1]
        .copy()
    )


# ============================================================
# TESTE ISOLADO
# ============================================================

if __name__ == "__main__":

    _print("")
    _print("=" * 80)
    _print(
        "TESTE ISOLADO — market_data.py"
    )
    _print("=" * 80)

    master = (
        build_master_dataset()
    )

    audit = (
        freshness_audit(
            master
        )
    )

    _print("")
    _print("=" * 80)
    _print(
        "AUDITORIA DE FRESCOR"
    )
    _print("=" * 80)

    _print(
        audit.to_string(
            index=False
        )
    )

    latest = (
        get_latest_state(
            master
        )
    )

    _print("")
    _print("=" * 80)
    _print("ÚLTIMO ESTADO")
    _print("=" * 80)

    important = [

        "date",

        "sp500",

        "drawdown",

        "return_12m",

        "cape",

        "cape_percentile",

        "fed_funds",

        "fed_change_12m",

        "yield_curve_10y_2y",

        "inflation_yoy",

        "inflation_change_6m",

        "unemployment",

        "sahm_indicator",

        "industrial_production_yoy",
    ]

    for column in important:

        if column in latest.index:

            _print(
                f"{column:32s}: "
                f"{latest[column]}"
            )

    _print("")
    _print(
        "✅ market_data.py executado."
    )
