# Indicateurs Techniques

Utilisés sur le timeframe **daily** pour définir le contexte macro du signal.

---

## 1. RSI — Relative Strength Index

**Période** : 14 (standard)

### Calcul

1. Pour chaque barre, on calcule la variation du close :

```
delta = Close[t] - Close[t-1]
```

2. On sépare les gains et pertes sur 14 périodes :

```
gain = delta  si delta > 0, sinon 0
loss = -delta si delta < 0, sinon 0
```

3. Moyenne lissée (Wilder smoothing) — *non pas SMA, mais RMA* :

```
avg_gain[t] = (avg_gain[t-1] * 13 + gain[t]) / 14
avg_loss[t] = (avg_loss[t-1] * 13 + loss[t]) / 14
```

4. Ratio et RSI final :

```
rs = avg_gain / avg_loss
rsi = 100 - (100 / (1 + rs))
```

### Interprétation

| Valeur | Lecture |
|---|---|
| > 70 | Suracheté (Overbought) |
| < 30 | Survente (Oversold) |
| 30–70 | Neutre |

### Dans le code

`lib/analysis.py` utilise `ta.momentum.RSIIndicator(close, window=14).rsi()`.
La valeur est arrondie à 1 décimale avant d'être transmise à l'IA.

---

## 2. MACD — Moving Average Convergence Divergence

**Paramètres** : 12 / 26 / 9 (standard)

### Calcul

1. **MACD line** : différence entre EMA rapide (12) et EMA lente (26)

```
macd_line = EMA(close, 12) - EMA(close, 26)
```

2. **Signal line** : EMA 9 de la MACD line

```
signal_line = EMA(macd_line, 9)
```

3. **Histogram** (non utilisé dans le signal) :

```
histogram = macd_line - signal_line
```

Les EMA utilisent le facteur de lissage :

```
α = 2 / (période + 1)
EMA[t] = close[t] * α + EMA[t-1] * (1 - α)
```

### Interprétation

| Condition | Valeur |
|---|---|
| MACD line > Signal line | `"bullish"` |
| MACD line < Signal line | `"bearish"` |

### Dans le code

```python
macd = ta.trend.MACD(close=df["Close"])
df["macd"] = macd.macd()
df["macd_signal"] = macd.macd_signal()
```

Comparaison sur la dernière barre uniquement.

---

## 3. MA20 — Moyenne Mobile 20 périodes

**Période** : 20 (standard)

### Calcul

SMA simple (chacune des 20 valeurs a le même poids) :

```
MA20[t] = (Close[t] + Close[t-1] + ... + Close[t-19]) / 20
```

### Interprétation

| Condition | Valeur |
|---|---|
| Close > MA20 | `"uptrend"` (tendance haussière) |
| Close < MA20 | `"downtrend"` (tendance baissière) |

### Pourquoi 20 périodes

Sur un graphique daily, 20 bougies ≈ **1 mois de trading** (environ 21 jours ouvrés). C'est l'horizon utilisé pour `period="1mo"` lors du fetch daily, donc la MA20 couvre la totalité des données chargées.

---

## 4. Dans le pipeline

Ces 3 indicateurs sont calculés dans la cellule d'analyse daily de chaque notebook :

```python
df_daily["rsi"] = ta.momentum.RSIIndicator(close=df_daily["Close"], window=14).rsi()
df_daily["macd"] = macd.macd()
df_daily["macd_signal"] = macd.macd_signal()
df_daily["ma20"] = df_daily["Close"].rolling(20).mean()

last = df_daily.iloc[-1]
daily_rsi    = round(float(last["rsi"]), 1)
daily_macd   = "bullish" if last["macd"] > last["macd_signal"] else "bearish"
daily_trend  = "uptrend" if float(last["Close"]) > float(last["ma20"]) else "downtrend"
```

Ils sont ensuite injectés dans le signal transmis à l'IA :

```json
{
  "daily_rsi": 38.3,
  "daily_macd": "bearish",
  "daily_trend": "downtrend"
}
```
