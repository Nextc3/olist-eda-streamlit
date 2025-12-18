# etl/build_kpi_executive.py

import pandas as pd
import numpy as np
from pathlib import Path
from scipy.stats import linregress

# -----------------------
# Paths
# -----------------------
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_PROCESSED = BASE_DIR / "data" / "processed"

INPUT_FILE = DATA_PROCESSED / "kpi_month_step5.parquet"
OUTPUT_FILE = DATA_PROCESSED / "kpi_month_executive.parquet"

# -----------------------
# Load data
# -----------------------
df = pd.read_parquet(INPUT_FILE)

# Período estatisticamente confiável
df = df[(df["year_month"] >= "2017-01") & (df["year_month"] <= "2018-08")].copy()

# Ordenação temporal
df = df.sort_values("year_month").reset_index(drop=True)

print("📊 Período analisado:", df["year_month"].min(), "→", df["year_month"].max())

# -----------------------
# Índices base 100 (base = média de 2017)
# -----------------------
base_2017 = df[df["year_month"].str.startswith("2017")]

def create_index(series, base_series):
    base_value = base_series.mean()
    return (series / base_value) * 100

df["ticket_index"] = create_index(df["ticket_avg"], base_2017["ticket_avg"])
df["installments_index"] = create_index(df["installments_avg"], base_2017["installments_avg"])
df["cancel_index"] = create_index(df["cancel_rate"], base_2017["cancel_rate"])

# -----------------------
# Tendências estatísticas
# -----------------------
def trend_analysis(series):
    x = np.arange(len(series))
    slope, intercept, r_value, p_value, std_err = linregress(x, series)
    return slope, p_value

trends = {}

for col in ["ticket_avg", "installments_avg", "cancel_rate"]:
    slope, pval = trend_analysis(df[col])
    trends[col] = {
        "slope": slope,
        "p_value": pval
    }

# -----------------------
# Interpretação automática
# -----------------------
def interpret_trend(slope, p_value, threshold=0.05):
    if p_value >= threshold:
        return "Estável (sem tendência estatisticamente significativa)"
    if slope > 0:
        return "Tendência de crescimento estatisticamente significativa"
    else:
        return "Tendência de queda estatisticamente significativa"

trend_text = {}

for metric, vals in trends.items():
    trend_text[metric] = interpret_trend(vals["slope"], vals["p_value"])

# -----------------------
# Anexar tendências ao dataframe
# -----------------------
for metric in trends:
    df[f"{metric}_trend_slope"] = trends[metric]["slope"]
    df[f"{metric}_trend_pvalue"] = trends[metric]["p_value"]
    df[f"{metric}_trend_text"] = trend_text[metric]

# -----------------------
# Save final dataset
# -----------------------
df.to_parquet(OUTPUT_FILE, index=False)
print("✅ Arquivo salvo:", OUTPUT_FILE.name)

