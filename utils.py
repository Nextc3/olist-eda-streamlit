import pandas as pd
import numpy as np
from scipy.stats import linregress

def format_int(n): 
    return f"{int(n):,}".replace(",", ".")

def format_money(n):
    return f"{float(n):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def format_pct(x):
    if pd.isna(x):
        return "N/A"
    return f"{x*100:.2f}%".replace(".", ",")

def delta(cur, prev):
    if prev is None or pd.isna(prev) or prev == 0:
        return None
    if pd.isna(cur):
        return None
    return (cur - prev) / prev

def interpret_change(pct):
    if pct is None or pd.isna(pct):
        return None
    if pct >= 0.10:
        return "alta"
    if pct >= 0.03:
        return "leve alta"
    if pct <= -0.10:
        return "queda"
    if pct <= -0.03:
        return "leve queda"
    return "estável"

def interpret_corr(r):
    if abs(r) < 0.2:
        return "Correlação muito fraca ou inexistente"
    if abs(r) < 0.4:
        return "Correlação fraca"
    if abs(r) < 0.6:
        return "Correlação moderada"
    if abs(r) < 0.8:
        return "Correlação forte"
    return "Correlação muito forte"

def trend_local(series):
    series = series.dropna()
    if len(series) < 2:
        return 0.0, 1.0
    x = np.arange(len(series))
    slope, intercept, r, p_value, se = linregress(x, series)
    return slope, p_value

def interpret_trend(slope, p_value, alpha=0.05):
    if p_value >= alpha:
        return "Estável (sem tendência estatisticamente significativa)"
    return "Tendência de crescimento estatisticamente significativa" if slope > 0 else "Tendência de queda estatisticamente significativa"
