# Analyse Forex Multi-Timeframe avec IA Locale

Analyse technique multi-timeframe (daily/1h/5m) de paires forex majeures avec signaux IA via Ollama. Utilise OpenBB (provider yfinance) comme source de données.

## Application desktop

**Logiciel visuel desktop** (PySide6/Qt) issu de l'ancien notebook d'analyse Price Action :

```bash
setup.bat        # création du venv + installation (1ʳᵉ fois)
run.bat          # lancement de l'application
```

Ce que fait l'app :
- **Graphique de chandeliers interactif** : bougies OHLC, EMAs 20/50/100/200, supports/résistances par timeframe, order blocks, FVG, patterns candlestick, lignes Entrée/SL/TP.
- **Interaction** : zoom à la molette, décalage à la souris, crosshair + OHLC au survol, clic droit = reset.
- **Panneau Signal** : synthese multi-timeframe (tendance, score bull/bear, confluence), RSI/ADX, zones d'achat/vente, liquidité, patterns récents.
- **Analyse IA (Ollama)** : envoi du signal YAML au modèle `gemma4` et affichage du rapport dans l'onglet (intra logiciel, sans fichier).

## Paires supportées

EURUSD, USDJPY, GBPUSD — configurables dans `src/lib/config.py`. L'app ajoute aussi USDCHF, AUDUSD, USDCAD, NZDUSD.

## Installation

```bash
pip install -r requirements.txt
```

Installe et lance [Ollama](https://ollama.ai/), puis tire le modèle :

```bash
ollama pull gemma4
ollama serve
```

## Structure du projet

```
├── src/                          # Code du logiciel
│   ├── app.py                    # Fenêtre principale Qt (sélection paire/TF, panneaux)
│   ├── chart_widget.py           # Graphique bougies interactif (QPainter)
│   └── lib/
│       ├── config.py             # Paires, timeframes, noms
│       ├── data.py               # Fetch OpenBB + cache pickle
│       ├── analysis.py           # S/R, structure, patterns, signal
│       ├── price_action.py       # Pipeline complet Price Action (refactor notebook)
│       └── ai.py                 # Analyse IA via Ollama
├── doc/                          # Documentation technique (indicateurs, S/R, prompts)
├── data_cache/                   # Cache des données (60 min TTL)
├── requirements.txt
├── run.bat / setup.bat           # Lancement / installation
└── README.md
```

## Pipeline

1. **Données** — `src/lib/data.py` : fetch via `obb.currency.price.historical()`, cache pickle 60 min
2. **Analyse** — `src/lib/analysis.py` : S/R adaptatif (ATR + pivot clustering), structure de marché, patterns bougies
3. **Signal** — Signal combiné multi-timeframe construit dans `src/lib/price_action.py`, envoyé à Ollama
4. **IA** — `src/lib/ai.py` : `gemma4`, prompt Price Action Markdown (disponible dans `doc/prompt_ia.md`)

## Configuration

Éditer `src/lib/config.py` pour changer les paires ou les timeframes.

Le modèle Ollama se change dans `src/lib/ai.py` :
```python
MODEL = "gemma4"  # → gemma3:12b, llama3:8b, etc.
```

## AVERTISSEMENT IMPORTANT

> [!WARNING]
> **PROJET STRICTEMENT EDUCATIF ET EXPERIMENTAL**
>
> Ce projet est fourni exclusivement a des fins d'apprentissage, de demonstration technique et d'experimentation. Il ne constitue **en aucun cas** un conseil en investissement, une recommandation financiere, une incitation a acheter ou vendre un actif, ni une promesse de performance.
>
> Tout algorithme de trading, aussi convaincant, sophistique ou automatise soit-il, peut produire des signaux faux, tardifs, incoherents ou desastreux dans des conditions de marche reelles. Les marches financiers sont volatils, imprevisibles et peuvent reagir brutalement a des evenements que le modele ne comprend pas, n'anticipe pas ou interprete mal.
>
> **Vous pouvez perdre une partie importante de votre capital, voire la totalite de l'argent engage.** Cela inclut les pertes liees aux faux signaux, aux erreurs de parametrage, aux biais de donnees, aux problemes techniques, a la latence, aux conditions de liquidite, au spread, au slippage, a l'effet de levier et a toute defaillance logicielle ou humaine.
>
> N'utilisez jamais cet outil avec de l'argent que vous ne pouvez pas vous permettre de perdre integralement. Si vous choisissez de vous en servir dans un contexte reel, vous le faites **a vos seuls risques**, sous votre **entiere responsabilite**.
>
> En resume : **ce projet peut vous aider a explorer des idees, pas a securiser votre argent.** Si vous cherchez une garantie, il n'y en a aucune.
