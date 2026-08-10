# S&P 500 HISTORICAL CYCLE ATLAS

Sistema quantitativo para acompanhamento do ciclo histórico do S&P 500.

O projeto utiliza dados de mercado e dados macroeconômicos para responder a uma pergunta central:

> **Em que estágio do ciclo histórico do S&P 500 estamos?**

O sistema não tenta prever o próximo topo, fundo ou preço do índice.

Seu objetivo é **classificar o regime atual do mercado com base em evidências históricas**.

---

# OBJETIVO

O S&P 500 Historical Cycle Atlas acompanha continuamente:

- tendência do mercado;
- drawdown;
- momentum;
- idade do bull market;
- retorno acumulado do bull market;
- valuation;
- política monetária;
- curva de juros;
- inflação;
- mercado de trabalho;
- Sahm Rule;
- produção industrial.

Essas informações são combinadas para determinar:

- regime de mercado;
- fase do ciclo;
- risco estrutural;
- condição macroeconômica;
- regime operacional;
- existência ou não de deterioração confirmada.

---

# FILOSOFIA

O projeto segue quatro princípios fundamentais.

### 1. Não prever o topo

Valuation elevado não significa que o mercado precisa cair imediatamente.

### 2. Não usar indicador isolado

Mudanças importantes de regime precisam ser confirmadas por múltiplas dimensões.

### 3. Separar valuation de timing

CAPE é utilizado principalmente como indicador de valuation e risco estrutural de longo prazo.

Não é tratado como sinal automático de venda.

### 4. Evidência histórica acima de narrativa

As regras utilizadas pelo sistema são derivadas do estudo histórico do S&P 500.

---

# EVIDÊNCIAS PRINCIPAIS DO ESTUDO

O estudo histórico encontrou evidências importantes.

## Drawdown

A região próxima de:

```text
-15%
```

foi identificada como uma região estrutural relevante de stress.

Isso significa:

```text
Drawdown ≈ -15%
        ↓
REAVALIAÇÃO DO REGIME
```

Não significa compra ou venda automática.

---

## Idade do Bull Market

A idade isolada do bull market apresentou baixa capacidade para determinar o topo.

Portanto:

```text
BULL ANTIGO ≠ TOPO IMINENTE
```

---

## Valuation

O CAPE apresentou relação mais relevante com retornos reais de longo prazo do que com market timing.

Portanto:

```text
CAPE ALTO
   ↓
menor expectativa estrutural de retorno

MAS

CAPE ALTO
   ≠
sinal automático de venda
```

---

## CAPE extremo

CAPE acima de 40 é historicamente raro.

Entretanto, a quantidade de episódios independentes é pequena.

Portanto:

```text
RARIDADE HISTÓRICA
≠
PROBABILIDADE DE CRASH
```

---

## Curva de juros

A transição da curva pode ser mais informativa do que simplesmente observar se ela está invertida.

O sistema acompanha:

```text
NORMAL
FLAT
INVERTED
RE-STEEPENING
```

---

## Sahm Rule

A Sahm Rule é utilizada como indicador de deterioração do mercado de trabalho.

Ela não é utilizada como sinal isolado de venda.

---

## Economic DNA

Foi desenvolvido um modelo de similaridade econômica utilizando múltiplas variáveis.

Entretanto, após validação walk-forward com purging/embargo, o modelo apresentou baixo poder preditivo para retornos futuros.

Por isso:

```text
ECONOMIC DNA
     ↓
CONTEXTO HISTÓRICO

NÃO

PREVISÃO DE RETORNO
```

Similaridade histórica nunca deve ser interpretada como probabilidade.

---

# REGIMES OPERACIONAIS

O Atlas classifica o mercado em regimes.

## GREEN_EXPANSION

Mercado estruturalmente saudável.

Características típicas:

```text
trend positivo
momentum positivo
macro estável
ausência de stress estrutural
```

---

## YELLOW_EXPENSIVE_BULL

Bull market ativo com valuation elevado.

Características típicas:

```text
trend positivo
momentum positivo
valuation extremo
macro ainda construtivo
```

Interpretação:

```text
BULL MARKET
+
VALUATION EXTREMO
+
CAUTELA
```

---

## ORANGE_DETERIORATION

Sinais relevantes de deterioração começam a aparecer.

Pode envolver combinação de:

```text
momentum enfraquecendo
drawdown aumentando
macro deteriorando
inflação problemática
curva de juros deteriorando
```

Exige confirmação por múltiplas dimensões.

---

## RED_STRUCTURAL_STRESS

Regime de stress estrutural.

Pode envolver:

```text
drawdown relevante
deterioração econômica
stress no mercado de trabalho
contração industrial
perda estrutural de momentum
```

---

## BLUE_REASSESS_ACCUMULATION

Regime de reavaliação após stress significativo.

O sistema não interpreta automaticamente grandes quedas como oportunidade.

Primeiro procura sinais de estabilização.

---

## NEUTRAL_UNCERTAIN

Utilizado quando as evidências não permitem classificação suficientemente forte em outro regime.

---

# REGRAS DE GOVERNANÇA

### REGRA 1

Nunca utilizar um único indicador para determinar topo ou fundo.

### REGRA 2

CAPE deve ser interpretado como valuation e expectativa estrutural de longo prazo.

Não como market timing.

### REGRA 3

Drawdown próximo de -15% ativa reavaliação.

Não compra ou venda automática.

### REGRA 4

Idade do bull market não deve ser utilizada isoladamente para determinar encerramento do ciclo.

### REGRA 5

Sahm, produção industrial, inflação e curva de juros são indicadores de regime econômico.

### REGRA 6

Análogos históricos servem para contexto.

Não para previsão pontual.

### REGRA 7

Similaridade histórica não é probabilidade.

### REGRA 8

Modelos preditivos precisam sobreviver a validação walk-forward purgada antes de serem utilizados.

### REGRA 9

Valuation extremo pode persistir enquanto preço, liquidez e economia permanecerem construtivos.

### REGRA 10

Mudança estrutural de regime exige confirmação por múltiplas dimensões.

---

# VARIÁVEIS MONITORADAS

## Mercado

```text
S&P 500
ATH
Drawdown
Momentum 12 meses
Bull age
Bull return
```

## Valuation

```text
CAPE
CAPE percentile
```

## Política monetária

```text
Fed Funds
Mudança Fed Funds 12 meses
```

## Curva de juros

```text
Treasury 10Y
Treasury 2Y
Spread 10Y-2Y
```

## Inflação

```text
CPI YoY
Mudança da inflação
```

## Trabalho

```text
Unemployment Rate
Sahm Rule
```

## Economia real

```text
Industrial Production YoY
```

---

# ESTRUTURA

```text
SP500_CYCLE_ATLAS/
│
├── main.py
├── settings.py
├── market_data.py
├── cycle_engine.py
├── report.py
├── requirements.txt
├── README.md
│
├── data/
│   ├── cycle_history.csv
│   ├── current_state.csv
│   └── current_report.txt
│
└── .github/
    └── workflows/
        └── run.yml
```

---

# ARQUITETURA

```text
MARKET DATA
     │
     ▼
market_data.py
     │
     ▼
MASTER DATASET
     │
     ▼
cycle_engine.py
     │
     ├── mercado
     ├── valuation
     ├── momentum
     ├── drawdown
     ├── monetário
     ├── inflação
     ├── trabalho
     └── produção industrial
     │
     ▼
CYCLE CLASSIFICATION
     │
     ▼
report.py
     │
     ├── current_state.csv
     ├── cycle_history.csv
     └── current_report.txt
```

---

# CURRENT STATE

O arquivo:

```text
data/current_state.csv
```

contém apenas o diagnóstico mais recente.

Exemplo conceitual:

```text
market_regime:
BULL MARKET

cycle_phase:
LATE_EXPANSION / VALUATION_EXTREME

structural_risk:
HIGH

top_timing:
NOT_CONFIRMED

operational_regime:
YELLOW_EXPENSIVE_BULL
```

---

# CYCLE HISTORY

O arquivo:

```text
data/cycle_history.csv
```

mantém o histórico das classificações.

Exemplo:

```text
DATE        REGIME

2026-05     GREEN_EXPANSION
2026-06     GREEN_EXPANSION
2026-07     GREEN_EXPANSION
2026-08     YELLOW_EXPENSIVE_BULL
```

Isso permite acompanhar mudanças estruturais do mercado ao longo do tempo.

---

# INTERPRETAÇÃO DO ATLAS

O sistema procura responder:

```text
1. O bull market continua?

2. Existe deterioração estrutural?

3. O valuation está normal ou extremo?

4. O momentum continua saudável?

5. O mercado de trabalho está deteriorando?

6. A economia real está expandindo ou contraindo?

7. A política monetária está ajudando ou restringindo?

8. A inflação está melhorando ou piorando?

9. A curva de juros está sinalizando stress?

10. Houve mudança confirmada de regime?
```

---

# AUTOMAÇÃO

O GitHub Actions executa:

```text
python main.py
```

automaticamente.

O workflow:

```text
.github/workflows/run.yml
```

realiza:

```text
coleta dos dados
        ↓
auditoria
        ↓
classificação
        ↓
relatório
        ↓
atualização do histórico
        ↓
commit automático
```

Também é possível executar manualmente através de:

```text
GitHub
→ Actions
→ SP500 Cycle Atlas
→ Run workflow
```

---

# IMPORTANTE

O S&P 500 Historical Cycle Atlas é um:

```text
REGIME CLASSIFICATION SYSTEM
```

e não um:

```text
MARKET PREDICTION SYSTEM
```

O Atlas não pretende responder:

```text
"Qual será o preço do S&P 500?"

"Quando exatamente acontecerá o próximo crash?"

"Qual será o mês do próximo topo?"
```

Ele pretende responder:

```text
"Em qual regime estamos?"

"O ciclo continua saudável?"

"O risco estrutural aumentou?"

"As evidências estão deteriorando?"

"O regime mudou?"
```

---

# PRINCÍPIO CENTRAL

> **Não prever. Classificar. Confirmar. Adaptar.**

O objetivo do Atlas é transformar décadas de evidência histórica do S&P 500 em um sistema simples, auditável e disciplinado de acompanhamento do ciclo.
