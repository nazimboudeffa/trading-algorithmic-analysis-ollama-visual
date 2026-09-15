# Prompt Price Action (`04_signal_price_action.ipynb` — cellule 10)

Le prompt transforme le modèle local en **trader professionnel spécialisé en Price Action Forex**. Il reçoit un signal YAML réduit (structure, zones, chandeliers, ATR) et répond en **Markdown** avec une lecture pure du comportement du prix — sans indicateurs statistiques.

---

## 1. Règles

- Analyser **uniquement** les informations fournies.
- Déterminer s'il existe une opportunité basée **uniquement** sur :
  - structure du marché
  - supports et résistances
  - zones de liquidité
  - order blocks
  - fair value gaps
  - figures de chandeliers
  - réaction du prix

---

## 2. Priorité d'analyse

**A) Structure du prix**
- Higher High / Higher Low = tendance haussière
- Lower High / Lower Low = tendance baissière
- absence de structure claire = **range**

**B) Zones importantes** — support, résistance, order block, FVG, liquidité au-dessus et en dessous du prix.

**C) Réaction du prix** — rejet d'une zone, pin bar, engulfing, cassure + retest, sweep de liquidité.

**D) Entrée**
- **Ne jamais entrer au milieu d'un range.**
- Privilégier : achat sur support après confirmation, vente sur résistance après confirmation, cassure uniquement après clôture et retest.

**E) Gestion du risque**
- **SL** placé derrière : dernier swing, zone d'invalidation, order block.
- **TP** visant : prochaine liquidité, support/résistance opposé, FVG.
- Si aucune configuration claire n'existe → **HOLD**.

---

## 3. Format de réponse (Markdown)

```markdown
## Analyse Price Action

Contexte :
Structure :
Zone clé :
Liquidité :
Confirmation :

## Décision

Action : BUY / SELL / HOLD

Entrée :
SL :
TP :
RR :

## Raisonnement

Expliquer en quelques lignes pourquoi le trade est valide ou pourquoi il faut attendre.
```

---

## 4. Intégration dans le notebook

```python
prompt = f"""{...règles et priorités ci-dessus...}
==========================
Données (YAML)
==========================
{yaml_text}"""
```

Appel Ollama :

```python
requests.post(OLLAMA_URL, json={
    "model": MODEL,               # gemma4 (lib/ai.py)
    "prompt": prompt,
    "stream": False,
    "options": {"temperature": 0.2, "num_predict": 2500},
}, timeout=120)
```

La réponse (Markdown) est affichée brute dans l'onglet « Analyse IA » du logiciel (intra logiciel, aucun fichier n'est sauvegardé).

---

## 5. Champs YAML fournis au prompt

| Champ | Rôle |
|---|---|
| `price`, `session` | Où est le prix, quelle session |
| `timeframes` | Contexte des timeframes analysés |
| `structure` | Structure de marché par TF (trend/range) |
| `trend` | Direction, force, score par TF |
| `atr` | Volatilité (cohérence des objectifs) |
| `ema` (optionnel) | Alignement + position du prix |
| `support` / `resistance` | Niveaux les plus proches (pips) |
| `smart_money.order_blocks` | Zones d'ordre |
| `smart_money.liquidity` | Liquidité au-dessus/en dessous, sweeps |
| `smart_money.fvg` | Fair Value Gaps |
| `candlestick` | Patterns récents avec index de bougie |

**Retirés volontairement** : RSI, MACD, ADX, DI+, DI-, Momentum, Volume, probabilités, zones/risque pré-calculés. Deux philosophies se mélangent mal : indicateurs = confirmation statistique, Price Action/SMC = lecture du comportement du prix.

---

## 6. Comparaison avec l'ancien prompt (avancé)

| Aspect | Ancien (analyste SMC enrichi) | Nouveau (trader Price Action) |
|---|---|---|
| Rôle | Analyste multi-critères | Trader Price Action pur |
| Étapes d'analyse | 8 étapes (dont Momentum, EMA…) | Priorités A→E |
| Indicateurs | RSI, MACD, ADX, DI+, Momentum | **Aucun** |
| Décision | Règles explicites (RR ≥ 1.5…) | Contexte + confirmation, sinon HOLD |
| Entrée | Calculée par l'IA (1 TP + RR) | Entrée / SL / TP / RR si configuration claire |
| Format | `# Résumé` / `# Analyse` / `# Signal` | `## Analyse Price Action` / `## Décision` / `## Raisonnement` |
| Longueur | ~200 lignes | ~90 lignes |

> `01_scan_rapide.ipynb`, `02_signal_paire.ipynb` et `03_exemple_multi_tf.ipynb` continuent d'utiliser l'ancien prompt JSON via `lib/ai.py`.
