# Candlestick Patterns

Calculés sur les **5 dernières barres 5m** et ajoutés au signal sous `recent_patterns`.

---

## 1. Primitives

Pour chaque barre `i`, on calcule :

```
body      = |Close[i] - Open[i]|
range     = High[i] - Low[i]

upper_wick = High[i] - max(Open[i], Close[i])
lower_wick = min(Open[i], Close[i]) - Low[i]
```

### Ratio corps / range

```
body_pct = body / range    # 0.0 = doji parfait, 1.0 = marubozu
```

---

## 2. Doji (Indecision)

**Condition** : corps quasi inexistant

```
body / range < 0.10
```

**Lecture** : Indécision entre acheteurs et vendeurs. Souvent un signal de retournement ou de pause.

**Exemple** :

```
    High ───
             |
             │  ← upper_wick
             |
    Open/Close ───┐
                  │  ← corps quasi nul
    Open/Close ───┘
             |
             │  ← lower_wick
             |
     Low ───
```

---

## 3. Hammer (Bullish Reversal)

**Condition** : longue mèche basse, petit corps en haut

```
lower_wick > 2 * body    # mèche basse ≥ 2× le corps
upper_wick < body        # mèche haute < corps
```

**Lecture** : Les vendeurs ont poussé le prix bas, mais les acheteurs ont repris le contrôle et clôturé près du haut. Signal de retournement haussier.

**Exemple** :

```
    High ───
             │
             │  ← upper_wick (petite)
             │
    Close ───┐
             │  ← corps (petit)
    Open  ───┤
             │
             │
             │  ← lower_wick (longue, ≥ 2× body)
             │
             │
     Low ───
```

---

## 4. Shooting Star (Bearish Reversal)

**Condition** : longue mèche haute, petit corps en bas

```
upper_wick > 2 * body    # mèche haute ≥ 2× le corps
lower_wick < body        # mèche basse < corps
```

**Lecture** : Les acheteurs ont poussé le prix haut, mais les vendeurs ont repris le contrôle et clôturé près du bas. Signal de retournement baissier.

**Exemple** :

```
     High ───
              │
              │
              │  ← upper_wick (longue, ≥ 2× body)
              │
              │
    Open  ───┐
             │  ← corps (petit)
    Close ───┤
             │
             │  ← lower_wick (petite)
             │
      Low ───
```

---

## 5. Bullish Engulfing (Bullish Reversal Fort)

**Condition** : bougie verte dont le corps *engloutit* la bougie rouge précédente

```
Close[i-1] < Open[i-1]               # bougie précédente baissière (rouge)
Close[i]   > Open[i]                 # bougie courante haussière (verte)
Open[i]    < Close[i-1]              # ouverture en dessous du close précédent
Close[i]   > Open[i-1]               # clôture au-dessus de l'ouverture précédente
```

**Lecture** : Renversement brutal. Les acheteurs effacent toute la perte précédente. Signal fort.

**Exemple** :

```
     (i-1) Rouge         (i) Verte
    ┌─────────┐
    │         │         ┌─────────────┐
    │         │         │             │
    │  Close  │         │   Close     │
    │         │         │             │
    │         │         │             │
    │  Open   │         │             │
    │         │         │   Open      │
    └─────────┘         └─────────────┘
    Open[i] < Close[i-1]
    Close[i] > Open[i-1]
    La verte engloutit complètement la rouge
```

---

## 6. Bearish Engulfing (Bearish Reversal Fort)

**Condition** : bougie rouge dont le corps *engloutit* la bougie verte précédente

```
Close[i-1] > Open[i-1]               # bougie précédente haussière (verte)
Close[i]   < Open[i]                 # bougie courante baissière (rouge)
Open[i]    > Close[i-1]              # ouverture au-dessus du close précédent
Close[i]   < Open[i-1]               # clôture en dessous de l'ouverture précédente
```

**Lecture** : Les vendeurs effacent tout le gain précédent. Signal fort.

**Exemple** :

```
     (i-1) Verte           (i) Rouge
    ┌─────────────┐
    │             │    ┌─────────┐
    │             │    │         │
    │   Close     │    │  Open   │
    │             │    │         │
    │             │    │         │
    │   Open      │    │  Close  │
    │             │    │         │
    └─────────────┘    └─────────┘
    Open[i] > Close[i-1]
    Close[i] < Open[i-1]
    La rouge engloutit complètement la verte
```

## 7. Force des patterns

| Pattern | Strength |
|---|---|
| Doji | Medium |
| Hammer | Strong |
| Shooting Star | Strong |
| Bullish Engulfing | Very Strong |
| Bearish Engulfing | Very Strong |

La force n'est pas transmise à l'IA actuellement, mais disponible dans le code pour filtrage.

---

## 8. Filtrage : patterns récents

Dans `build_price_action_signal()` :

```python
recent_patterns = [p for p in patterns if p['index'] >= len(df) - 5]
```

Seuls les patterns des **5 dernières barres** sont gardés, pour éviter de signaler un Hammer vieux de 50 bouges.

---

## 9. Code : `detect_candlestick_patterns()`

```python
for i in range(1, len(df)):
    for each bar i:
        body = abs(close - open)
        range_size = high - low

        # Doji
        if body / range_size < 0.10

        # Hammer / Shooting Star
        upper_wick / lower_wick vs body

        # Engulfing (i >= 1)
        compare bar i-1 and i
```

Chaque pattern est ajouté sous forme de dict :

```python
{'index': i, 'pattern': 'Hammer', 'signal': 'Bullish Reversal', 'strength': 'Strong'}
```
