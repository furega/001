import streamlit as st
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime
from dateutil.relativedelta import relativedelta
import matplotlib.pyplot as plt

# Configuração da página
st.set_page_config(page_title="Indicadores Econômicos", layout="wide")
st.title("📊 Indicadores Econômicos")

# Entrada do usuário
entrada = st.text_input("Digite a quantidade de meses (ex: 12, 24, 36...) ou uma data no formato americano 'feb/24':")

if entrada:
    hoje = datetime.today()
    opcoes_validas = [12, 24, 36, 48, 60, 72, 84, 96, 108, 120]

    try:
        if entrada.isdigit() and int(entrada) in opcoes_validas:
            historico_meses = int(entrada)
            data_inicio = hoje - relativedelta(months=historico_meses + 1)
        else:
            data_inicio = datetime.strptime(entrada, '%b/%y')
            historico_meses = (hoje.year - data_inicio.year) * 12 + hoje.month - data_inicio.month
            if historico_meses < 1:
                st.error("Data de início inválida ou no futuro.")
                st.stop()
    except Exception:
        st.error("Entrada inválida. Use número (ex: 24) ou mês no formato americano 'feb/24'")
        st.stop()

    # --- Coleta de dados ---
    series = {
        'IGPM': 189, 'INCC': 192, 'IPCA': 433, 'CDI': 4391, 'POUP': 196
    }
    data_inicial = '01/01/2000'
    data_final = hoje.strftime('%d/%m/%Y')

    def consulta_bc(codigo, ini, fim):
        url = f'https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json&dataInicial={ini}&dataFinal={fim}'
        r = requests.get(url)
        if r.status_code != 200: return pd.Series(dtype=float)
        dados = r.json()
        df = pd.DataFrame(dados)
        df['data'] = pd.to_datetime(df['data'], dayfirst=True)
        df['valor'] = pd.to_numeric(df['valor'].str.replace(',', '.'), errors='coerce')
        return df.set_index('data')['valor']

    # Séries Bacen
    df_indices = pd.DataFrame()
    for nome, cod in series.items():
        s = consulta_bc(cod, data_inicial, data_final)
        if not s.empty:
            df_indices[nome] = s

    # Agregação mensal
    media = ['IGPM', 'INCC', 'IPCA']
    soma = ['CDI', 'POUP']
    aggs = {col: 'mean' if col in media else 'sum' for col in df_indices.columns}
    df_mensal = df_indices.resample('ME').agg(aggs)

    # Yahoo Finance
    inicio = data_inicio.strftime('%Y-%m-%d')
    fim = hoje.strftime('%Y-%m-%d')
    ibov = yf.download("^BVSP", start=inicio, end=fim)['Close'].resample('ME').last()
    usd = yf.download("USDBRL=X", start=inicio, end=fim)['Close'].resample('ME').last()

    mes_atual = hoje.strftime('%Y-%m')
    ibov = ibov[ibov.index.strftime('%Y-%m') < mes_atual]
    usd = usd[usd.index.strftime('%Y-%m') < mes_atual]
    df_mensal['IBOV MES'] = ibov
    df_mensal['DOLAR'] = usd
    df_mensal = df_mensal.dropna().tail(historico_meses)

    # Acumulados
    df_acum = df_mensal.copy()
    for col in media + soma:
        if col in df_acum:
            df_acum[f'{col}-A'] = ((1 + df_acum[col] / 100).cumprod() - 1) * 100
    if 'IBOV MES' in df_acum:
        base = df_acum['IBOV MES'].iloc[0]
        df_acum['IBOV MES-A'] = (df_acum['IBOV MES'] / base - 1) * 100
    if 'DOLAR' in df_acum:
        base = df_acum['DOLAR'].iloc[0]
        df_acum['DOLAR-A'] = (df_acum['DOLAR'] / base - 1) * 100

    # Tabela
    df_exibir = df_acum.copy()
    df_exibir.index = df_exibir.index.to_series().dt.strftime('%b/%y').str.lower()
    st.subheader("📋 Tabela de Indicadores")
    st.dataframe(df_exibir.style.format("{:,.2f}"))

    # Gráfico de barras acumulados
cols_acumulados = [col for col in df_acumulado.columns if col.endswith('-A')]
df_barras = df_acumulado[cols_acumulados].copy()
valores_finais = df_barras.iloc[-1].sort_values()

plt.figure(figsize=(7, 5))
bars = plt.bar(valores_finais.index, valores_finais.values, color='skyblue')
for bar in bars:
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2, height + 0.5, f'{height:.2f}%',
             ha='center', va='bottom', fontsize=10)
plt.title(f"Indicadores Acumulados dos Últimos {historico_meses} meses", fontsize=14)
plt.ylabel("Acumulado (%)")
plt.xticks(rotation=45)
plt.grid(axis='y', linestyle='--', alpha=0.5)
plt.ylim(valores_finais.min() - 5, valores_finais.max() + 6)
plt.tight_layout()
plt.show()
