# Plan de développement — Analyse Forex Multi-Timeframe avec IA Locale

> Document de pilotage : objectifs, architecture cible, feuille de route et backlog.
> État : brouillon v1 — à faire évoluer au fil des itérations.

---

## 1. Contexte & objectifs

Application desktop **PySide6/Qt** qui analyse des paires forex majeures sur
plusieurs timeframes (daily/1h/5m), affiche un graphique de chandeliers
interactif et génère un signal combiné envoyé à un modèle IA **local (Ollama)**
pour un rapport en langage naturel.

Le projet est **strictement éducatif et expérimental** (voir l'avertissement du
README). Aucun objectif de rentabilité : l'objectif est la robustesse du code,
la reproductibilité de l'analyse et la qualité des rendus.

### Objectifs prioritaires
1. Fiabiliser les données et l'analyse (déterministe, sans source de bug).
2. Rendre l'app fluide et utilisable (threads, cache, erreurs claires).
3. Uniformiser les onglets et l'affichage (cohérence visuelle et numeric).
4. Garantir un fonctionnement hors-ligne (Ollama n'est pas indispensable à l'analyse).

---

## 2. Architecture actuelle

```
src/
  app.py           # Fenêtre principale Qt (onglets Signal / Analyse IA), workers QThread
  chart_widget.py  # Graphique bougies interactif (QPainter, zoom, crosshair)
  lib/
    config.py      # Paires, timeframes, noms complets
    data.py        # Fetch OpenBB/yfinance + cache pickle (TTL 60 min)
    analysis.py    # S/R adaptatif, structure de marché, patterns bougies
    price_action.py# Pipeline complet Price Action + build signal YAML + ask_ai()
    ai.py          # Client Ollama (génération du prompt, lecture réponse)
```

Écarts déjà corrigés / à surveiller :
- **Notation scientifique** : les prix étaient affichés en `1e+00` (spec de
  format mal formé `"0.00000"` → corrigé en `f".{dec}f"`) ; côté IA, le prompt
  interdit la notation scientifique et `_expand_scientific()` normalise la
  réponse (`src/lib/price_action.py`).
- **Cohérence visuelle** : l'onglet Analyse IA est désormais encadré comme
  l'onglet Signal (`QFrame` + bord arrondi, `src/app.py`).

---

## 3. Feuille de route (phases)

### Phase 1 — Mise à niveau données & analyse (cœur métier)
- [x] Correction notation scientifique dans l'affichage signal (`app.py`)
- [x] Correction notation scientifique dans le rapport IA (prompt + `_expand_scientific`)
- [x] Harmonisation visuelle des onglets Signal / Analyse IA
- [ ] Tests unitaires sur `price_action` et `_expand_scientific` (cas JPY, 1e+00, 2e+02)
- [ ] Gestion d'erreurs Ollama (timeout, modèle absent, serveur down) avec message clair

### Phase 2 — Robustesse & expérience utilisateur
- [ ] Séparation métier / UI plus nette (extraire la logique hors des workers Qt)
- [ ] Barre de progression / état pendant l'analyse et l'appel IA
- [ ] Export des rapports IA (Markdown/TXT) à la demande
- [ ] Historique des signaux (liste des dernières analyses)

### Phase 3 — Qualité & maintenance
- [ ] Suite de tests automatisés (pytest) sur `analysis.py` et `price_action.py`
- [ ] Typage (`py.typed`) + lint (ruff) en CI
- [ ] Documentation `doc/` : prompt IA, indicateurs, S/R (déjà en cours)
- [ ] CI GitHub Actions : lint + tests sur chaque push

---

## 4. Backlog (idées non priorisées)

- Backtest des signaux sur données historiques (metrics win-rate, R-multiple).
- Multi-modèles Ollama configurables (UI) avec fallback.
- Export PNG du graphique.
- Configuration des paires/timeframes via interface (au lieu du fichier `config.py`).
- Détection d'instructions de risque dans le prompt IA (l'interdiction de notation scientifique est déjà là).

---

## 5. Dette technique / points de vigilance

- `data.py` dépend de la disponibilité réseau (yfinance/OpenBB) : toujours envelopper
  les appels réseau, prévoir le mode hors-ligne (cache uniquement).
- Le cache pickle a un TTL de 60 min : vérifier la fraîcheur au chargement (pas seulement au fetch).
- Les workers (QThread) doivent être owned par la fenêtre et nettoyés proprement à la fermeture.
- Garder le français comme langue des messages utilisateur (cohérence du produit).

---

## 6. Règles de contribution

- Messages de commit en français, convention `fix:`, `feat:`, `refactor:`, `docs:`.
- Ne jamais committer de secrets ni de données d'API.
- Tout changement de comportement de l'analyse doit être couvert par un test.
- Code review avant merge sur `main`.

---

*Document généré pour accompagner l'évolution du projet. À maintenir à jour avec les itérations.*
