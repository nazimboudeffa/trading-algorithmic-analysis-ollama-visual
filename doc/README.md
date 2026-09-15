# Documentation

Documentation technique du projet d'analyse forex multi-timeframe. Lire dans l'ordre ci-dessous, du général au détail.

## Ordre de lecture

| # | Fichier | Contenu |
|---|---|---|
| 1 | [`signal_generation.md`](signal_generation.md) | **Pipeline complet** — des données aux signaux IA (fetch, cache, analyse, prompt, parsing JSON) |
| 2 | [`signal_parameters.md`](signal_parameters.md) | **Paramètres du signal** — chaque champ du dictionnaire envoyé à l'IA (JSON) |
| 3 | [`indicateurs_techniques.md`](indicateurs_techniques.md) | **Math des indicateurs** — RSI, MACD, MA20 (formules et intégration) |
| 4 | [`support_resistance.md`](support_resistance.md) | **Algorithme S/R** — swing points, clustering, scoring |
| 5 | [`candlestick_patterns.md`](candlestick_patterns.md) | **Patterns de chandeliers** — Doji, Hammer, Engulfing, etc. |
| 6 | [`analyse_avancee.md`](analyse_avancee.md) | **Analyse Price Action** (`04_signal_price_action.ipynb`) — 4 timeframes, Smart Money, YAML Price Action pur, sauvegarde des rapports |
| 7 | [`prompt_ia.md`](prompt_ia.md) | **Prompt Price Action** — structure, zones, réaction du prix, décision BUY/SELL/HOLD, réponse Markdown |
| 8 | [`price_action_method.md`](price_action_method.md) | **Méthode Price Action** — synthèse de la méthode, concepts SMC, règles de décision |

## Dépendances

```
signal_generation.md
      │
      ├──► signal_parameters.md   (structure du signal)
      ├──► indicateurs_techniques.md
      ├──► support_resistance.md
      └──► candlestick_patterns.md
                  │
                  ▼
      analyse_avancee.md   (Price Action : YAML pur + Smart Money)
                  │
                  ▼
      prompt_ia.md         (analyse IA en Markdown)
```

## Organisation du dossier

```
doc/
├── README.md                  ← ce fichier (index)
├── signal_generation.md       #1 Pipeline général
├── signal_parameters.md       #2 Paramètres du signal
├── indicateurs_techniques.md  #3 Indicateurs (math)
├── support_resistance.md      #4 Supports / Résistances
├── candlestick_patterns.md    #5 Patterns de chandeliers
├── analyse_avancee.md         #6 Analyse avancée (04)
└── prompt_ia.md               #7 Prompt analyste
```
