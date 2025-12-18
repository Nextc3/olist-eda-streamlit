# etl/build_kpi_month.py

import pandas as pd
from pathlib import Path

# -----------------------
# Configurações de caminho
# -----------------------
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_RAW = BASE_DIR / "data" / "raw"
DATA_PROCESSED = BASE_DIR / "data" / "processed"

DATA_PROCESSED.mkdir(exist_ok=True)

print("📂 Diretório base:", BASE_DIR)

# -----------------------
# Leitura dos pedidos
# -----------------------
orders = pd.read_csv(
    DATA_RAW / "olist_orders_dataset.csv",
    parse_dates=[
        "order_purchase_timestamp",
        "order_delivered_customer_date",
        "order_estimated_delivery_date"
    ]
)

print("📦 Pedidos carregados:", orders.shape)

# -----------------------
# Colunas de tempo
# -----------------------
orders["year"] = orders["order_purchase_timestamp"].dt.year
orders["month"] = orders["order_purchase_timestamp"].dt.month
orders["year_month"] = orders["order_purchase_timestamp"].dt.to_period("M").astype(str)

# -----------------------
# Volume de pedidos
# -----------------------
orders_month = (
    orders
    .groupby("year_month")
    .agg(
        orders_total=("order_id", "nunique"),
        orders_delivered=("order_status", lambda x: (x == "delivered").sum()),
        orders_canceled=("order_status", lambda x: (x == "canceled").sum())
    )
    .reset_index()
)

orders_month["cancel_rate"] = (
    orders_month["orders_canceled"] / orders_month["orders_total"]
)

print("📊 Base mensal criada:", orders_month.shape)


# -----------------------
# Salvar base intermediária
# -----------------------
orders_month.to_parquet(
    DATA_PROCESSED / "orders_month_basic.parquet",
    index=False
)

print("✅ Arquivo salvo: orders_month_basic.parquet")

# -----------------------
# Leitura dos itens do pedido (valores)
# -----------------------
order_items = pd.read_csv(
    DATA_RAW / "olist_order_items_dataset.csv"
)

print("🧾 Itens carregados:", order_items.shape)

# -----------------------
# Agregação por pedido (evita duplicação)
# -----------------------
items_by_order = (
    order_items
    .groupby("order_id")
    .agg(
        items_count=("order_item_id", "count"),
        gmv=("price", "sum"),
        freight_total=("freight_value", "sum")
    )
    .reset_index()
)

print("💰 Itens agregados por pedido:", items_by_order.shape)

# -----------------------
# Join no nível do pedido
# -----------------------
orders_enriched = orders.merge(items_by_order, on="order_id", how="left")

print("🔗 Orders enriquecido:", orders_enriched.shape)

# -----------------------
# KPIs mensais financeiros (apenas delivered)
# -----------------------
delivered = orders_enriched[orders_enriched["order_status"] == "delivered"].copy()

kpi_fin_month = (
    delivered
    .groupby("year_month")
    .agg(
        gmv=("gmv", "sum"),
        freight_total=("freight_total", "sum"),
        items_count=("items_count", "sum"),
        orders_delivered_calc=("order_id", "nunique")
    )
    .reset_index()
)

kpi_fin_month["ticket_avg"] = kpi_fin_month["gmv"] / kpi_fin_month["orders_delivered_calc"]
kpi_fin_month["freight_avg"] = kpi_fin_month["freight_total"] / kpi_fin_month["orders_delivered_calc"]

print("📈 KPIs financeiros mensais:", kpi_fin_month.shape)

# -----------------------
# Merge: volume + finanças
# -----------------------
kpi_month = orders_month.merge(kpi_fin_month, on="year_month", how="left")

kpi_month["orders_delivered"] = kpi_month["orders_delivered_calc"]
kpi_month = kpi_month.drop(columns=["orders_delivered_calc"])



# -----------------------
# Salvar resultado do passo 4
# -----------------------
kpi_month.to_parquet(DATA_PROCESSED / "kpi_month_step4.parquet", index=False)
print("✅ Arquivo salvo: kpi_month_step4.parquet")

# -----------------------
# Leitura de pagamentos
# -----------------------
payments = pd.read_csv(DATA_RAW / "olist_order_payments_dataset.csv")
print("💳 Pagamentos carregados:", payments.shape)

# -----------------------
# Agregação de pagamentos por pedido
# -----------------------
payments_by_order = (
    payments
    .groupby("order_id")
    .agg(
        payment_value_total=("payment_value", "sum"),
        installments_max=("payment_installments", "max")
    )
    .reset_index()
)

print("🧮 Pagamentos agregados por pedido:", payments_by_order.shape)

# -----------------------
# Tipo principal de pagamento por pedido (maior valor)
# -----------------------
payments_sorted = payments.sort_values(["order_id", "payment_value"], ascending=[True, False])
payment_main_type = (
    payments_sorted
    .drop_duplicates("order_id")[["order_id", "payment_type"]]
    .rename(columns={"payment_type": "payment_type_main"})
)

payments_by_order = payments_by_order.merge(payment_main_type, on="order_id", how="left")


# -----------------------
# Join pagamentos no nível do pedido
# -----------------------
orders_enriched = orders_enriched.merge(payments_by_order, on="order_id", how="left")
print("🔗 Orders enriquecido + pagamentos:", orders_enriched.shape)

# -----------------------
# KPIs mensais de pagamento (apenas delivered)
# -----------------------
delivered = orders_enriched[orders_enriched["order_status"] == "delivered"].copy()

pay_month = (
    delivered
    .groupby("year_month")
    .agg(
        installments_avg=("installments_max", "mean"),
        installments_p75=("installments_max", lambda x: x.quantile(0.75))
    )
    .reset_index()
)

# shares de tipo de pagamento (principal)
type_counts = (
    delivered
    .groupby(["year_month", "payment_type_main"])
    .size()
    .reset_index(name="orders")
)

type_totals = type_counts.groupby("year_month")["orders"].sum().reset_index(name="orders_total")
type_counts = type_counts.merge(type_totals, on="year_month", how="left")
type_counts["share"] = type_counts["orders"] / type_counts["orders_total"]

# Pivot para colunas (credit_card, boleto etc.)
type_pivot = (
    type_counts
    .pivot(index="year_month", columns="payment_type_main", values="share")
    .fillna(0)
    .reset_index()
)

# Padronizar nomes das colunas para ficar estável
type_pivot = type_pivot.rename(columns={
    "credit_card": "payment_credit_share",
    "boleto": "payment_boleto_share"
})

# Se alguma não existir em algum mês, garante que a coluna exista
for col in ["payment_credit_share", "payment_boleto_share"]:
    if col not in type_pivot.columns:
        type_pivot[col] = 0.0

print("📊 KPIs mensais de pagamento:", pay_month.shape, type_pivot.shape)

# Merge pagamentos
kpi_month = kpi_month.merge(pay_month, on="year_month", how="left")
kpi_month = kpi_month.merge(type_pivot[["year_month", "payment_credit_share", "payment_boleto_share"]],
                            on="year_month", how="left")

# Salvar versão mais completa
kpi_month.to_parquet(DATA_PROCESSED / "kpi_month_step5.parquet", index=False)
print("✅ Arquivo salvo: kpi_month_step5.parquet")



