# 📊 Análise Exploratória do E-commerce Brasileiro (Olist)

Este projeto realiza uma **análise exploratória de dados (EDA)** sobre o comportamento
de compra no e-commerce brasileiro entre **2017 e 2018**, utilizando dados reais do
marketplace **Olist**.

A análise é apresentada por meio de um **dashboard interativo em Streamlit**, organizado
em camadas executiva, analítica e técnica, com foco em **clareza, rigor metodológico e
apoio à tomada de decisão**.

---

## 🎯 Objetivo
Explorar padrões temporais, métricas financeiras e relações entre variáveis para responder
perguntas como:

- O volume de pedidos cresceu ao longo do período?
- O gasto médio por pedido (ticket) mudou?
- Houve mudança no comportamento de pagamento (crédito, boleto, parcelamento)?
- Existem sinais de aumento de risco (cancelamentos)?
- Como essas métricas se relacionam entre si?

---

## 🧠 Abordagem metodológica

- **Análise exploratória de dados (EDA)**  
- **Agregação mensal** de dados transacionais
- **Séries temporais** e índices normalizados (base 2017 = 100)
- **Regressão linear simples** para estimativa de tendências
- **Correlação de Pearson** para análise de associações
- Estudo **observacional**, sem inferência causal

---

## 📊 Estrutura do dashboard

### 🟢 Visão Executiva (dinâmica)
- KPIs com comparação temporal
- Recomendações automáticas condicionadas a critérios estatísticos
- Resumo interpretativo

### 🔎 Análise Exploratória (dinâmica)
- Séries temporais normalizadas
- Mix de pagamento
- Correlações entre métricas

### 🧪 Aspectos Técnicos (global + dinâmico)
- Tendências globais (2017–2018)
- Tendências locais por período selecionado
- Limitações metodológicas
- Glossário técnico

---

## ⚠️ Limitações
- Dados restritos a um único marketplace
- Ausência de variáveis macroeconômicas
- Análise observacional (não causal)
- Sensibilidade ao período selecionado

---

## 🛠️ Tecnologias
- Python
- Pandas, NumPy, SciPy
- Plotly
- Streamlit

---

## ▶️ Como executar localmente

```bash
# criar ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# instalar dependências
pip install -r requirements.txt

# rodar o app
streamlit run app.py
