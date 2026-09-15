# Algorithme de détection Support / Résistance

Fonction : `find_support_resistance()` dans `lib/analysis.py`

## Principe général

L'algorithme détecte les niveaux de support et résistance à partir des **swing highs** et **swing lows** (points hauts et bas significatifs) du prix, puis les regroupe en niveaux par **clustering de proximité**.

---

## 1. Fenêtre adaptative (`window`)

La fenêtre détermine le nombre de barres regardées de chaque côté pour identifier un pivot.

```python
window = max(3, min(15, len(df) // 40))
```

| Timeframe | Barres (1 mois) | Fenêtre | Effet |
|---|---|---|---|
| Daily (1d) | ~22 | 3 | Détecte les swings même sur peu de données |
| 1h | ~720 | 15 | Filtre le bruit, ne garde que les swings significatifs |
| 5m intraday | ~288 | 7 | Compromis réactivité / filtrage |

**Règle** : plus la fenêtre est grande, moins on détecte de pivots (seuls les extrêmes locaux marqués sont retenus).

---

## 2. Seuil dynamique (`threshold`)

Le seuil sert à :
1. **Clustering** : deux pivots sont considérés comme un même niveau s'ils sont plus proches que ce seuil
2. **Filtrage** : éviter de créer des niveaux trop proches les uns des autres

### Calcul

```python
atr = (df['High'] - df['Low']).rolling(14, min_periods=1).mean().iloc[-1]
threshold = max(atr * 0.4, price_range * 0.0008)
```

- **ATR** (Average True Range) : volatilité moyenne sur 14 barres
- Seuil = 40% de l'ATR (adapté à la volatilité du timeframe)
- Minimum : 0.08% du range total (évite un seuil trop serré en période de faible volatilité)

| Timeframe | ATR typique (EUR/USD) | Seuil résultant |
|---|---|---|
| Daily | ~0.005 | ~0.002 |
| 1h | ~0.0015 | ~0.0006 |
| 5m | ~0.0004 | ~0.00016 |

---

## 3. Détection des pivots

Un **swing high** (futur niveau de résistance) est détecté quand :

```python
df['High'].iloc[i] == high_slice.max() AND high_slice.max() != high_slice.min()
```

Un **swing low** (futur niveau de support) est détecté quand :

```python
df['Low'].iloc[i] == low_slice.min() AND low_slice.min() != low_slice.max()
```

La condition `max() != min()` évite de créer des pivots sur des zones plates (range_size = 0).

**Exemple visuel** (fenêtre = 3) :

```
Prix     |
         |     H2
         |    / \
         |   /   \     H4
         |  /     \   / \
         | H1      \ /   \
         |          L3    L5
         | L0       L2    L4
         |______________________
          0  1  2  3  4  5  6
```

Pivots détectés : H1, H2 (highs), L2, L3 (lows)

---

## 4. Clustering

Les pivots sont triés par prix puis regroupés si leur distance relative est inférieure au seuil :

```python
clusters = [[pivots[0]]]
for p in pivots[1:]:
    if abs(p - clusters[-1][-1]) / max(clusters[-1][-1], 1e-10) < threshold:
        clusters[-1].append(p)
    else:
        clusters.append([p])
```

**Exemple** avec des pivots resistance à [1.1400, 1.1402, 1.1405, 1.1420, 1.1422] et threshold = 0.0002 :

| Cluster | Pivots fusionnés |
|---|---|
| 1 | 1.1400, 1.1402, 1.1405 → niveau = **1.1402** |
| 2 | 1.1420, 1.1422 → niveau = **1.1421** |

---

## 5. Score des niveaux

Chaque cluster devient un niveau avec :

- **`level`** : moyenne des pivots du cluster
- **`touches`** : nombre de pivots dans le cluster
- **`strength`** : `Strong` (≥ 3 touches), `Medium` (2 touches), `Weak` (1 touche)

Les niveaux sont triés par nombre de touches décroissant et seuls les **5 meilleurs** sont retournés.

---

## Résumé

```
Données OHLC
    │
    ▼
Fenêtre adaptative ───► Détection swing highs/lows
                              │
                              ▼
            Clustering par seuil ATR
                              │
                              ▼
            Score (touches) + tri
                              │
                              ▼
            Top 5 niveaux (S/R)
```
