"""
Analyse Price Action multi-timeframe.
Refactorisation du notebook 04_signal_price_action.ipynb en fonctions reutilisables.

Produit un dictionnaire de resultat consomme par l'interface graphique
(app.py) et genera le signal YAML envoye a l'IA (Ollama).
"""
import json
import re

import numpy as np
import pandas as pd
import ta
import yaml
import requests

from .analysis import analyze_market_structure, find_support_resistance
from .data import get_cached_data, get_session
from .ai import MODEL, OLLAMA_URL


DEFAULT_TFS = {
    "M15":    {"interval": "15m", "period": "5d"},
    "H1":     {"interval": "1h",  "period": "1mo"},
    "Daily":  {"interval": "1d",  "period": "1y"},
    "Weekly": {"interval": "1W",  "period": "2y"},
}


def pip_size(symbol):
    return 0.01 if "JPY" in symbol.upper() else 0.0001


def pips(price_diff, symbol):
    if price_diff is None or (isinstance(price_diff, float) and np.isnan(price_diff)):
        return None
    return round(float(price_diff) / pip_size(symbol), 1)


def compute_indicators(df):
    df = df.copy()
    df["atr"] = ta.volatility.AverageTrueRange(
        df["High"], df["Low"], df["Close"], window=14
    ).average_true_range()

    adx = ta.trend.ADXIndicator(df["High"], df["Low"], df["Close"], window=14)
    df["adx"] = adx.adx()
    df["di_pos"] = adx.adx_pos()
    df["di_neg"] = adx.adx_neg()

    df["rsi"] = ta.momentum.RSIIndicator(close=df["Close"], window=14).rsi()
    macd = ta.trend.MACD(close=df["Close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["momentum"] = ta.momentum.ROCIndicator(close=df["Close"], window=12).roc()

    for w in (20, 50, 100, 200):
        df[f"ema{w}"] = ta.trend.EMAIndicator(close=df["Close"], window=w).ema_indicator()

    return df


def analyze_trend(df):
    last = df.iloc[-1]
    close = float(last["Close"])
    rsi = float(last["rsi"])
    macd_bull = last["macd"] > last["macd_signal"]
    adx = float(last["adx"])
    di_pos, di_neg = float(last["di_pos"]), float(last["di_neg"])
    ema20 = float(last["ema20"])

    score = 0.0
    if macd_bull:
        score += 1.0
    else:
        score -= 1.0
    if rsi > 55:
        score += 1.0
    elif rsi < 45:
        score -= 1.0
    if close > ema20:
        score += 1.0
    else:
        score -= 1.0
    if di_pos > di_neg:
        score += 0.5
    else:
        score -= 0.5

    direction = "Bullish" if score >= 1.5 else "Bearish" if score <= -1.5 else "Neutral"
    strength = None
    if direction != "Neutral":
        strength = "Strong" if adx >= 30 else "Moderate" if adx >= 20 else "Weak"
    return {"direction": direction, "strength": strength, "score": round(score, 1)}


def ema_analysis(df):
    last = df.iloc[-1]
    close = float(last["Close"])
    emas = {f"EMA{w}": float(last[f"ema{w}"]) for w in (20, 50, 100, 200)}
    e = [emas[f"EMA{w}"] for w in (20, 50, 100, 200)]
    result = {}
    if all(np.isfinite(v) for v in e):
        e20, e50, e100, e200 = e
        alignment = "Bullish" if e20 > e50 > e100 > e200 else "Bearish" if e20 < e50 < e100 < e200 else "Mixed"
        below = sum(1 for v in e if close > v)
        pos = ("Above EMA20" if below >= 4
               else "Between EMA20 and EMA50" if below == 3
               else "Between EMA50 and EMA100" if below == 2
               else "Between EMA100 and EMA200" if below == 1
               else "Below EMA200")
        result["alignment"] = alignment
        result["price_position"] = pos
        result.update({k: round(v, 5) for k, v in emas.items()})
    else:
        result["alignment"] = "N/A (insufficient data)"
        result["price_position"] = "N/A"
    return result


def detect_patterns_avances(df, lookback=10):
    n = len(df)
    found = []
    for i in range(max(2, n - lookback), n):
        o, c = df["Open"].iloc[i], df["Close"].iloc[i]
        h, l = df["High"].iloc[i], df["Low"].iloc[i]
        po, pc = df["Open"].iloc[i - 1], df["Close"].iloc[i - 1]
        ph, pl = df["High"].iloc[i - 1], df["Low"].iloc[i - 1]
        body = abs(c - o)
        rng = h - l
        if rng == 0:
            continue
        upper = h - max(o, c)
        lower = min(o, c) - l
        idx = i - n

        def add(name, sig):
            entry = {"candle": idx, "pattern": name, "signal": sig}
            if entry not in found:
                found.append(entry)

        if body / rng < 0.1:
            add("Doji", "Indecision")
        if lower > 2 * body and upper < body:
            add("Hammer", "Bullish Reversal")
        if upper > 2 * body and lower < body:
            add("Shooting Star", "Bearish Reversal")
        if upper > 2 * body and lower > 2 * body:
            add("Pin Bar", "Reversal")
        if pc < po and c > o and o < pc and c > po:
            add("Bullish Engulfing", "Bullish Reversal")
        if pc > po and c < o and o > pc and c < po:
            add("Bearish Engulfing", "Bearish Reversal")
        if h <= ph and l >= pl:
            add("Inside Bar", "Compression")
        if h >= ph and l <= pl:
            add("Outside Bar", "Expansion")
        if i >= 2:
            po2, pc2 = df["Open"].iloc[i - 2], df["Close"].iloc[i - 2]
            bo, bc = df["Open"].iloc[i - 1], df["Close"].iloc[i - 1]
            rng1 = df["High"].iloc[i - 1] - df["Low"].iloc[i - 1]
            if rng1 > 0 and pc2 < po2 and abs(bc - bo) / rng1 < 0.3 and c > o and c > (po2 + pc2) / 2:
                add("Morning Star", "Bullish Reversal")
    return found


def find_order_blocks(df, lookback=40):
    bullish, bearish = [], []
    n = len(df)
    for i in range(max(2, n - lookback), n - 1):
        atr = df["atr"].iloc[i]
        if atr == 0 or np.isnan(atr):
            continue
        move = df["Close"].iloc[i + 1] - df["Close"].iloc[i]
        if move > 1.5 * atr and df["Close"].iloc[i] < df["Open"].iloc[i]:
            bullish.append(float(df["High"].iloc[i]))
        elif move < -1.5 * atr and df["Close"].iloc[i] > df["Open"].iloc[i]:
            bearish.append(float(df["Low"].iloc[i]))
    return bullish, bearish


def round_list(vals, n=5):
    return sorted(set(round(x, n) for x in vals))


def find_fvg(df, lookback=40):
    bullish, bearish = None, None
    n = len(df)
    for i in range(max(2, n - lookback), n - 1):
        h1, l1 = df["High"].iloc[i - 1], df["Low"].iloc[i - 1]
        h2, l2 = df["High"].iloc[i + 1], df["Low"].iloc[i + 1]
        if l2 > h1:
            bullish = (float(h1), float(l2))
        if h2 < l1:
            bearish = (float(h2), float(l1))
    return bullish, bearish


def liquidity_analysis(df, lookback=20):
    n = len(df)
    highs = df["High"].iloc[-lookback:].values
    lows = df["Low"].iloc[-lookback:].values
    last_high, last_low = df["High"].iloc[-1], df["Low"].iloc[-1]
    atr = df["atr"].iloc[-1]
    if atr == 0 or np.isnan(atr):
        atr = 1e-9
    tol = atr * 0.5

    def max_repeat(vals):
        best = 0
        for v in vals:
            best = max(best, sum(1 for w in vals if abs(w - v) <= tol))
        return best

    eq_highs = max_repeat(highs[:-1])
    eq_lows = max_repeat(lows[:-1])
    sweep_above = bool(last_high > np.max(highs[:-1])) if len(highs) > 1 else False
    sweep_below = bool(last_low < np.min(lows[:-1])) if len(lows) > 1 else False
    return {
        "equal_highs": eq_highs,
        "equal_lows": eq_lows,
        "liquidity_above": eq_highs >= 2,
        "liquidity_below": eq_lows >= 2,
        "sweep_above": sweep_above,
        "sweep_below": sweep_below,
    }


def nearest_levels(levels_list, price):
    supp = [l for l in levels_list if l["type"] == "Support" and l["level"] < price]
    res = [l for l in levels_list if l["type"] == "Resistance" and l["level"] > price]
    near_s = max(supp, key=lambda l: l["level"]) if supp else None
    near_r = min(res, key=lambda l: l["level"]) if res else None
    return near_s, near_r


def analyze_pair(
    symbol,
    full_name=None,
    tfs=None,
    data=None,
    verbose=True,
    compute_signal=True,
    ask_llm=False,
):
    """Analyse de marche multi-timeframe.

    Retourne un dict contenant toutes les donnees (donnees, indicateurs,
    niveaux, zones...) utilisees par le GUI et le graphique.

    compute_signal=False : analyse seulement le graphique (pas de signal,
    pas de YAML) — le signal peut etre calcule ensuite via compute_signal().
    Si ask_llm=True, appelle Ollama et renvoie le rapport (affiche intra logiciel).
    """
    from .config import FULL_NAMES

    symbol = symbol.upper()
    tfs = tfs or DEFAULT_TFS
    full_name = full_name or FULL_NAMES.get(symbol, symbol.replace("USD", "/USD"))

    if data is None:
        data = {}
        for tf_name, tf in tfs.items():
            data[tf_name] = get_cached_data(symbol + "=X", tf["interval"], tf["period"], verbose=verbose)

    indicators = {tf: compute_indicators(df) for tf, df in data.items()}
    structure = {tf: analyze_market_structure(data[tf])["structure"] for tf in tfs}
    levels = {tf: find_support_resistance(data[tf]) for tf in tfs}
    trend = {tf: analyze_trend(indicators[tf]) for tf in tfs}
    ema_data = {
        "Daily": ema_analysis(indicators["Daily"]),
        "H1": ema_analysis(indicators["H1"]),
    }

    vol_series = data["M15"]["Volume"].dropna().astype(float)
    vol_available = bool((vol_series > 0).any())
    if vol_available and len(vol_series) >= 10:
        vol_val = int(data["M15"]["Volume"].iloc[-1])
        vol_trend = "Increasing" if vol_series.iloc[-5:].mean() > vol_series.iloc[-10:-5].mean() else "Decreasing"
    else:
        vol_val, vol_trend = None, "Unknown"
    volume_info = {"available": vol_available, "tick_volume": vol_val, "trend": vol_trend}

    atr_d = indicators["Daily"]["atr"]
    atr_last = atr_d.iloc[-1]
    atr_mean = atr_d.rolling(14).mean().iloc[-1]
    volatility = "Medium"
    if atr_last > atr_mean * 1.2:
        volatility = "High"
    elif atr_last < atr_mean * 0.8:
        volatility = "Low"

    patterns = detect_patterns_avances(data["M15"])

    bullish_ob_raw, bearish_ob_raw = find_order_blocks(indicators["H1"])
    bullish_ob = round_list(bullish_ob_raw)
    bearish_ob = round_list(bearish_ob_raw)
    ob_overlap = sorted(set(bullish_ob) & set(bearish_ob))
    bullish_ob = [x for x in bullish_ob if x not in ob_overlap]
    bearish_ob = [x for x in bearish_ob if x not in ob_overlap]

    fvg_bullish, fvg_bearish = find_fvg(indicators["H1"])
    liquidity = liquidity_analysis(indicators["M15"])

    zones = {}
    for tf in tfs:
        b_ob_raw, s_ob_raw = find_order_blocks(indicators[tf])
        b_ob = round_list(b_ob_raw)[-4:]
        s_ob = round_list(s_ob_raw)[-4:]
        f_bull, f_bear = find_fvg(indicators[tf])
        zones[tf] = {
            "bullish_ob": b_ob,
            "bearish_ob": s_ob,
            "fvg_bullish": f_bull,
            "fvg_bearish": f_bear,
        }

    price = float(data["M15"]["Close"].iloc[-1])
    near_s, near_r = nearest_levels(levels["M15"], price)

    result = {
        "symbol": symbol,
        "full_name": full_name,
        "tfs": tfs,
        "data": data,
        "indicators": indicators,
        "structure": structure,
        "levels": levels,
        "trend": trend,
        "ema_data": ema_data,
        "volume_info": volume_info,
        "volatility": volatility,
        "patterns": patterns,
        "bullish_ob": bullish_ob,
        "bearish_ob": bearish_ob,
        "ob_overlap": ob_overlap,
        "fvg_bullish": fvg_bullish,
        "fvg_bearish": fvg_bearish,
        "zones": zones,
        "liquidity": liquidity,
        "price": price,
        "near_s": near_s,
        "near_r": near_r,
        "entry": None,
        "stop_loss": None,
        "take_profit": None,
    }

    if compute_signal:
        result.update(compute_signal(result))
    if ask_llm and compute_signal:
        result["ai_report_text"] = ask_ai(result["yaml_text"])

    return result


def compute_signal(r):
    """Calcule le signal (facteurs, score, entree/SL/TP, zones, signal YAML)
    a partir d'une analyse de marche produite par analyze_pair(..., compute_signal=False).

    Retourne un dict a fusionner dans le resultat : score, entry, stop_loss,
    take_profit, buy_zone, sell_zone, signal_yaml, yaml_text.
    """
    symbol = r["symbol"]
    full_name = r["full_name"]
    tfs = r["tfs"]
    indicators = r["indicators"]
    structure = r["structure"]
    trend = r["trend"]
    ema_data = r["ema_data"]
    patterns = r["patterns"]
    bullish_ob = r["bullish_ob"]
    bearish_ob = r["bearish_ob"]
    ob_overlap = r["ob_overlap"]
    fvg_bullish = r["fvg_bullish"]
    fvg_bearish = r["fvg_bearish"]
    liquidity = r["liquidity"]
    price = r["price"]
    near_s = r["near_s"]
    near_r = r["near_r"]

    factors = []
    if ema_data["Daily"]["alignment"] == "Bearish":
        factors.append(("Daily EMA alignment Bearish", "bear"))
    elif ema_data["Daily"]["alignment"] == "Bullish":
        factors.append(("Daily EMA alignment Bullish", "bull"))
    pos = ema_data["Daily"]["price_position"]
    if pos in ("Above EMA20", "Between EMA20 and EMA50"):
        factors.append((f"Price {pos}", "bull"))
    elif pos in ("Between EMA100 and EMA200", "Below EMA200"):
        factors.append((f"Price {pos}", "bear"))
    if indicators["Daily"]["macd"].iloc[-1] > indicators["Daily"]["macd_signal"].iloc[-1]:
        factors.append(("MACD bullish (Daily)", "bull"))
    else:
        factors.append(("MACD bearish (Daily)", "bear"))
    if indicators["Daily"]["rsi"].iloc[-1] > 50:
        factors.append(("RSI > 50 (Daily)", "bull"))
    else:
        factors.append(("RSI < 50 (Daily)", "bear"))
    if trend["H1"]["direction"] == "Bullish":
        factors.append(("H1 trend Bullish", "bull"))
    elif trend["H1"]["direction"] == "Bearish":
        factors.append(("H1 trend Bearish", "bear"))
    if trend["M15"]["direction"] == "Bullish":
        factors.append(("M15 trend Bullish", "bull"))
    elif trend["M15"]["direction"] == "Bearish":
        factors.append(("M15 trend Bearish", "bear"))

    bull_score = sum(1 for _, s in factors if s == "bull")
    bear_score = sum(1 for _, s in factors if s == "bear")
    total = bull_score + bear_score
    if total:
        bull_pct = round(100 * bull_score / total)
        bear_pct = 100 - bull_pct
        confidence = round(100 * max(bull_score, bear_score) / total)
    else:
        bull_pct = bear_pct = 50
        confidence = 50

    ts = trend["Daily"]["strength"] or trend["H1"]["strength"]
    if ts == "Strong":
        confidence = min(95, confidence + 10)
    elif ts == "Moderate":
        confidence = min(95, confidence + 5)

    if abs(bull_score - bear_score) <= 1:
        direction = "HOLD"
    else:
        direction = "BUY" if bull_score > bear_score else "SELL"

    strength = None if direction == "HOLD" else "Weak" if confidence < 65 else "Moderate" if confidence < 80 else "Strong"
    dominant = "bull" if bull_score >= bear_score else "bear"
    confluences = [f for f, s in factors if s == dominant]
    confluence_str = f"{max(bull_score, bear_score)}/{total}" if total else "0/0"
    reasons = list(confluences[:6])
    if direction == "HOLD":
        reasons.append(f"Score too close ({bull_score} vs {bear_score})")

    atr_ref = float(indicators["M15"]["atr"].iloc[-1])
    sl_dist = 1.5 * atr_ref
    tp_dist = 2.5 * atr_ref
    rr = round(tp_dist / sl_dist, 2) if sl_dist else None
    if direction == "BUY":
        entry_p, sl_p, tp_p = price, price - sl_dist, price + tp_dist
    elif direction == "SELL":
        entry_p, sl_p, tp_p = price, price + sl_dist, price - tp_dist
    else:
        entry_p = sl_p = tp_p = None

    buy_zone = [x for x in bullish_ob if x < price]
    sell_zone = [x for x in bearish_ob if x > price]
    if near_s:
        buy_zone.append(float(near_s["level"]))
    if near_r:
        sell_zone.append(float(near_r["level"]))
    buy_zone = sorted(set(round(x, 5) for x in buy_zone), reverse=True)[:2]
    sell_zone = sorted(set(round(x, 5) for x in sell_zone))[:2]

    spread = 0.8
    signal_yaml = {
        "pair": f"{symbol} ({full_name})",
        "price": {"current": round(price, 5), "spread": spread},
        "session": {"name": get_session()},
        "timeframes": {
            "analyzed": list(tfs.keys()),
            "interval": {tf: tfs[tf]["interval"] for tf in tfs},
            "period": {tf: tfs[tf]["period"] for tf in tfs},
        },
        "structure": {tf: structure[tf] for tf in tfs},
        "trend": {tf: trend[tf] for tf in tfs},
        "atr": {tf: round(float(indicators[tf]["atr"].iloc[-1]), 6) for tf in tfs},
        "ema": ema_data,
        "support": {
            "nearest": {
                "exists": near_s is not None,
                "price": round(float(near_s["level"]), 5) if near_s else None,
                "strength": near_s["strength"] if near_s else None,
                "distance_pips": pips(price - near_s["level"], symbol) if near_s else None,
                "reason": None if near_s else "No support identified below current price",
            }
        },
        "resistance": {
            "nearest": {
                "exists": near_r is not None,
                "price": round(float(near_r["level"]), 5) if near_r else None,
                "strength": near_r["strength"] if near_r else None,
                "distance_pips": pips(near_r["level"] - price, symbol) if near_r else None,
                "reason": None if near_r else "No resistance identified above current price",
            }
        },
        "smart_money": {
            "order_blocks": {
                "bullish": bullish_ob[-3:],
                "bearish": bearish_ob[-3:],
                "role_change_levels": ob_overlap,
                "note": "Levels in role_change_levels act as both support and resistance",
            },
            "liquidity": liquidity,
            "fvg": {
                "bullish": {
                    "exists": fvg_bullish is not None,
                    "zone": {"low": round(fvg_bullish[0], 5), "high": round(fvg_bullish[1], 5)} if fvg_bullish else None,
                },
                "bearish": {
                    "exists": fvg_bearish is not None,
                    "zone": {"low": round(fvg_bearish[0], 5), "high": round(fvg_bearish[1], 5)} if fvg_bearish else None,
                },
            },
        },
        "candlestick": {"patterns": {"recent": patterns, "timeframe": "M15"}},
    }

    return {
        "score": {
            "direction": direction,
            "strength": strength,
            "confidence": confidence,
            "bull_pct": bull_pct,
            "bear_pct": bear_pct,
            "bull_score": bull_score,
            "bear_score": bear_score,
            "confluence": confluence_str,
            "factors": factors,
            "reasons": reasons,
        },
        "entry": entry_p,
        "stop_loss": sl_p,
        "take_profit": tp_p,
        "buy_zone": buy_zone,
        "sell_zone": sell_zone,
        "signal_yaml": signal_yaml,
        "yaml_text": yaml.dump(signal_yaml, sort_keys=False, allow_unicode=True, default_flow_style=False),
    }


def _expand_scientific(text):
    """Réécrit les nombres en notation scientifique (ex. 1e+00) en notation décimale."""
    if not text:
        return text

    def repl(m):
        try:
            value = float(m.group(0))
        except ValueError:
            return m.group(0)
        s = f"{value:f}"
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return s or "0"

    return re.sub(
        r"(?<![0-9A-Za-z_.])([0-9]+(?:\.[0-9]+)?)[eE]([+-]?[0-9]+)(?![0-9A-Za-z_.])",
        repl,
        text,
    )


def ask_ai(yaml_text):
    """Envoie le signal YAML a Ollama (prompt du notebook 04)."""
    prompt = f"""Tu es un trader professionnel spécialisé en Price Action Forex.

Tu vas recevoir un signal enrichi YAML contenant les données d'une paire Forex.

Analyse uniquement les informations fournies.

Objectif :
Déterminer s'il existe une opportunité de trading basée uniquement sur :
- structure du marché
- supports et résistances
- zones de liquidité
- order blocks
- fair value gaps
- figures de chandeliers
- réaction du prix

Règles :

1. Toujours commencer par déterminer le contexte :
- tendance
- range
- cassure
- retournement potentiel

2. Priorité d'analyse :

A) Structure du prix
- Higher High / Higher Low = tendance haussière
- Lower High / Lower Low = tendance baissière
- absence de structure claire = range

B) Zones importantes
Analyser :
- support
- résistance
- order block
- FVG
- liquidité au-dessus et en dessous du prix

C) Réaction du prix
Chercher :
- rejet d'une zone
- pin bar
- engulfing
- cassure + retest
- sweep de liquidité

D) Entrée
Ne jamais entrer au milieu d'un range.

Privilégier :
- achat sur support après confirmation
- vente sur résistance après confirmation
- cassure uniquement après clôture et retest

E) Gestion du risque

Si un trade est valide :
définir :

Entrée
Stop Loss
Take Profit
Ratio Risk/Reward

Le SL doit être placé derrière :
- dernier swing
- zone invalidation
- order block

Le TP doit viser :
- prochaine liquidité
- support/résistance opposé
- FVG

Si aucune configuration claire n'existe :

Répondre HOLD.

Tous les prix et nombres (Entrée, SL, TP, RR, niveaux) doivent être écrits
en notation décimale standard (exemple : 1.15433, 0.00032), jamais en
notation scientifique (exemple : 1e+00).

Format de réponse :

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

==========================
Données (YAML)
==========================
{yaml_text}"""

    try:
        r = requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "prompt": prompt, "stream": False,
                  "options": {"temperature": 0.2, "num_predict": 2500}},
            timeout=120,
        )
        r.raise_for_status()
        text = r.json().get("response", "").strip()
        return _expand_scientific(text) if text else None
    except requests.exceptions.ConnectionError:
        return f"[Ollama injoignable sur {OLLAMA_URL}. Lance 'ollama serve'.]"
    except Exception as e:
        return f"[Analyse IA indisponible : {e}]"