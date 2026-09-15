# Méthode Price Action du projet

Explication de la méthode d'analyse Price Action utilisée par le notebook `04_signal_price_action.ipynb` et documentée dans ce dossier.

---

## 1. Philosophie de base

L'analyse se base **uniquement sur le comportement du prix** : structure, zones, réaction du prix, figures de chandeliers.

Les indicateurs statistiques (RSI, MACD, ADX, DI+, Momentum) sont calculés en interne mais **retirés du signal envoyé à l'IA** : ils polluent une lecture Price Action pure. L'IA reçoit uniquement *où est le prix, quelle est la structure, où sont les zones*, et décide elle-même entrée / SL / TP / RR.

---

## 2. Pipeline

1. **4 timeframes** — M15 (5j), H1 (1mois), Daily (1an), Weekly (2ans)
2. Extraction de la **lecture du prix** → signal **YAML**
3. Envoi à un LLM local (Ollama, `gemma4`) avec un prompt de "trader Price Action"
4. Réponse **Markdown** → affichée dans l'onglet du logiciel (intra logiciel, sans fichier)

```
Données (cache 60 min)
      │
      ▼
Analyse (structure, tendance, zones, chandeliers, SMC)
      │
      ▼
Signal YAML (Price Action pur)
      │
      ▼
Prompt IA → réponse Markdown
      │
      ▼
Affichage dans l'onglet (intra logiciel)
```

---

## 3. Concepts clés

### 3.1 Structure de marché

Le contexte d'abord :

- `Higher High / Higher Low` → tendance haussière
- `Lower High / Lower Low` → tendance baissière
- Absence de structure claire → **range**

### 3.2 Tendance

Chaque timeframe expose :

| Champ | Valeur |
|---|---|
| `direction` | `Bullish` / `Bearish` / `Neutral` |
| `strength` | `Strong` (ADX ≥ 30) / `Moderate` (≥ 20) / `Weak` |
| `score` | arrondi à 0.1 |

Données contextuelles uniquement — aucune décision pré-calculée.

### 3.3 Supports / Résistances

Niveaux M15 les plus proches : support sous le prix, résistance au-dessus, avec **distance en pips** (`PIP_SIZE = 0.01` pour les JPY, `0.0001` sinon). Détails dans `support_resistance.md`.

### 3.4 Patterns de chandeliers (M15)

Détectés sur les 10 dernières bougies, chaque pattern porte un index de bougie (`-1` = dernière bougie) :

| Pattern | Condition | Signal |
|---|---|---|
| Doji | corps / range < 0.1 | Indécision |
| Hammer | mèche basse > 2×corps, mèche haute < corps | Retournement haussier |
| Shooting Star | mèche haute > 2×corps, mèche basse < corps | Retournement baissier |
| Pin Bar | mèches haute ET basse > 2×corps | Rejet |
| Bullish Engulfing | bougie verte engloutit la rouge précédente | Retournement haussier fort |
| Bearish Engulfing | bougie rouge engloutit la verte précédente | Retournement baissier fort |
| Inside Bar | H ≤ H_prev et L ≥ L_prev | Compression |
| Outside Bar | H ≥ H_prev et L ≤ L_prev | Expansion |
| Morning Star | étoile + 3ᵉ bougie > milieu de la 1ʳᵉ | Retournement haussier |

Détails : `candlestick_patterns.md`.

### 3.5 Smart Money Concepts (SMC)

**Order Blocks** (H1) — la dernière bougie avant un fort déplacement :

```
move = close[i+1] - close[i]
move >  +1.5 × ATR et bougie[i] baissière  → Order Block HAUSSIER
move <  -1.5 × ATR et bougie[i] haussière  → Order Block BAISSIER
```

Un niveau présent dans les deux listes devient `role_change_levels` (support **et** résistance).

**Fair Value Gap / FVG** (H1) — déséquilibre à 3 bougies :

```
l2 > h1  → FVG haussier, zone (h1, l2)   # gap au-dessus
h2 < l1  → FVG baissier, zone (h2, l1)   # gap en dessous
```

Zone de prix "injuste" que le marché tend à retester avant de continuer.

**Liquidité** (M15) — où se trouvent les stop-loss des autres traders :

```
tol = 0.5 × ATR
equal_highs / equal_lows = nombre de sommets/creux groupés
liquidity_above = equal_highs ≥ 2        # buy stops au-dessus
liquidity_below = equal_lows ≥ 2         # sell stops en dessous
sweep_above     = dernier high > max(highs précédents)   # chasse au-dessus
sweep_below     = dernier low  < min(lows précédents)    # chasse en dessous
```

Les acteurs institutionnels chassent ces zones (sweeps) avant d'inverser le prix.

---

## 4. Règles de décision (prompt IA)

Priorité **A → E** :

- **A. Structure** — déterminer le contexte : tendance, range, cassure, retournement potentiel.
- **B. Zones** — support, résistance, order block, FVG, liquidité au-dessus et en dessous.
- **C. Réaction du prix** — rejet d'une zone, pin bar, engulfing, cassure + retest, sweep de liquidité.
- **D. Entrée** — **jamais au milieu d'un range** :
  - achat sur support après confirmation
  - vente sur résistance après confirmation
  - cassure uniquement après clôture et retest
- **E. Gestion du risque** :
  - **SL** derrière : dernier swing, zone d'invalidation, order block
  - **TP** vers : prochaine liquidité, support/résistance opposé, FVG
  - aucune configuration claire → **HOLD**

---

## 5. Exemple concret (rapport EURUSD, août 2026)

Le rapport lit une **consolidation (Range)** sur tous les timeframes, avec un conflit entre tendance haussière H1/Daily et pression vendeuse M15. Le signal le plus récent est un Bearish Engulfing mais le prix est au milieu du range, près du sommet du FVG haussier.

Décision : **HOLD** — "Le conflit entre la tendance haussière H1/Daily et la pression vendeuse M15 n'est pas suffisamment fort pour justifier une entrée immédiate. Attendre qu'une cassure (breakout) ou un rejet clair de l'une des zones clés soit confirmé par une clôture sur M15."

Résumé : le code extrait objectivement l'état du marché, l'IA applique la logique de trading (entrée / SL / TP / RR) sans forcer de réponse statistique.

---

## Fichiers liés

| Fichier | Rôle |
|---|---|
| `04_signal_price_action.ipynb` | Notebook Price Action multi-timeframe |
| `analyse_avancee.md` | Analyse avancée (détail technique du notebook) |
| `prompt_ia.md` | Prompt Price Action (règles A→E, format de réponse) |
| `candlestick_patterns.md` | Patterns de chandeliers |
| `support_resistance.md` | Algorithme S/R |
| `lib/analysis.py` | Structure de marché, S/R |
| `lib/ai.py` | `MODEL`, `OLLAMA_URL` |
