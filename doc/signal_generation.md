# Processus de génération d'un signal trading avec l'IA

## Vue d'ensemble

```
Données marché (EUR/USD)
        │
        ▼
  1. Fetch OHLC ────► Cache pickle (60 min)
        │
        ▼
  2. Analyse technique
        │
        ├──► Indicateurs (RSI, MACD, MA20)
        ├──► Market Structure (swings, tendance)
        ├──► Support / Résistance (pivots clustering)
        └──► Patterns bougies (doji, engulfing, etc.)
        │
        ▼
  3. Construction du signal
        │
        └──► Signal structuré (prix, biais, niveaux, patterns)
        │
        ▼
  4. Prompt IA
        │
        └──► Envoi à Ollama (modèle local)
        │
        ▼
  5. Parsing JSON
        │
        └──► Extraction signal, confiance, SL/TP
        │
        ▼
  6. Affichage résultat
```

---

## 1. Récupération des données (`lib/data.py`)

```python
df = get_cached_data("EURUSD=X", interval="5m", period="1d")
```

- Appel **OpenBB** (`obb.currency.price.historical()`) avec le provider `yfinance`
- Résultat converti en **DataFrame pandas** (colonnes : Open, High, Low, Close, Volume)
- **Cache pickle** dans `data_cache/` — durée de vie : 60 minutes
- Si le cache est valide, pas de téléchargement

### Timeframes disponibles

| Paramètre | Usage | Exemple |
|---|---|---|
| `interval="5m"` | Intraday (signal) | 1 jour de données |
| `interval="1h"` | Tendance moyen terme | 1 mois de données |
| `interval="1d"` | Tendance long terme | 1 mois de données |
| `period="1d"` | Période de données | 1d, 5d, 1mo, 3mo |

---

## 2. Analyse technique

### Market Structure (`analyze_market_structure()`)

Analyse les 20 dernières barres pour déterminer la tendance :

```python
higher_highs = count(highs[i] > highs[i-1])  # sur 20 barres
lower_lows  = count(lows[i] < lows[i-1])

if higher_highs > lower_lows * 1.5  → "Uptrend (Higher Highs)"   → bias Bullish
if lower_lows > higher_highs * 1.5  → "Downtrend (Lower Lows)"   → bias Bearish
sinon                                → "Consolidation (Ranging)" → bias Neutral
```

### Support / Résistance (`find_support_resistance()`)

Cf. [doc/support_resistance.md](support_resistance.md)

Algorithme en résumé :
1. **Fenêtre adaptative** selon le nombre de barres
2. **Détection des swing highs/lows** (pivots)
3. **Clustering** des pivots proches (seuil basé sur l'ATR)
4. **Score** = nombre de touches (pivots dans le cluster)
5. **Top 5** niveaux retournés

### Patterns bougies (`detect_candlestick_patterns()`)

Patterns détectés sur chaque barre :

| Pattern | Signal |
|---|---|
| Doji | Indecision |
| Hammer | Bullish Reversal |
| Shooting Star | Bearish Reversal |
| Bullish Engulfing | Bullish Reversal |
| Bearish Engulfing | Bearish Reversal |

---

## 3. Construction du signal (`build_price_action_signal()`)

Assemble toutes les analyses en un dictionnaire structuré :

```python
{
    "pair": "EUR/USD",
    "price": 1.14116,
    "session": "London",           # Asian / London / New York
    "market_structure": "Uptrend (Higher Highs)",
    "bias": "Bullish",
    "price_range_pct": 0.21,
    "recent_patterns": ["Doji (Indecision)"],
    "nearest_support": 1.13950,
    "support_strength": "Strong",
    "dist_to_support_pct": 0.15,
    "nearest_resistance": 1.14200,
    "resistance_strength": "Medium",
    "dist_to_resistance_pct": 0.07
}
```

En mode multi-timeframe, le signal est enrichi avec le contexte des timeframes supérieures :

```python
signal["htf_daily_bias"] = "Bullish"
signal["htf_1h_bias"] = "Neutral"
signal["daily_support"] = [1.1350, 1.1300]
signal["daily_resistance"] = [1.1450, 1.1500]
```

---

## 4. Envoi à l'IA (`lib/ai.py`)

Le signal est envoyé à **Ollama** (modèle local, `gemma4`) via une requête HTTP :

```python
POST http://localhost:11434/api/generate
{
    "model": "gemma4",
    "prompt": "...",
    "stream": false,
    "format": "json",
    "options": { "temperature": 0.1, "num_predict": 500 }
}
```

### Prompt IA

```
Analyze this forex price action data and provide a trading signal.

Data:
{signal_data en JSON}

Rules:
- HOLD → set entry, stop_loss, take_profit to null
- BUY  → take_profit > entry > stop_loss
- SELL → stop_loss > entry > take_profit

Use 5 decimals for prices.
Respond with JSON only:
{"signal": "BUY or SELL or HOLD", "confidence": 0-100,
 "reason": "brief reason", "entry": null,
 "stop_loss": null, "take_profit": null}
```

### Paramètres du modèle

| Paramètre | Valeur | Effet |
|---|---|---|
| `temperature` | 0.1 | Réponses déterministes et cohérentes |
| `format` | `json` | Force la sortie en JSON |
| `num_predict` | 500 | Limite de tokens suffisante |

---

## 5. Parsing de la réponse

```python
response → JSON parsing → {"signal": "BUY", "confidence": 85, ...}
```

Gestion des erreurs :
- Réponse vide → erreur
- JSON invalide → tentative d'extraction avec regex `\{...\}`
- Timeout / connexion → message d'erreur explicite

---

## 6. Affichage du résultat

L'IA décide du signal final. Les prix sont formatés avec 5 décimales.

### Exemple de sortie

```
🤖 AI ANALYSIS:
   Signal:          BUY 🟢
   Confidence:      85% (HIGH)
   Reason:          Uptrend with bullish MACD and strong support

   Entrée:          1.15100
   Stop Loss:       1.14900
   Take Profit:     1.15500
```

Pour un signal HOLD, les champs entry/SL/TP ne sont pas affichés.

---

## Fichiers impliqués

| Fichier | Rôle |
|---|---|
| `lib/data.py` | Récupération et cache des données |
| `lib/analysis.py` | Analyse technique (S/R, structure, patterns) |
| `lib/ai.py` | Interaction avec Ollama |
| `analyse_multi_tf.ipynb` | Notebook multi-timeframe |
| `trading-analysis.ipynb` | Notebook indicateurs techniques |
| `price-action-analysis.ipynb` | Notebook price action |
