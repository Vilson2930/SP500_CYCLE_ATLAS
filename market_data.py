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
import time
import warnings
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

    _print(
        f"Ticker: {SP500_TICKER}"
    )

    _print(
        f"Início histórico: {MARKET_START_DATE}"
    )

    _print(
        "→ Conectando ao Yahoo Finance..."
    )

    try:

        data = yf.download(
            SP500_TICKER,
            start=MARKET_START_DATE,
            auto_adjust=False,
            progress=False,
            threads=False,
            timeout=20,
        )

    except Exception as error:

        raise RuntimeError(
            "Falha ao consultar Yahoo Finance: "
            f"{type(error).__name__}: {error}"
        ) from error

    _print(
        "→ Resposta do Yahoo recebida."
    )

    if (
        data is None
        or data.empty
    ):

        raise RuntimeError(
            "Yahoo Finance retornou dataset vazio."
        )

    # --------------------------------------------------------
    # Corrigir MultiIndex do yfinance
    # --------------------------------------------------------

    if isinstance(
        data.columns,
        pd.MultiIndex,
    ):

        try:

            close = (
                data["Close"][
                    SP500_TICKER
                ]
            )

        except Exception:

            close = (
                data["Close"]
                .iloc[:, 0]
            )

    else:

        if "Close" not in data.columns:

            raise RuntimeError(
                "Coluna Close não encontrada "
                "nos dados do Yahoo."
            )

        close = data["Close"]

    # --------------------------------------------------------
    # DataFrame diário
    # --------------------------------------------------------

    close_values = np.asarray(
        close
    ).reshape(-1)

    df = pd.DataFrame({

        "date":
            pd.to_datetime(
                close.index
            ),

        "sp500":
            pd.to_numeric(
                close_values,
                errors="coerce",
            ),
    })

    df = (
        df
        .dropna(
            subset=[
                "date",
                "sp500",
            ]
        )
        .sort_values("date")
        .drop_duplicates(
            subset="date",
            keep="last",
        )
        .reset_index(drop=True)
    )

    if df.empty:

        raise RuntimeError(
            "S&P 500 ficou vazio após limpeza."
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
        f"✅ Observações mensais: "
        f"{len(df):,}"
    )

    _print(
        f"✅ Último fechamento: "
        f"{df['sp500'].iloc[-1]:,.2f}"
    )

    return df


# ============================================================
# FRED — SÉRIE INDIVIDUAL
# ============================================================

def download_fred_series(
    series_id: str,
    name: str,
) -> pd.DataFrame:

    url = (
        "https://fred.stlouisfed.org/"
        "graph/fredgraph.csv"
        f"?id={series_id}"
    )

    _print(
        f"→ Baixando {name} [{series_id}]..."
    )

    response = _http_get(
        url=url,
        read_timeout=READ_TIMEOUT,
    )

    if not response.content:

        raise RuntimeError(
            f"FRED retornou resposta vazia: "
            f"{series_id}"
        )

    try:

        df = pd.read_csv(
            io.StringIO(
                response.text
            )
        )

    except Exception as error:

        raise RuntimeError(
            f"Falha ao interpretar CSV FRED "
            f"{series_id}: {error}"
        ) from error

    if (
        df is None
        or df.empty
        or len(df.columns) < 2
    ):

        raise RuntimeError(
            f"Série FRED inválida: {series_id}"
        )

    date_column = (
        df.columns[0]
    )

    value_column = (
        df.columns[1]
    )

    df = df.rename(
        columns={
            date_column: "date",
            value_column: name,
        }
    )

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce",
    )

    df[name] = pd.to_numeric(
        df[name],
        errors="coerce",
    )

    df = df[
        df["date"]
        >=
        pd.Timestamp(
            FRED_START_DATE
        )
    ].copy()

    df = (
        df
        .dropna(
            subset=["date"]
        )
        .sort_values("date")
        .drop_duplicates(
            subset="date",
            keep="last",
        )
        .reset_index(drop=True)
    )

    valid = df.dropna(
        subset=[name]
    )

    if valid.empty:

        raise RuntimeError(
            f"Série FRED sem valores válidos: "
            f"{series_id}"
        )

    _print(
        f"   ✅ {name}: "
        f"{valid['date'].min().date()} "
        f"→ "
        f"{valid['date'].max().date()} "
        f"| {len(valid):,} obs."
    )

    return df


# ============================================================
# FRED — TODAS AS SÉRIES
# ============================================================

def download_all_fred() -> Dict[str, pd.DataFrame]:

    _print("")
    _print("=" * 80)
    _print("BAIXANDO DADOS MACRO — FRED")
    _print("=" * 80)

    fred_data = {}

    total = len(
        FRED_SERIES
    )

    success = 0

    for position, (
        name,
        series_id,
    ) in enumerate(
        FRED_SERIES.items(),
        start=1,
    ):

        _print(
            f"[{position}/{total}] "
            f"{name}"
        )

        try:

            df = download_fred_series(
                series_id=series_id,
                name=name,
            )

            fred_data[name] = df

            success += 1

        except Exception as error:

            _print(
                f"   ❌ Falha em "
                f"{name} [{series_id}]"
            )

            _print(
                f"   {type(error).__name__}: "
                f"{error}"
            )

            fred_data[name] = (
                pd.DataFrame(
                    columns=[
                        "date",
                        name,
                    ]
                )
            )

    _print("")

    _print(
        f"FRED concluído: "
        f"{success}/{total} séries válidas."
    )

    if success == 0:

        raise RuntimeError(
            "Nenhuma série FRED foi obtida."
        )

    return fred_data


# ============================================================
# SHILLER — CAPE
# ============================================================

def download_shiller() -> pd.DataFrame:

    _print("")
    _print("=" * 80)
    _print("BAIXANDO SHILLER CAPE")
    _print("=" * 80)

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
                read_timeout=(
                    SHILLER_READ_TIMEOUT
                ),
            )

            content = response.content

            if len(content) < 10_000:

                raise RuntimeError(
                    "Arquivo Shiller muito pequeno "
                    "para ser uma planilha válida."
                )

            _print(
                f"→ Arquivo recebido: "
                f"{len(content) / 1024:.1f} KB"
            )

            excel_data = (
                io.BytesIO(content)
            )

            _print(
                "→ Lendo planilha XLS..."
            )

            try:

                raw = pd.read_excel(
                    excel_data,
                    sheet_name="Data",
                    header=None,
                    engine="xlrd",
                )

            except Exception as error:

                raise RuntimeError(
                    "Falha ao abrir XLS Shiller. "
                    "Verifique se 'xlrd' está "
                    "no requirements.txt. "
                    f"Erro: {error}"
                ) from error

            _print(
                f"→ Planilha lida: "
                f"{raw.shape[0]:,} linhas × "
                f"{raw.shape[1]:,} colunas"
            )

            # ------------------------------------------------
            # Localizar linha do cabeçalho
            # ------------------------------------------------

            header_row = None

            for i in range(
                min(
                    20,
                    len(raw)
                )
            ):

                first_values = (
                    raw.iloc[i]
                    .astype(str)
                    .str.strip()
                    .str.lower()
                )

                if (
                    first_values
                    ==
                    "date"
                ).any():

                    header_row = i
                    break

            if header_row is None:

                raise RuntimeError(
                    "Linha de cabeçalho 'Date' "
                    "não localizada na base Shiller."
                )

            _print(
                f"→ Cabeçalho detectado "
                f"na linha {header_row}"
            )

            headers = (
                raw.iloc[
                    header_row
                ]
                .tolist()
            )

            data = (
                raw.iloc[
                    header_row + 1:
                ]
                .copy()
            )

            data.columns = headers

            # ------------------------------------------------
            # Date
            # ------------------------------------------------

            date_col = None

            for column in (
                data.columns
            ):

                if (
                    str(column)
                    .strip()
                    .lower()
                    ==
                    "date"
                ):

                    date_col = column
                    break

            if date_col is None:

                raise RuntimeError(
                    "Coluna Date não encontrada."
                )

            # ------------------------------------------------
            # CAPE
            # ------------------------------------------------

            cape_col = None

            for column in (
                data.columns
            ):

                normalized = (
                    str(column)
                    .strip()
                    .lower()
                )

                if normalized in [
                    "cape",
                    "p/e10",
                    "p/e10 or cape",
                ]:

                    cape_col = column
                    break

            # ------------------------------------------------
            # Fallback:
            # procurar coluna com "cape"
            # ------------------------------------------------

            if cape_col is None:

                for column in (
                    data.columns
                ):

                    normalized = (
                        str(column)
                        .strip()
                        .lower()
                    )

                    if "cape" in normalized:

                        cape_col = column
                        break

            # ------------------------------------------------
            # Fallback numérico
            # ------------------------------------------------

            if cape_col is None:

                numeric_candidates = []

                for column in (
                    data.columns
                ):

                    series = pd.to_numeric(
                        data[column],
                        errors="coerce",
                    )

                    if (
                        series.notna().sum()
                        >
                        500
                    ):

                        numeric_candidates.append(
                            (
                                column,
                                series,
                            )
                        )

                for (
                    column,
                    series,
                ) in reversed(
                    numeric_candidates
                ):

                    median = (
                        series.median()
                    )

                    maximum = (
                        series.max()
                    )

                    if (
                        5 < median < 40
                        and
                        30 < maximum < 100
                    ):

                        cape_col = column
                        break

            if cape_col is None:

                raise RuntimeError(
                    "Coluna CAPE não identificada."
                )

            _print(
                f"→ CAPE detectado na coluna: "
                f"{cape_col}"
            )

            # ------------------------------------------------
            # Converter datas Shiller YYYY.MM
            # ------------------------------------------------

            date_numeric = pd.to_numeric(
                data[date_col],
                errors="coerce",
            )

            valid_date_mask = (
                date_numeric.notna()
                &
                (date_numeric >= 1800)
                &
                (date_numeric <= 2200)
            )

            date_numeric = (
                date_numeric.where(
                    valid_date_mask
                )
            )

            year = np.floor(
                date_numeric
            )

            month = np.round(
                (
                    date_numeric - year
                )
                *
                100
            )

            month = pd.Series(
                month,
                index=data.index,
            )

            month = month.where(
                month.between(
                    1,
                    12
                )
            )

            year_series = pd.Series(
                year,
                index=data.index,
            )

            date_string = (

                year_series
                .astype("Int64")
                .astype(str)

                + "-"

                + month
                .astype("Int64")
                .astype(str)
                .str.zfill(2)

                + "-01"
            )

            result = pd.DataFrame({

                "date":
                    pd.to_datetime(
                        date_string,
                        errors="coerce",
                    ),

                "cape":
                    pd.to_numeric(
                        data[cape_col],
                        errors="coerce",
                    ),
            })

            result = (
                result
                .dropna(
                    subset=[
                        "date",
                        "cape",
                    ]
                )
                .sort_values("date")
                .drop_duplicates(
                    subset="date",
                    keep="last",
                )
                .reset_index(drop=True)
            )

            # ------------------------------------------------
            # Sanidade
            # ------------------------------------------------

            result = result[
                result["cape"]
                .between(
                    1,
                    100
                )
            ].copy()

            if len(result) < 500:

                raise RuntimeError(
                    "Base CAPE retornou número "
                    "insuficiente de observações: "
                    f"{len(result)}"
                )

            _print(
                f"✅ CAPE: "
                f"{result['date'].min().date()} "
                f"→ "
                f"{result['date'].max().date()}"
            )

            _print(
                f"✅ Observações CAPE: "
                f"{len(result):,}"
            )

            _print(
                f"✅ CAPE mais recente: "
                f"{result['cape'].iloc[-1]:.2f}"
            )

            return result

        except Exception as error:

            last_error = error

            _print(
                f"⚠️ Fonte Shiller falhou: "
                f"{type(error).__name__}: "
                f"{error}"
            )

    raise RuntimeError(
        "Nenhuma fonte Shiller funcionou. "
        f"Último erro: {last_error}"
    )


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

    # ========================================================
    # 3. SHILLER
    # ========================================================

    _print("")
    _print("[3/4] VALUATION / SHILLER")

    try:

        shiller = (
            download_shiller()
        )

    except Exception as error:

        _print("")
        _print(
            "⚠️ CAPE indisponível nesta execução."
        )

        _print(
            f"{type(error).__name__}: "
            f"{error}"
        )

        _print(
            "⚠️ O restante do Atlas continuará."
        )

        shiller = (
            pd.DataFrame(
                columns=[
                    "date",
                    "cape",
                ]
            )
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

        "treasury_10y",
        "treasury_2y",

        "yield_curve_10y_2y",

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

    return master


# ============================================================
# AUDITORIA DE FRESCOR
# ============================================================

def freshness_audit(
    master: pd.DataFrame
) -> pd.DataFrame:

    columns = {

        "sp500":
            "S&P 500",

        "cape":
            "CAPE",

        "fed_funds":
            "Fed Funds",

        "treasury_2y":
            "Treasury 2Y",

        "treasury_10y":
            "Treasury 10Y",

        "cpi":
            "CPI",

        "unemployment":
            "Unemployment",

        "sahm_indicator":
            "Sahm",

        "industrial_production":
            "Industrial Production",
    }

    rows = []

    market_date = (
        master["date"]
        .max()
    )

    for (
        column,
        label,
    ) in columns.items():

        if (
            column
            not in master.columns
        ):

            continue

        valid = (
            master[
                [
                    "date",
                    column,
                ]
            ]
            .dropna()
        )

        if valid.empty:

            continue

        last = (
            valid.iloc[-1]
        )

        last_date = (
            pd.Timestamp(
                last["date"]
            )
        )

        lag_months = (

            (
                market_date.year
                -
                last_date.year
            )
            *
            12

            +

            (
                market_date.month
                -
                last_date.month
            )
        )

        rows.append({

            "series":
                label,

            "last_valid_date":
                last_date,

            "last_value":
                last[column],

            "lag_months":
                lag_months,

            "observations":
                len(valid),
        })

    return pd.DataFrame(
        rows
    )


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
