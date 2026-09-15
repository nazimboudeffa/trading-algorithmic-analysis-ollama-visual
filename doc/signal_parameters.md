# Paramètres du signal envoyé à l'IA

Le signal est un dictionnaire Python transmis à `analyze_with_ai()` dans `lib/ai.py`.  
Il contient toutes les données techniques et contextuelles nécessaires à l'analyse.

---

## 1. Identité de la paire

| Champ | Type | Exemple | Description |
|---|---|---|---|
| `pair` | `string` | `"EURUSD (EUR/USD)"` | Paire traitée |

---

## 2. Prix et session

| Champ | Type | Exemple | Description |
|---|---|---|---|
| `price` | `float` | `1.14116` | Dernier cours de clôture (5 décimales) |
| `session` | `string` | `"London"` | Session de marché actuelle |

Valeurs possibles pour `session` : `"Asian"` (00h-07h UTC), `"London"` (07h-16h UTC), `"New York"` (13h-22h UTC).

---

## 3. Structure de marché (intraday)

| Champ | Type | Exemple | Description |
|---|---|---|---|
| `market_structure` | `string` | `"Uptrend (Higher Highs)"` | Structure des 20 dernières barres 5m |
| `bias` | `string` | `"Bullish"` | Biais directionnel intraday |
| `price_range_pct` | `float` | `0.21` | Range prix en % |

### Valeurs possibles

| `market_structure` | `bias` | Signification |
|---|---|---|
| `"Uptrend (Higher Highs)"` | `"Bullish"` | Hausse : plus de higher highs que de lower lows |
| `"Downtrend (Lower Lows)"` | `"Bearish"` | Baisse : plus de lower lows que de higher highs |
| `"Consolidation (Ranging)"` | `"Neutral"` | Range : pas de tendance claire |

> Calcul : `higher_highs > lower_lows * 1.5` → uptrend, inversement pour downtrend.

---

## 4. Indicateurs techniques (daily)

| Champ | Type | Exemple | Description |
|---|---|---|---|
| `daily_rsi` | `float` | `38.3` | RSI 14 périodes sur données daily |
| `daily_macd` | `string` | `"bearish"` | MACD vs signal line |
| `daily_trend` | `string` | `"downtrend"` | Prix vs MA20 |

### daily_macd

| Valeur | Signification |
|---|---|
| `"bullish"` | MACD > signal line (momentum haussier) |
| `"bearish"` | MACD < signal line (momentum baissier) |

### daily_trend

| Valeur | Signification |
|---|---|
| `"uptrend"` | Prix > MA20 (tendance haussière) |
| `"downtrend"` | Prix < MA20 (tendance baissière) |

---

## 5. Niveaux de support et résistance

### Support / Résistance les plus proches (intraday 5m)

| Champ | Type | Exemple | Description |
|---|---|---|---|
| `nearest_support` | `float` | `1.13950` | Support le plus proche sous le prix |
| `support_strength` | `string` | `"Strong"` | Force du support |
| `dist_to_support_pct` | `float` | `0.15` | Distance % au support |
| `nearest_resistance` | `float` | `1.14200` | Résistance la plus proche au-dessus du prix |
| `resistance_strength` | `string` | `"Medium"` | Force de la résistance |
| `dist_to_resistance_pct` | `float` | `0.07` | Distance % à la résistance |

### Force des niveaux

| Valeur | Critère |
|---|---|
| `"Strong"` | ≥ 3 pivots dans le cluster |
| `"Medium"` | 2 pivots |
| `"Weak"` | 1 pivot |

---

## 6. Contexte multi-timeframe (HTF)

Ajouté par `analyse_multi_tf.ipynb` et `scan_paires.ipynb`.

| Champ | Type | Exemple | Description |
|---|---|---|---|
| `htf_daily_bias` | `string` | `"Neutral"` | Biais directionnel daily (1mo) |
| `htf_daily_structure` | `string` | `"Consolidation (Ranging)"` | Structure daily |
| `htf_1h_bias` | `string` | `"Bullish"` | Biais directionnel 1h (1mo) |
| `htf_1h_structure` | `string` | `"Uptrend (Higher Highs)"` | Structure 1h |
| `daily_support` | `list[float]` | `[1.1350, 1.1300]` | Top 2 supports daily |
| `daily_resistance` | `list[float]` | `[1.1450, 1.1500]` | Top 2 résistances daily |
| `hourly_support` | `list[float]` | `[1.1380, 1.1360]` | Top 2 supports 1h |
| `hourly_resistance` | `list[float]` | `[1.1430, 1.1450]` | Top 2 résistances 1h |

---

## 7. Candlestick patterns

| Champ | Type | Exemple | Description |
|---|---|---|---|
| `recent_patterns` | `list[string]` | `["Doji (Indecision)"]` | Patterns des 5 dernières barres 5m |

Patterns possibles :

| Pattern | Signal |
|---|---|
| `"Doji (Indecision)"` | Indécision |
| `"Hammer (Bullish Reversal)"` | Retournement haussier |
| `"Shooting Star (Bearish Reversal)"` | Retournement baissier |
| `"Bullish Engulfing (Bullish Reversal)"` | Retournement haussier fort |
| `"Bearish Engulfing (Bearish Reversal)"` | Retournement baissier fort |

---

## Exemple complet de signal

```json
{
  "pair": "EURUSD (EUR/USD)",
  "price": 1.14116,
  "session": "London",
  "market_structure": "Uptrend (Higher Highs)",
  "bias": "Bullish",
  "price_range_pct": 0.21,
  "daily_rsi": 38.3,
  "daily_macd": "bearish",
  "daily_trend": "downtrend",
  "nearest_support": 1.13950,
  "support_strength": "Strong",
  "dist_to_support_pct": 0.15,
  "nearest_resistance": 1.14200,
  "resistance_strength": "Medium",
  "dist_to_resistance_pct": 0.07,
  "recent_patterns": ["Doji (Indecision)"],
  "htf_daily_bias": "Neutral",
  "htf_daily_structure": "Consolidation (Ranging)",
  "htf_1h_bias": "Bullish",
  "htf_1h_structure": "Uptrend (Higher Highs)",
  "daily_support": [1.1350, 1.1300],
  "daily_resistance": [1.1450, 1.1500],
  "hourly_support": [1.1380, 1.1360],
  "hourly_resistance": [1.1430, 1.1450]
}
```
