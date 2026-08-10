# ============================================================
# SP500 CYCLE ATLAS
# market_data.py
# ============================================================
#
# Responsável por:
#
# - S&P 500 via Yahoo Finance
# - CAPE via base de Robert Shiller
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
# UTILITÁRIOS
# ============================================================

def _print(message: str):
    print(message)


def _normalize_month(date_series):
    """
    Converte datas para o primeiro dia do mês.
    """
    return (
        pd.to_datetime(date_series)
        .dt.to_period("M")
        .dt.to_timestamp()
    )


def _safe_numeric(series):
    """
    Converte série para numérico sem quebrar execução.
    """
    return pd.to_numeric(series, errors="coerce")


# ============================================================
# S&P 500
# ============================================================

def download_sp500() -> pd.DataFrame:

    _print("=" * 80)
    _print("BAIXANDO S&P 500")
    _print("=" * 80)

    data = yf.download(
        SP500_TICKER,
        start=MARKET_START_DATE,
        auto_adjust=False,
        progress=False,
    )

    if data is None or data.empty:
        raise RuntimeError(
            "Não foi possível baixar dados do S&P 500."
        )

    # --------------------------------------------------------
    # Corrige MultiIndex eventualmente retornado pelo yfinance
    # --------------------------------------------------------

    if isinstance(data.columns, pd.MultiIndex):

        try:
            close = data["Close"][SP500_TICKER]

        except Exception:
            close = data["Close"].iloc[:, 0]

    else:

        close = data["Close"]

    df = pd.DataFrame({
        "date": pd.to_datetime(close.index),
        "sp500": pd.to_numeric(close.values, errors="coerce"),
    })

    df = (
        df
        .dropna()
        .sort_values("date")
        .drop_duplicates("date")
        .reset_index(drop=True)
    )

    # --------------------------------------------------------
    # Transformação mensal
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
        f"{df['date'].min().date()} → "
        f"{df['date'].max().date()}"
    )

    _print(f"Observações mensais: {len(df):,}")

    return df


# ============================================================
# FRED
# ============================================================

def download_fred_series(
    series_id: str,
    name: str,
) -> pd.DataFrame:

    """
    Faz download de uma série FRED usando CSV público.

    Não exige API key.
    """

    url = (
        "https://fred.stlouisfed.org/graph/"
        f"fredgraph.csv?id={series_id}"
    )

    _print(f"Baixando {name} [{series_id}]...")

    response = requests.get(
        url,
        timeout=60,
        headers={
            "User-Agent": "Mozilla/5.0"
        },
    )

    response.raise_for_status()

    df = pd.read_csv(
        io.StringIO(response.text)
    )

    if df.empty:
        raise RuntimeError(
            f"Série FRED vazia: {series_id}"
        )

    date_column = df.columns[0]
    value_column = df.columns[1]

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
        df["date"] >= pd.Timestamp(FRED_START_DATE)
    ]

    df = (
        df
        .dropna(subset=["date"])
        .sort_values("date")
        .drop_duplicates("date")
        .reset_index(drop=True)
    )

    _print(
        f"✅ {name}: "
        f"{df['date'].min().date()} → "
        f"{df['date'].max().date()}"
    )

    return df


# ============================================================
# TODAS AS SÉRIES FRED
# ============================================================

def download_all_fred() -> Dict[str, pd.DataFrame]:

    _print("")
    _print("=" * 80)
    _print("BAIXANDO DADOS MACRO — FRED")
    _print("=" * 80)

    fred_data = {}

    for name, series_id in FRED_SERIES.items():

        try:

            fred_data[name] = download_fred_series(
                series_id,
                name,
            )

        except Exception as error:

            _print(
                f"❌ Falha em {name} [{series_id}]"
            )

            _print(str(error))

            fred_data[name] = pd.DataFrame(
                columns=["date", name]
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

    for url in SHILLER_URLS:

        try:

            _print(f"Tentando: {url}")

            response = requests.get(
                url,
                timeout=90,
                headers={
                    "User-Agent": "Mozilla/5.0"
                },
            )

            response.raise_for_status()

            excel_data = io.BytesIO(
                response.content
            )

            # ------------------------------------------------
            # A planilha Shiller normalmente possui cabeçalhos
            # antes da tabela principal.
            # ------------------------------------------------

            raw = pd.read_excel(
                excel_data,
                sheet_name="Data",
                header=None,
            )

            # ------------------------------------------------
            # Localiza automaticamente a linha que contém Date
            # ------------------------------------------------

            header_row = None

            for i in range(min(20, len(raw))):

                row = raw.iloc[i].astype(str)

                if row.str.contains(
                    "Date",
                    case=False,
                    na=False,
                ).any():

                    header_row = i
                    break

            if header_row is None:

                raise RuntimeError(
                    "Cabeçalho da planilha Shiller "
                    "não localizado."
                )

            headers = raw.iloc[header_row].tolist()

            data = raw.iloc[
                header_row + 1:
            ].copy()

            data.columns = headers

            # ------------------------------------------------
            # Identifica Date
            # ------------------------------------------------

            date_col = None

            for column in data.columns:

                if str(column).strip().lower() == "date":

                    date_col = column
                    break

            if date_col is None:

                raise RuntimeError(
                    "Coluna Date não encontrada "
                    "na base Shiller."
                )

            # ------------------------------------------------
            # Identifica CAPE
            # ------------------------------------------------

            cape_col = None

            possible_names = [
                "cape",
                "cyclically adjusted",
                "p/e10",
            ]

            for column in data.columns:

                text = str(column).lower()

                if any(
                    name in text
                    for name in possible_names
                ):

                    cape_col = column
                    break

            # ------------------------------------------------
            # Em versões tradicionais da planilha,
            # CAPE costuma estar próximo das últimas colunas.
            # ------------------------------------------------

            if cape_col is None:

                numeric_candidates = []

                for column in data.columns:

                    series = pd.to_numeric(
                        data[column],
                        errors="coerce",
                    )

                    if series.notna().sum() > 100:

                        numeric_candidates.append(
                            column
                        )

                # Procura uma série compatível com CAPE
                # pela faixa econômica plausível.

                for column in reversed(
                    numeric_candidates
                ):

                    series = pd.to_numeric(
                        data[column],
                        errors="coerce",
                    )

                    median = series.median()

                    maximum = series.max()

                    if (
                        5 < median < 40
                        and maximum > 30
                        and maximum < 100
                    ):

                        cape_col = column
                        break

            if cape_col is None:

                raise RuntimeError(
                    "Não foi possível identificar "
                    "a coluna CAPE."
                )

            # ------------------------------------------------
            # Converte datas Shiller
            #
            # Exemplo:
            # 2026.07
            # ------------------------------------------------

            date_numeric = pd.to_numeric(
                data[date_col],
                errors="coerce",
            )

            year = np.floor(
                date_numeric
            )

            month_decimal = (
                date_numeric - year
            )

            month = np.round(
                month_decimal * 100
            )

            month = np.clip(
                month,
                1,
                12,
            )

            date_string = (
                year.astype("Int64").astype(str)
                + "-"
                + month.astype("Int64")
                .astype(str)
                .str.zfill(2)
                + "-01"
            )

            result = pd.DataFrame({
                "date": pd.to_datetime(
                    date_string,
                    errors="coerce",
                ),

                "cape": pd.to_numeric(
                    data[cape_col],
                    errors="coerce",
                ),
            })

            result = (
                result
                .dropna()
                .sort_values("date")
                .drop_duplicates("date")
                .reset_index(drop=True)
            )

            if len(result) < 100:

                raise RuntimeError(
                    "Base CAPE retornou poucas observações."
                )

            _print(
                f"✅ CAPE: "
                f"{result['date'].min().date()} → "
                f"{result['date'].max().date()}"
            )

            _print(
                f"Observações CAPE: {len(result):,}"
            )

            return result

        except Exception as error:

            last_error = error

            _print(
                f"⚠️ Falha nesta fonte: {error}"
            )

    raise RuntimeError(
        "Não foi possível carregar Shiller CAPE. "
        f"Último erro: {last_error}"
    )


# ============================================================
# MERGE DAS SÉRIES FRED
# ============================================================

def merge_fred_series(
    fred_data: Dict[str, pd.DataFrame]
) -> pd.DataFrame:

    merged = None

    for name, df in fred_data.items():

        if df is None or df.empty:
            continue

        temp = df[
            ["date", name]
        ].copy()

        if merged is None:

            merged = temp

        else:

            merged = pd.merge(
                merged,
                temp,
                on="date",
                how="outer",
            )

    if merged is None:

        raise RuntimeError(
            "Nenhuma série FRED disponível."
        )

    merged = (
        merged
        .sort_values("date")
        .drop_duplicates("date")
        .reset_index(drop=True)
    )

    return merged


# ============================================================
# FEATURES DE MERCADO
# ============================================================

def calculate_market_features(
    market: pd.DataFrame
) -> pd.DataFrame:

    df = market.copy()

    # --------------------------------------------------------
    # ATH
    # --------------------------------------------------------

    df["ath"] = (
        df["sp500"]
        .cummax()
    )

    # --------------------------------------------------------
    # Drawdown
    # --------------------------------------------------------

    df["drawdown"] = (
        df["sp500"] /
        df["ath"]
        - 1
    )

    # --------------------------------------------------------
    # Distância do ATH
    # --------------------------------------------------------

    df["distance_from_ath"] = (
        df["drawdown"]
    )

    # --------------------------------------------------------
    # Momentum 6 meses
    # --------------------------------------------------------

    df["return_6m"] = (
        df["sp500"]
        .pct_change(6)
    )

    # --------------------------------------------------------
    # Momentum 12 meses
    # --------------------------------------------------------

    df["return_12m"] = (
        df["sp500"]
        .pct_change(12)
    )

    # --------------------------------------------------------
    # Momentum 24 meses
    # --------------------------------------------------------

    df["return_24m"] = (
        df["sp500"]
        .pct_change(24)
    )

    return df


# ============================================================
# FEATURES MONETÁRIAS
# ============================================================

def calculate_monetary_features(
    df: pd.DataFrame
) -> pd.DataFrame:

    result = df.copy()

    if "fed_funds" in result.columns:

        result["fed_change_6m"] = (
            result["fed_funds"]
            .diff(6)
        )

        result["fed_change_12m"] = (
            result["fed_funds"]
            .diff(12)
        )

    if (
        "treasury_10y" in result.columns
        and
        "treasury_2y" in result.columns
    ):

        result["yield_curve_10y_2y"] = (
            result["treasury_10y"]
            -
            result["treasury_2y"]
        )

        result["yield_curve_change_6m"] = (
            result["yield_curve_10y_2y"]
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

    if "cpi" not in result.columns:
        return result

    # --------------------------------------------------------
    # Inflação YoY
    # --------------------------------------------------------

    result["inflation_yoy"] = (
        result["cpi"]
        .pct_change(12)
        * 100
    )

    # --------------------------------------------------------
    # Inflação acumulada em 6 meses anualizada
    # --------------------------------------------------------

    inflation_6m = (
        result["cpi"]
        .pct_change(6)
    )

    result["inflation_6m_annualized"] = (
        (
            (1 + inflation_6m) ** 2
            - 1
        )
        * 100
    )

    # --------------------------------------------------------
    # Mudança da inflação YoY em 6 meses
    # --------------------------------------------------------

    result["inflation_change_6m"] = (
        result["inflation_yoy"]
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

    if "unemployment" in result.columns:

        result["unemployment_change_6m"] = (
            result["unemployment"]
            .diff(6)
        )

        result["unemployment_change_12m"] = (
            result["unemployment"]
            .diff(12)
        )

    # --------------------------------------------------------
    # SAHMREALTIME já vem calculado oficialmente pelo FRED.
    # Não recalculamos.
    # --------------------------------------------------------

    if "sahm" in result.columns:

        result["sahm_indicator"] = (
            result["sahm"]
        )

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

        result["industrial_production"]
        .pct_change(12)
        * 100
    )

    return result


# ============================================================
# CAPE PERCENTILE
# ============================================================

def calculate_cape_percentile(
    df: pd.DataFrame
) -> pd.DataFrame:

    result = df.copy()

    if "cape" not in result.columns:
        return result

    cape = result["cape"]

    # --------------------------------------------------------
    # Percentil EXPANDING.
    #
    # Isso evita look-ahead:
    # cada mês só conhece o histórico disponível até então.
    # --------------------------------------------------------

    result["cape_percentile"] = (

        cape
        .expanding(min_periods=60)
        .apply(
            lambda x:
            pd.Series(x).rank(pct=True).iloc[-1],
            raw=False,
        )
    )

    return result


# ============================================================
# MERGE GERAL
# ============================================================

def build_master_dataset() -> pd.DataFrame:

    _print("")
    _print("=" * 80)
    _print("SP500 CYCLE ATLAS — DATA PIPELINE")
    _print("=" * 80)

    # --------------------------------------------------------
    # Mercado
    # --------------------------------------------------------

    market = download_sp500()

    market = calculate_market_features(
        market
    )

    # --------------------------------------------------------
    # FRED
    # --------------------------------------------------------

    fred_data = download_all_fred()

    macro = merge_fred_series(
        fred_data
    )

    macro = calculate_monetary_features(
        macro
    )

    macro = calculate_inflation_features(
        macro
    )

    macro = calculate_labor_features(
        macro
    )

    macro = calculate_industrial_features(
        macro
    )

    # --------------------------------------------------------
    # CAPE
    # --------------------------------------------------------

    try:

        shiller = download_shiller()

    except Exception as error:

        _print("")
        _print("⚠️ CAPE indisponível.")
        _print(str(error))

        shiller = pd.DataFrame(
            columns=["date", "cape"]
        )

    # --------------------------------------------------------
    # MERGE
    # --------------------------------------------------------

    master = pd.merge(
        market,
        macro,
        on="date",
        how="left",
    )

    if not shiller.empty:

        master = pd.merge(
            master,
            shiller,
            on="date",
            how="left",
        )

    else:

        master["cape"] = np.nan

    master = (
        master
        .sort_values("date")
        .drop_duplicates("date")
        .reset_index(drop=True)
    )

    # --------------------------------------------------------
    # IMPORTANTE
    #
    # Macro mensal possui publicação defasada.
    # NÃO fazemos bfill.
    #
    # Forward-fill limitado evita usar informação futura.
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

    for column in macro_columns:

        if column in master.columns:

            master[column] = (
                master[column]
                .ffill(limit=3)
            )

    # CAPE também é mensal.
    if "cape" in master.columns:

        master["cape"] = (
            master["cape"]
            .ffill(limit=3)
        )

    # --------------------------------------------------------
    # CAPE percentile
    # --------------------------------------------------------

    master = calculate_cape_percentile(
        master
    )

    _print("")
    _print("=" * 80)
    _print("MASTER DATASET")
    _print("=" * 80)

    _print(
        f"Período: "
        f"{master['date'].min().date()} → "
        f"{master['date'].max().date()}"
    )

    _print(
        f"Meses: {len(master):,}"
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

    for column, label in columns.items():

        if column not in master.columns:
            continue

        valid = master[
            ["date", column]
        ].dropna()

        if valid.empty:
            continue

        last = valid.iloc[-1]

        rows.append({

            "series": label,

            "last_valid_date":
                last["date"],

            "last_value":
                last[column],

            "observations":
                len(valid),
        })

    audit = pd.DataFrame(rows)

    return audit


# ============================================================
# ÚLTIMO ESTADO DISPONÍVEL
# ============================================================

def get_latest_state(
    master: pd.DataFrame
) -> pd.Series:

    if master.empty:

        raise RuntimeError(
            "Master dataset vazio."
        )

    return master.iloc[-1].copy()


# ============================================================
# TESTE ISOLADO
# ============================================================

if __name__ == "__main__":

    master = build_master_dataset()

    audit = freshness_audit(
        master
    )

    print("")
    print("=" * 80)
    print("AUDITORIA DE FRESCOR")
    print("=" * 80)

    print(
        audit.to_string(
            index=False
        )
    )

    print("")
    print("=" * 80)
    print("ÚLTIMO ESTADO")
    print("=" * 80)

    latest = get_latest_state(
        master
    )

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

            print(
                f"{column:30s}: "
                f"{latest[column]}"
            )

    print("")
    print(
        "✅ market_data.py executado."
    )
