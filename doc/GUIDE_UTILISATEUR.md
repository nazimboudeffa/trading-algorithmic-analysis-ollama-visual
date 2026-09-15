# Guide utilisateur — Analyse Forex Multi-Timeframe avec IA Locale

> Guide pratique pour installer, lancer et utiliser l'application.
> Varie du README : il se concentre sur l'usage quotidien et l'interface.

---

## 1. Prérequis

- **Python 3.x** (3.10 ou plus récent recommandé) avec `pip`.
- **Ollama** installé et démarré (pour l'onglet Analyse IA).
- Une connexion réseau pour télécharger les cotations (yfinance / OpenBB).

---

## 2. Installation

### 2.1 Dépendances Python

```bash
pip install -r requirements.txt
```

### 2.2 Ollama

Installe [Ollama](https://ollama.ai/) puis tire le modèle utilisé par l'app :

```bash
ollama pull gemma4
ollama serve
```

> Le serveur Ollama doit rester actif pendant l'utilisation de l'onglet IA.
> Le modèle précis utilisé se configure dans `src/lib/ai.py` (`MODEL`).

---

## 3. Lancement

```bash
python src/app.py
```

Ou, sous Windows, double-cliquez sur `run.bat`.

---

## 4. Vue d'ensemble de l'interface

La fenêtre principale propose :

- **Barre d'outils** : sélection de la paire et du timeframe, bouton **Analyser**.
- **Onglet Signal** : le graphique de chandeliers + le panneau de signal
  multi-timeframe.
- **Onglet Analyse IA** : le rapport en langage naturel produit par Ollama à
  partir du signal.

---

## 5. Onglet Signal — lecture de base

### 5.1 Le graphique

- **Bougies OHLC** avec moyennes mobiles (EMA 20/50/100/200).
- **Supports / Résistances** (S/R) détectés automatiquement par timeframe.
- **Order blocks, FVG, patterns candlestick**, lignes Entrée / SL / TP.
- **Interaction** : molette = zoom, glisser = déplacer, survol = crosshair +
  OHLC, clic droit = réinitialiser la vue.

### 5.2 Le panneau Signal

Résumé multi-timeframe (tendance, score bull/bear, confluence), RSI / ADX,
zones d'achat / vente, liquidité et patterns récents. Les prix s'affichent en
notation décimale standard (ex. `1.15407`, `0.00032`) — jamais en notation
scientifique (`1e+00`).

---

## 6. Onglet Analyse IA

1. Terminez d'abord une analyse dans l'onglet Signal (cliquez sur **Analyser**).
2. Basculez sur **Analyse IA** puis cliquez sur **Générer l'analyse IA**.
3. Le signal YAML est envoyé au modèle local (Ollama) ; le rapport s'affiche
   dans le panneau de l'onglet, sans créer de fichier.

> Si Ollama est injoignable ou que le modèle est absent, un message d'erreur
> clair s'affiche à la place du rapport.

---

## 7. Dépannage

| Problème                        | Solution                                                |
|---------------------------------|---------------------------------------------------------|
| `Ollama injoignable`            | Lancer `ollama serve` puis relancer l'analyse IA        |
| Modèle absent                   | `ollama pull gemma4`                                    |
| Données absentes / erreur       | Vérifier la connexion ; le cache expire après 60 min    |
| Valeurs type `1e+00` affichées  | Normalement corrigées ; signaler si réapparition        |

---

## 8. Avertissement

> [!WARNING]
> **Projet strictement éducatif et expérimental.** Ce logiciel ne fournit
> **aucun conseil en investissement** et ne garantit aucune performance.
> Les marchés sont volatils et imprévisibles : vous pouvez perdre une partie
> importante, voire la totalité, de votre capital. Utilisez cet outil **à vos
> seuls risques**, jamais avec de l'argent dont vous ne pouvez pas vous
> permettre la perte.
