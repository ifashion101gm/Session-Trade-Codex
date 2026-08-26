import numpy as np
import pandas as pd


def extract_smc_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extracts rolling body medians and causal 3-bar fractals.
    Open-stamped convention: A fractal formed across [t-2, t-1, t] is confirmed after bar t closes.
    """
    df = df.copy()
    df['body'] = (df['close'] - df['open']).abs()
    df['range'] = df['high'] - df['low']
    df['median_body_20'] = df['body'].shift(1).rolling(20).median()
    df['body_eff'] = df['body'] / df['range'].replace(0, np.nan)

    df['disp_bull'] = (
        (df['close'] > df['open']) &
        (df['body'] >= 1.5 * df['median_body_20']) &
        (df['body_eff'] >= 0.60)
    )

    df['disp_bear'] = (
        (df['close'] < df['open']) &
        (df['body'] >= 1.5 * df['median_body_20']) &
        (df['body_eff'] >= 0.60)
    )

    # Causal fractals: Swing at t-1 is confirmed when bar t closes
    df['is_swing_high'] = (df['high'].shift(1) > df['high'].shift(2)) & (df['high'].shift(1) > df['high'])
    df['confirmed_swing_high'] = np.where(df['is_swing_high'], df['high'].shift(1), np.nan)
    df['last_confirmed_swing_high'] = df['confirmed_swing_high'].ffill()

    df['is_swing_low'] = (df['low'].shift(1) < df['low'].shift(2)) & (df['low'].shift(1) < df['low'])
    df['confirmed_swing_low'] = np.where(df['is_swing_low'], df['low'].shift(1), np.nan)
    df['last_confirmed_swing_low'] = df['confirmed_swing_low'].ffill()

    return df
