import pandas as pd


def detect_candlestick_patterns(df):
    patterns = []

    for i in range(1, len(df)):
        open_price = df['Open'].iloc[i]
        close_price = df['Close'].iloc[i]
        high = df['High'].iloc[i]
        low = df['Low'].iloc[i]
        prev_close = df['Close'].iloc[i-1]

        body = abs(close_price - open_price)
        range_size = high - low

        if range_size == 0:
            continue

        if body / range_size < 0.1:
            patterns.append({
                'index': i,
                'pattern': 'Doji',
                'signal': 'Indecision',
                'strength': 'Medium'
            })

        upper_wick = high - max(open_price, close_price)
        lower_wick = min(open_price, close_price) - low

        if lower_wick > 2 * body and upper_wick < body:
            patterns.append({
                'index': i,
                'pattern': 'Hammer',
                'signal': 'Bullish Reversal',
                'strength': 'Strong'
            })

        if upper_wick > 2 * body and lower_wick < body:
            patterns.append({
                'index': i,
                'pattern': 'Shooting Star',
                'signal': 'Bearish Reversal',
                'strength': 'Strong'
            })

        if i >= 1:
            prev_open = df['Open'].iloc[i-1]
            prev_close = df['Close'].iloc[i-1]

            if (prev_close < prev_open and
                close_price > open_price and
                open_price < prev_close and
                close_price > prev_open):
                patterns.append({
                    'index': i,
                    'pattern': 'Bullish Engulfing',
                    'signal': 'Bullish Reversal',
                    'strength': 'Very Strong'
                })

            if (prev_close > prev_open and
                close_price < open_price and
                open_price > prev_close and
                close_price < prev_open):
                patterns.append({
                    'index': i,
                    'pattern': 'Bearish Engulfing',
                    'signal': 'Bearish Reversal',
                    'strength': 'Very Strong'
                })

    return patterns


def find_support_resistance(df, window=None, threshold=None):
    if window is None:
        window = max(3, min(15, len(df) // 40))

    if threshold is None:
        atr = (df['High'] - df['Low']).rolling(14, min_periods=1).mean().iloc[-1]
        threshold = atr * 0.4
    min_threshold = (df['High'].max() - df['Low'].min()) * 0.0008
    threshold = max(threshold, min_threshold)

    pivot_highs = []
    pivot_lows = []

    for i in range(window, len(df) - window):
        high_slice = df['High'].iloc[i-window:i+window+1]
        low_slice = df['Low'].iloc[i-window:i+window+1]
        if df['High'].iloc[i] == high_slice.max() and high_slice.max() != high_slice.min():
            pivot_highs.append(df['High'].iloc[i])
        if df['Low'].iloc[i] == low_slice.min() and low_slice.min() != low_slice.max():
            pivot_lows.append(df['Low'].iloc[i])

    def cluster_pivots(pivots, level_type):
        if not pivots:
            return []
        pivots.sort()
        clusters = [[pivots[0]]]
        for p in pivots[1:]:
            if abs(p - clusters[-1][-1]) / max(clusters[-1][-1], 1e-10) < threshold:
                clusters[-1].append(p)
            else:
                clusters.append([p])

        results = []
        for c in clusters:
            level = round(sum(c) / len(c), 5)
            results.append({
                'level': level,
                'type': level_type,
                'touches': len(c),
                'strength': 'Strong' if len(c) >= 3 else 'Medium' if len(c) >= 2 else 'Weak'
            })
        return results

    levels = cluster_pivots(pivot_highs, 'Resistance') + cluster_pivots(pivot_lows, 'Support')
    levels.sort(key=lambda x: x['touches'], reverse=True)
    return levels[:5]


def analyze_market_structure(df):
    recent = df.tail(20)

    highs = recent['High'].values
    lows = recent['Low'].values

    higher_highs = sum(1 for i in range(1, len(highs)) if highs[i] > highs[i-1])
    lower_lows = sum(1 for i in range(1, len(lows)) if lows[i] < lows[i-1])

    if higher_highs > lower_lows * 1.5:
        structure = "Uptrend (Higher Highs)"
        bias = "Bullish"
    elif lower_lows > higher_highs * 1.5:
        structure = "Downtrend (Lower Lows)"
        bias = "Bearish"
    else:
        structure = "Consolidation (Ranging)"
        bias = "Neutral"

    price_range = (recent['High'].max() - recent['Low'].min()) / recent['Close'].iloc[-1]

    return {
        'structure': structure,
        'bias': bias,
        'higher_highs': higher_highs,
        'lower_lows': lower_lows,
        'price_range_pct': price_range * 100
    }


def build_price_action_signal(df, patterns, levels, structure):
    from .data import get_session

    last = df.iloc[-1]
    current_price = float(last['Close'])

    recent_patterns = [p for p in patterns if p['index'] >= len(df) - 5]

    nearest_support = None
    nearest_resistance = None

    for level in levels:
        if level['type'] == 'Support' and level['level'] < current_price:
            if nearest_support is None or level['level'] > nearest_support['level']:
                nearest_support = level
        elif level['type'] == 'Resistance' and level['level'] > current_price:
            if nearest_resistance is None or level['level'] < nearest_resistance['level']:
                nearest_resistance = level

    dist_to_support = ((current_price - nearest_support['level']) / current_price * 100) if nearest_support else None
    dist_to_resistance = ((nearest_resistance['level'] - current_price) / current_price * 100) if nearest_resistance else None

    return {
        'pair': 'EUR/USD',
        'price': current_price,
        'session': get_session(),
        'market_structure': structure['structure'],
        'bias': structure['bias'],
        'price_range_pct': round(structure['price_range_pct'], 2),
        'recent_patterns': [f"{p['pattern']} ({p['signal']})" for p in recent_patterns],
        'nearest_support': round(nearest_support['level'], 5) if nearest_support else None,
        'support_strength': nearest_support['strength'] if nearest_support else None,
        'dist_to_support_pct': round(dist_to_support, 2) if dist_to_support else None,
        'nearest_resistance': round(nearest_resistance['level'], 5) if nearest_resistance else None,
        'resistance_strength': nearest_resistance['strength'] if nearest_resistance else None,
        'dist_to_resistance_pct': round(dist_to_resistance, 2) if dist_to_resistance else None
    }
