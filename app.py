import streamlit as st
import pandas as pd
from pathlib import Path
import plotly.express as px

# -----------------------
# Config
# -----------------------
st.set_page_config(
    page_title="Olist (2016–2018) — Análise Temporal",
    layout="wide"
)

BASE_DIR = Path(__file__).resolve().parent
DATA_PROCESSED = BASE_DIR / "data" / "processed"
DATA_FILE = DATA_PROCESSED / "kpi_month_executive.parquet"


# -----------------------
# Carregamento (cache)
# -----------------------
@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    # Garantir ordenação temporal
    df = df.sort_values("year_month").reset_index(drop=True)
    return df

st.title("📦 Olist (2016–2018) — Sinais temporais no e-commerce")
st.caption("Projeto Caio e Arthur.")

with st.sidebar:
    st.header("⚙️ Controles")
    modo_apresentacao = st.toggle("Modo apresentação (10 min)", value=True)

if not DATA_FILE.exists():
    st.error(f"Arquivo não encontrado: {DATA_FILE}")
    st.stop()

df = load_data(DATA_FILE)

if modo_apresentacao:
    st.success(
        "**Resumo (2017-01 a 2018-08)**\n"
        "• Crescimento consistente no volume de pedidos entregues.\n"
        "• Ticket médio sem tendência forte → crescimento extensivo.\n"
        "• Parcelamento e mix de pagamento ajudam a interpretar comportamento financeiro."
    )

with st.expander("🧭 Como ler este dashboard (rápido)"):
    st.markdown("""
        **Passo 1 — Selecione o período (🟢 dinâmico).**  
        Os KPIs e gráficos refletem apenas o intervalo escolhido.

        **Passo 2 — Leia o resumo executivo e as tendências.**  
        A seção executiva mostra *o que mudou* no período.  
        As tendências (🔵 globais) resumem o comportamento no intervalo 2017–2018.

        **Passo 3 — Explore relações e método.**  
        Aba Analítica: índices e correlações (EDA).  
        Aba Técnica: slopes/p-values, limitações e glossário.

        **Importante:** esta é uma análise exploratória e observacional; não há inferência causal.
        """)
    
st.markdown("""
**Perguntas que este dashboard ajuda a responder:**
- O volume de pedidos cresceu no período?  
- O gasto médio por pedido (ticket) mudou?  
- Houve mudança no comportamento de pagamento (crédito vs boleto, parcelamento)?  
- Existe sinal de aumento de risco (cancelamento)?  
- Como essas métricas se relacionam (correlação) ao longo do tempo?
""")


# -----------------------
# Filtro de período
# -----------------------
months = df["year_month"].tolist()
min_m, max_m = months[0], months[-1]

default_period = ("2017-01", "2018-08") if modo_apresentacao else (min_m, max_m)


period = st.select_slider(
    "Selecione o período",
    options=months,
    value=(min_m, max_m)
)

df_f = df[(df["year_month"] >= period[0]) & (df["year_month"] <= period[1])].copy()

# -----------------------
# KPIs Executivos (com delta)
# -----------------------
def format_int(n): 
    return f"{int(n):,}".replace(",", ".")

def format_money(n):
    return f"{float(n):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def format_pct(x):
    return f"{x*100:.2f}%".replace(".", ",")

# período atual (selecionado)
cur_orders = df_f["orders_delivered"].sum()
cur_gmv = df_f["gmv"].sum()
cur_ticket = cur_gmv / cur_orders if cur_orders else 0
cur_cancel = df_f["cancel_rate"].mean()

# delta: compara com o mesmo tamanho de janela anterior (se existir)
window = len(df_f)
df_all = df.copy()

start_idx = df_all.index[df_all["year_month"] == df_f["year_month"].iloc[0]][0]
prev_start = start_idx - window
prev_end = start_idx

has_prev = prev_start >= 0
if has_prev:
    df_prev = df_all.iloc[prev_start:prev_end]
    prev_orders = df_prev["orders_delivered"].sum()
    prev_gmv = df_prev["gmv"].sum()
    prev_ticket = prev_gmv / prev_orders if prev_orders else 0
    prev_cancel = df_prev["cancel_rate"].mean()
else:
    prev_orders = prev_gmv = prev_ticket = prev_cancel = None

def delta(cur, prev):
    if prev is None or prev == 0:
        return None
    return (cur - prev) / prev

d_orders = delta(cur_orders, prev_orders)
d_ticket = delta(cur_ticket, prev_ticket)
d_cancel = delta(cur_cancel, prev_cancel)

st.subheader("📌 Visão executiva")
c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Pedidos entregues",
    format_int(cur_orders),
    None if d_orders is None else format_pct(d_orders),
    help="Número de pedidos com status 'delivered' no período selecionado."
)

c2.metric(
    "GMV (R$)",
    format_money(cur_gmv),
    None if prev_gmv is None else format_pct(delta(cur_gmv, prev_gmv)),
    help="Gross Merchandise Value: soma do valor dos produtos (price) dos pedidos entregues."
)

c3.metric(
    "Ticket médio (R$)",
    format_money(cur_ticket),
    None if d_ticket is None else format_pct(d_ticket),
    help="Valor médio por pedido entregue: GMV ÷ pedidos entregues."
)

c4.metric(
    "Cancelamento médio",
    format_pct(cur_cancel),
    None if d_cancel is None else format_pct(d_cancel),
    help="Média mensal da taxa de cancelamento (pedidos cancelados ÷ pedidos totais) no período."
)

st.caption(
    "ℹ️ Recomendações automáticas são exibidas apenas quando existe um período anterior "
    "comparável, evitando conclusões sem base estatística."
)

with st.expander("ℹ️ Entenda quando as recomendações aparecem"):
    st.markdown("""
**Como funcionam as recomendações automáticas?**

As leituras exibidas neste painel são geradas por comparação entre o período selecionado
e um período imediatamente anterior de mesma duração.

Esse critério garante comparabilidade temporal e evita conclusões frágeis.

**Exemplos práticos:**
- ✔ *2017-07 a 2017-12* → recomendações exibidas  
- ❌ *2017-01 a 2018-08* → não há período anterior comparável  
- ❌ Períodos muito curtos → base estatística insuficiente  
""")


# -----------------------
# Recomendações acionáveis (texto automático)
# -----------------------


def interpret_change(pct):
    if pct is None:
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

if not has_prev:
    st.info(
        "Neste recorte não existe um período anterior comparável. "
        "As recomendações automáticas são omitidas por critério metodológico."
    )


insights = []



# Crescimento
if d_orders is not None:
    mov = interpret_change(d_orders)
    insights.append(f"📦 **Volume:** pedidos entregues em **{mov}** ({format_pct(d_orders)}).")

# Valor
d_gmv = None if prev_gmv is None else delta(cur_gmv, prev_gmv)
if d_gmv is not None:
    mov = interpret_change(d_gmv)
    insights.append(f"💰 **Receita bruta (GMV):** em **{mov}** ({format_pct(d_gmv)}).")

if d_ticket is not None:
    mov = interpret_change(d_ticket)
    insights.append(f"🎟️ **Ticket médio:** em **{mov}** ({format_pct(d_ticket)}).")

# Pressão financeira (parcelamento)
cur_inst = float(df_f["installments_avg"].mean()) if "installments_avg" in df_f.columns else None
prev_inst = float(df_prev["installments_avg"].mean()) if has_prev and "installments_avg" in df_prev.columns else None
d_inst = delta(cur_inst, prev_inst) if (cur_inst is not None and prev_inst is not None) else None

if d_inst is not None:
    mov = interpret_change(d_inst)
    insights.append(f"💳 **Parcelamento médio:** em **{mov}** ({format_pct(d_inst)}).")

# Risco
if d_cancel is not None:
    mov = interpret_change(d_cancel)
    insights.append(f"⚠️ **Cancelamento:** em **{mov}** ({format_pct(d_cancel)}).")

# Tendências globais (do dataset executivo)
trend_ticket = df_f["ticket_avg_trend_text"].iloc[0]
trend_inst = df_f["installments_avg_trend_text"].iloc[0]
trend_cancel = df_f["cancel_rate_trend_text"].iloc[0]

insights.append(f"📈 **Tendência (geral):** Ticket → *{trend_ticket}*.")
insights.append(f"📈 **Tendência (geral):** Parcelamento → *{trend_inst}*.")
insights.append(f"📈 **Tendência (geral):** Cancelamento → *{trend_cancel}*.")

st.markdown("### ✅ Leituras e recomendações (automáticas)")
st.write("Geração automática baseada no período selecionado e tendências do conjunto 2017–2018.")
for line in insights[:8]:
    st.write("- " + line)


st.caption("Delta compara o período selecionado com a janela imediatamente anterior de mesma duração (se existir).")

if modo_apresentacao:
    st.markdown("""
**Roteiro sugerido (10 min):**
1) **Executivo** — KPIs + leitura automática  
2) **Analítico** — índices base 100 + pagamento  
3) **Técnico** — slope/p-value + limitações  
4) **Glossário** — definições rápidas  
""")


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

import numpy as np
from scipy.stats import linregress

def trend_local(series):
    x = np.arange(len(series))
    slope, intercept, r, p_value, se = linregress(x, series)
    return slope, p_value

def interpret_trend(slope, p_value, alpha=0.05):
    if p_value >= alpha:
        return "Estável (sem tendência estatisticamente significativa)"
    return "Tendência de crescimento estatisticamente significativa" if slope > 0 else "Tendência de queda estatisticamente significativa"


tab1, tab2, tab3 = st.tabs(["📊 Executivo", "🔎 Analítico", "🧪 Técnico"])

with tab1:
    st.markdown("### 🧠 Leitura automática (tendências estatísticas)")

    st.caption("🔵 Tendências globais (2017–2018) — fixas por critério metodológico")
    st.info(f"**Ticket médio:** {df_f['ticket_avg_trend_text'].iloc[0]}")
    st.info(f"**Parcelamento médio:** {df_f['installments_avg_trend_text'].iloc[0]}")
    st.info(f"**Taxa de cancelamento:** {df_f['cancel_rate_trend_text'].iloc[0]}")

    st.divider()
    st.caption("🟢 Tendências do período selecionado — variam com o filtro")

    min_months = 6
    if len(df_f) >= min_months:
        s_ticket, p_ticket = trend_local(df_f["ticket_avg"])
        s_inst, p_inst = trend_local(df_f["installments_avg"])
        s_cancel, p_cancel = trend_local(df_f["cancel_rate"])

        st.success(f"**Ticket médio (local):** {interpret_trend(s_ticket, p_ticket)}  \n(slope={s_ticket:.4f}, p-value={p_ticket:.4f})")
        st.success(f"**Parcelamento médio (local):** {interpret_trend(s_inst, p_inst)}  \n(slope={s_inst:.4f}, p-value={p_inst:.4f})")
        st.success(f"**Cancelamento (local):** {interpret_trend(s_cancel, p_cancel)}  \n(slope={s_cancel:.6f}, p-value={p_cancel:.4f})")
    else:
        st.info("Tendências locais exigem pelo menos 6 meses no período selecionado.")


with tab2:
    st.markdown("## 🔎 Análise exploratória")

    # =====================================================
    # 1) Índices base 100 (comparação relativa)
    # =====================================================
    st.markdown("### 📈 Índices (base 2017 = 100)")
    st.write(
        "Os índices permitem comparar a evolução relativa das métricas, "
        "normalizando a média de 2017 como base 100."
    )

    import plotly.express as px

    idx_df = df_f[[
        "year_month",
        "ticket_index",
        "installments_index",
        "cancel_index"
    ]].copy()

    idx_df = idx_df.rename(columns={
        "ticket_index": "Ticket médio (índice)",
        "installments_index": "Parcelamento médio (índice)",
        "cancel_index": "Cancelamento (índice)"
    })

    idx_melt = idx_df.melt(
        id_vars="year_month",
        var_name="Métrica",
        value_name="Índice"
    )

    fig_idx = px.line(
        idx_melt,
        x="year_month",
        y="Índice",
        color="Métrica",
        markers=True,
        title="Evolução relativa das métricas (base 2017 = 100)"
    )

    fig_idx.update_layout(
        xaxis_title="Mês",
        yaxis_title="Índice"
    )

    st.plotly_chart(fig_idx, use_container_width=True)

    # =====================================================
    # 2) Mix de pagamento
    # =====================================================
    # =====================================================
    # 2) Mix de pagamento
    # =====================================================
    st.markdown("### 💳 Mix de pagamento")
    st.write("Participação relativa dos principais meios de pagamento ao longo do tempo.")

    pay = df_f[["year_month", "payment_credit_share", "payment_boleto_share"]].copy()
    pay = pay.rename(columns={
        "payment_credit_share": "Cartão de crédito",
        "payment_boleto_share": "Boleto"
    })

    pay_melt = pay.melt(
        id_vars="year_month",
        var_name="Tipo",
        value_name="Participação"
    )

    fig_pay = px.line(
        pay_melt,
        x="year_month",
        y="Participação",
        color="Tipo",
        markers=True,
        title="Participação por tipo de pagamento"
    )

    fig_pay.update_layout(
        xaxis_title="Mês",
        yaxis_title="Participação"
    )
    fig_pay.update_yaxes(tickformat=".0%")

    st.plotly_chart(fig_pay, use_container_width=True)

    # =====================================================
    # 3) Correlações (EDA clássico)
    # =====================================================
    st.markdown("### 🔗 Relações entre métricas (EDA clássico)")
    st.write(
        "Correlação de Pearson entre métricas mensais. "
        "O objetivo é identificar associações, não causalidade."
    )

    corr_df = df_f[[
        "ticket_avg",
        "installments_avg",
        "cancel_rate"
    ]].dropna()

    if len(corr_df) >= 6:  # mínimo razoável de observações
        r_ticket_inst = corr_df["ticket_avg"].corr(corr_df["installments_avg"])
        r_inst_cancel = corr_df["installments_avg"].corr(corr_df["cancel_rate"])

        c1, c2 = st.columns(2)

        c1.metric(
            "Correlação: Ticket × Parcelamento",
            f"{r_ticket_inst:.2f}",
            help="Correlação de Pearson entre ticket médio e parcelamento médio."
        )
        c1.caption(interpret_corr(r_ticket_inst))

        c2.metric(
            "Correlação: Parcelamento × Cancelamento",
            f"{r_inst_cancel:.2f}",
            help="Correlação de Pearson entre parcelamento médio e taxa de cancelamento."
        )
        c2.caption(interpret_corr(r_inst_cancel))

        st.caption(
            "ℹ️ Correlação mede associação linear e não implica causalidade. "
            "Resultados dependem do período selecionado."
        )

    else:
        st.info(
            "Correlação não exibida: número insuficiente de observações mensais "
            "no período selecionado."
        )
    
    





with tab3:
    st.markdown("## 🧪 Aspectos técnicos, conclusões e limitações")

    # =====================================================
    # 1) Conclusões automáticas
    # =====================================================
    st.markdown("### 📌 Conclusões do período analisado")

    st.caption(
    "🟢 **Dinâmico:** varia com o período selecionado | "
    "🔵 **Global:** calculado para todo o intervalo 2017–2018 (fixo por critério metodológico)"
    )


    conclusions = []

        # Conclusões dinâmicas (período selecionado)
    if d_orders is not None:
        conclusions.append(f"• No período selecionado, **pedidos entregues** variaram em {format_pct(d_orders)} (vs janela anterior comparável).")
    if d_ticket is not None:
        conclusions.append(f"• No período selecionado, **ticket médio** variou em {format_pct(d_ticket)} (vs janela anterior comparável).")
    if d_cancel is not None:
        conclusions.append(f"• No período selecionado, **cancelamento médio** variou em {format_pct(d_cancel)} (vs janela anterior comparável).")


    # Tendências globais
    conclusions.append(
        f"• O **ticket médio** apresentou: *{df_f['ticket_avg_trend_text'].iloc[0]}*."
    )
    conclusions.append(
        f"• O **parcelamento médio** apresentou: *{df_f['installments_avg_trend_text'].iloc[0]}*."
    )
    conclusions.append(
        f"• A **taxa de cancelamento** apresentou: *{df_f['cancel_rate_trend_text'].iloc[0]}*."
    )

    # Crescimento vs valor
    if d_orders is not None and d_ticket is not None:
        if d_orders > 0 and abs(d_ticket) < 0.03:
            conclusions.append(
                "• O crescimento observado foi predominantemente **extensivo**, "
                "impulsionado por aumento no número de pedidos."
            )
        elif d_ticket > 0:
            conclusions.append(
                "• Parte do crescimento foi associada a **aumento no valor médio por pedido**."
            )

    for c in conclusions:
        st.write(c)

    # =====================================================
    # 2) Limitações da análise
    # =====================================================
    st.markdown("### ⚠️ Limitações e considerações metodológicas")

    st.markdown("""
- O dataset representa transações de **um único marketplace**, não o e-commerce brasileiro como um todo.
- A análise é **observacional**, não permitindo inferência causal.
- Não há variáveis macroeconômicas explícitas (ex.: renda, inflação).
- Meses incompletos foram removidos para evitar viés de borda.
- Tendências foram estimadas por **regressão linear simples**, sensível ao período analisado.
""")

    # =====================================================
    # 3) Transparência estatística
    # =====================================================
    st.markdown("### 📊 Transparência estatística")
    st.markdown("### 🔵 Tendências globais (2017–2018)")
    st.caption(
    "As tendências abaixo foram estimadas para todo o período 2017–2018 "
    "por regressão linear simples. Elas não mudam com o período selecionado."
    )


    tech_df = pd.DataFrame([
        {
            "Métrica": "Ticket médio",
            "Slope": df_f["ticket_avg_trend_slope"].iloc[0],
            "p-value": df_f["ticket_avg_trend_pvalue"].iloc[0],
            "Interpretação": df_f["ticket_avg_trend_text"].iloc[0]
        },
        {
            "Métrica": "Parcelamento médio",
            "Slope": df_f["installments_avg_trend_slope"].iloc[0],
            "p-value": df_f["installments_avg_trend_pvalue"].iloc[0],
            "Interpretação": df_f["installments_avg_trend_text"].iloc[0]
        },
        {
            "Métrica": "Taxa de cancelamento",
            "Slope": df_f["cancel_rate_trend_slope"].iloc[0],
            "p-value": df_f["cancel_rate_trend_pvalue"].iloc[0],
            "Interpretação": df_f["cancel_rate_trend_text"].iloc[0]
        },
    ])

    st.dataframe(tech_df, use_container_width=True)
    with st.expander("📘 Glossário técnico (Análise Exploratória de Dados)"):
        st.markdown("""
            **Análise exploratória de dados (EDA)**  
            Abordagem voltada à exploração, visualização e compreensão dos dados, sem objetivo
            de inferência causal ou preditiva.

            **Análise observacional**  
            Análise baseada em dados observados, sem controle experimental ou intervenção.

            **Série temporal**  
            Conjunto de observações ordenadas no tempo. Neste projeto, os dados são agregados
            mensalmente.

            **Agregação mensal**  
            Processo de sumarizar dados transacionais (nível pedido/item) em métricas mensais.

            **Regressão linear simples**  
            Modelo estatístico utilizado para estimar tendências lineares ao longo do tempo.

            **Slope (coeficiente angular)**  
            Indica a direção e a intensidade da tendência estimada pela regressão linear.

            **p-value**  
            Probabilidade de observar uma tendência igual ou mais extrema assumindo ausência de
            tendência real. Valores baixos indicam maior evidência estatística.

            **Correlação de Pearson**  
            Mede a associação linear entre duas variáveis numéricas, variando entre −1 e +1.
            Não implica causalidade.

            **Normalização (índice base 100)**  
            Transformação que fixa a média de um período de referência como 100, permitindo
            comparações relativas ao longo do tempo.

            **EDA ≠ Inferência causal**  
            Os resultados indicam padrões, associações e tendências, mas não estabelecem relações
            de causa e efeito.
        """)

    
    with st.expander("🔍 Ver base mensal utilizada nesta análise"):
        st.dataframe(df_f, use_container_width=True)
    

