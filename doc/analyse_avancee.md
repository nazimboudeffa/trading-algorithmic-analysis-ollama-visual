# Analyse Price Action multi-timeframe (`04_signal_price_action.ipynb`)

Analyse approfondie d'**une seule paire** sur 4 timeframes (M15, H1, Daily, Weekly) produisant un **signal YAML Price Action pur** envoyé à un LLM local (Ollama) qui répond en **Markdown**.

Le signal ne contient que les données de **lecture du prix** (structure, tendance, zones, chandeliers, ATR). Les indicateurs statistiques (RSI, MACD, ADX, DI+, Momentum) ont été retirés du YAML : ils polluent une lecture Price Action pure. L'IA décide elle-même de l'entrée, du SL/TP et du RR.

---

## 1. Architecture du notebook (11 cellules)

| Cellule | Contenu |
|---|---|
| 0 | Configuration : `SYMBOL`, `FULL_NAME`, timeframes `TFS` |
| 1 | Imports (pandas, numpy, `ta`, `yaml`, `requests`, `lib.*`) |
| 2 | Téléchargement des données (cache 60 min) pour les 4 timeframes |
| 3 | Indicateurs internes + définition `PIP_SIZE` / `pips()` |
| 4 | Structure, tendance (score), EMA, volume, volatilité |
| 5 | Détection de patterns candlestick enrichie (index de bougie) |
| 6 | Smart Money : Order Blocks, FVG, liquidité |
| 7 | Supports / résistances les plus proches (distance en pips) |
| 8 | Calculs internes (zones, risque ATR) — **non envoyés à l'IA** |
| 9 | Construction du signal YAML Price Action + affichage |
| 10 | Envoi à l'IA (prompt Price Action, réponse Markdown brute) + sauvegarde |

---

## 2. Configuration

```python
SYMBOL = "GBPUSD"      # EURUSD, USDJPY, GBPUSD, USDCHF, AUDUSD, USDCAD, NZDUSD...
FULL_NAME = "GBP/USD"

TFS = {
    "M15":    {"interval": "15m", "period": "5d"},
    "H1":     {"interval": "1h",  "period": "1mo"},
    "Daily":  {"interval": "1d",  "period": "1y"},
    "Weekly": {"interval": "1W",  "period": "2y"},
}
```

> **Note** : yfinance ne supporte pas l'intervalle `4h`. Le timeframe hebdomadaire (`1W`, 2 ans) est utilisé à la place.

### Taille d'un pip

```python
PIP_SIZE = 0.01 if "JPY" in SYMBOL else 0.0001
```

Les paires JPY ont 2 décimales (USDJPY = 157.39), les autres 4 (EURUSD = 1.1527).

---

## 3. Tendance (direction + force + score)

La tendance est calculée en interne (score à partir de MACD, RSI, EMA20, DI+/DI-) mais seuls la **direction**, la **force** et le **score** sont exposés dans le YAML :

| Résultat | Valeur |
|---|---|
| `direction` | `Bullish` si score ≥ 1.5, `Bearish` si ≤ -1.5, sinon `Neutral` |
| `strength` | `Strong` si ADX ≥ 30, `Moderate` si ≥ 20, sinon `Weak` |
| `score` | arrondi à 0.1 |

La **structure de marché** (`analyze_market_structure`) donne par ailleurs :
`Uptrend (Higher Highs)` / `Downtrend (Lower Lows)` / `Consolidation (Ranging)`.

---

## 4. Analyse EMA

Calculée sur Daily et H1 uniquement :

```python
alignement Bullish : EMA20 > EMA50 > EMA100 > EMA200
alignement Bearish : EMA20 < EMA50 < EMA100 < EMA200
sinon               : Mixed
```

`price_position` = nombre d'EMA sous le prix courant :

| Compteur (EMA sous le prix) | Position |
|---|---|
| 4 | `Above EMA20` |
| 3 | `Between EMA20 and EMA50` |
| 2 | `Between EMA50 and EMA100` |
| 1 | `Between EMA100 and EMA200` |
| 0 | `Below EMA200` |

> L'EMA est **optionnelle** pour une lecture Price Action pure mais reste fournie comme contexte de tendance.

---

## 5. Patterns candlestick enrichis (M15)

`detect_patterns_avances()` — fenêtre de 10 bougies, chaque pattern porte l'**index de bougie** (négatif : -1 = dernière bougie) :

| Pattern | Condition (sur le corps/ombres) | Signal |
|---|---|---|
| Doji | corps / range < 0.1 | Indecision |
| Hammer | ombre basse > 2×corps, ombre haute < corps | Bullish Reversal |
| Shooting Star | ombre haute > 2×corps, ombre basse < corps | Bearish Reversal |
| Pin Bar | ombres haute ET basse > 2×corps | Reversal |
| Bullish Engulfing | barre verte engloutit la barre rouge précédente | Bullish Reversal |
| Bearish Engulfing | barre rouge engloutit la verte précédente | Bearish Reversal |
| Inside Bar | H ≤ H_prev et L ≥ L_prev | Compression |
| Outside Bar | H ≥ H_prev et L ≤ L_prev | Expansion |
| Morning Star | bougie étoile + 3ᵉ barre > milieu de la 1ʳᵉ | Bullish Reversal |

---

## 6. Smart Money Concepts

### Order Blocks (sur H1)

```python
move = close[i+1] - close[i]
if  move > +1.5 * ATR and bougie[i] baissière  → Order Block HAUSSIER  (high[i])
elif move < -1.5 * ATR and bougie[i] haussière  → Order Block BAISSIER  (low[i])
```

- Déduplication (arrondi à 5 décimales)
- Niveaux présents **dans les deux** listes → `role_change_levels` (servent de support **et** de résistance)

### Fair Value Gaps (FVG) (sur H1)

```python
l2 > h1  → FVG haussier, zone (h1, l2)
h2 < l1  → FVG baissier, zone (h2, l1)
```

### Liquidité (sur M15)

```python
tol = 0.5 × ATR
equal_highs = plus grand nombre de highs à moins de tol l'un de l'autre
equal_lows  = idem pour les lows
liquidity_above = equal_highs >= 2
liquidity_below = equal_lows >= 2
sweep_above     = dernier high > max(highs précédents)   # chasse au-dessus
sweep_below     = dernier low  < min(lows précédents)    # chasse en dessous
```

---

## 7. Supports / Résistances proches

Depuis les niveaux M15 (`find_support_resistance`) :

- support le plus proche **sous** le prix, résistance la plus proche **au-dessus**
- distance convertie en **pips** avec `pips()`

---

## 8. Structure du YAML généré (Price Action pur)

```
pair
├── price          current, spread
├── session        name
├── timeframes     analyzed, interval, period
├── structure      M15/H1/Daily/Weekly
├── trend          direction, strength, score (par TF)
├── atr            M15/H1/Daily/Weekly
├── ema            Daily/H1 : alignment, price_position, EMA20/50/100/200
├── support        nearest : exists, price, strength, distance_pips, reason
├── resistance     nearest : idem
├── smart_money    order_blocks (bullish/bearish/role_change_levels),
│                  liquidity (equal_highs/lows, liquidity_above/below, sweeps),
│                  fvg (bullish/bearish : exists, zone)
└── candlestick    patterns.recent (candle, pattern, signal), timeframe
```

**Retirés du YAML** (pollution statistique ou décision pré-calculée) :
`volatility`, `indicators` (RSI, MACD, ADX, DI+, DI-, Momentum, Volume), `probabilities`, `signals`, `analysis`, `entry`, `risk`, `news`.

L'IA reçoit uniquement **où est le prix, quelle est la structure, où sont les zones**, et décide elle-même entrée / SL / TP / RR.

### Exemple réel (GBPUSD, août 2026)

```yaml
pair: GBPUSD (GBP/USD)
price:
  current: 1.34867
  spread: 0.8
session:
  name: Asian
trend:
  M15: {direction: Bullish, strength: Strong, score: 1.5}
  H1: {direction: Bullish, strength: Moderate, score: 3.5}
  Daily: {direction: Bullish, strength: Weak, score: 3.5}
  Weekly: {direction: Bullish, strength: Weak, score: 2.5}
atr: {M15: 0.000698, H1: 0.00163, Daily: 0.008372, Weekly: 0.018725}
ema:
  Daily: {alignment: Mixed, price_position: Above EMA20}
  H1: {alignment: Bullish, price_position: Above EMA20}
support:
  nearest: {exists: true, price: 1.32871, strength: Medium, distance_pips: 199.6}
resistance:
  nearest: {exists: false, price: null, reason: No resistance identified above current price}
smart_money:
  order_blocks:
    bullish: [1.33957, 1.3432]
    bearish: []
    role_change_levels: []
  liquidity:
    equal_highs: 10
    equal_lows: 11
    liquidity_above: true
    liquidity_below: true
  fvg:
    bullish: {exists: true, zone: {low: 1.34862, high: 1.34867}}
    bearish: {exists: true, zone: {low: 1.34284, high: 1.34441}}
candlestick:
  patterns:
    recent:
    - candle: -9
      pattern: Hammer
      signal: Bullish Reversal
    - candle: -8
      pattern: Hammer
      signal: Bullish Reversal
    - candle: -7
      pattern: Bearish Engulfing
      signal: Bearish Reversal
    - candle: -5
      pattern: Morning Star
      signal: Bullish Reversal
    - candle: -3
      pattern: Bearish Engulfing
      signal: Bearish Reversal
    timeframe: M15
```

---

## 9. Passage à l'IA et affichage du rapport

Le YAML est sérialisé (`yaml.dump`) et injecté dans le prompt (cf. [prompt_ia.md](prompt_ia.md)). La réponse du modèle est **Markdown brut** affichée telle quelle dans l'onglet « Analyse IA » du logiciel (intra logiciel, aucun fichier n'est écrit) :

```python
ai_result = ask_ai(yaml.dump(signal_yaml, sort_keys=False, allow_unicode=True))
```

Paramètres de l'appel :

| Paramètre | Valeur |
|---|---|
| `model` | `gemma4` (configurable dans `lib/ai.py`) |
| `stream` | `false` |
| `format` | **non défini** (réponse texte libre, pas de JSON forcé) |
| `temperature` | 0.2 |
| `num_predict` | 2500 |
| `timeout` | 120 s |

---

## Fichiers impliqués

| Fichier | Rôle |
|---|---|
| `04_signal_price_action.ipynb` | Notebook Price Action multi-timeframe |
| `lib/data.py` | Fetch OpenBB + cache |
| `lib/analysis.py` | Structure de marché, S/R |
| `lib/ai.py` | `MODEL`, `OLLAMA_URL` |
| `doc/prompt_ia.md` | Prompt Price Action (sortie Markdown) |
