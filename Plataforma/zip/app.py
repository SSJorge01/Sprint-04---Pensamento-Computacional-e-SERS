# app.py
# -------------------------------------------------------------------
# FIAP x GoodWe – Starter (Streamlit + mock SEMS data) - v2
# Inclui modo "Real (SEMS)" usando demo@goodwe.com / GoodweSems123!@#
# -------------------------------------------------------------------
import os
import json
from pathlib import Path
from datetime import datetime, date, time as dtime, timedelta
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# Módulos locais
from ai import analisar_com_deterministico,analisar_expansao_deterministico

# Caminhos
ROOT = Path(__file__).parent
MOCK_PATH = ROOT / "data" / "mock_data_semanal.json"
logo_url = "data\Gemini_Generated_Image_hf67zmhf67zmhf67.png"


# ----------------------- Funções utilitárias ------------------------
def carregar_mock(path: Path) -> pd.DataFrame:
    """Carrega o arquivo JSON mock e devolve um DataFrame com datetime."""
    if not path.exists():
        st.error(f"Arquivo de mock não encontrado: {path}")
        return pd.DataFrame()
    
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    
    # Converter para DataFrame
    df = pd.DataFrame(payload)
    
    # Criar coluna de datetime combinando data e hora
    df["time"] = pd.to_datetime(df["data"] + " " + df["hora"])
    
    # Adicionar metadados (simulados)
    df.attrs["meta"] = {
        "plant_id": "PLANT_DEMO_001",
        "inverter_sn": "5010KETU229W6177",
        "timezone": "America/Sao_Paulo",
        "units": {
            "geracao_atual_kW": "kW",
            "geracao_acumulada_kWh": "kWh"
        }
    }
    
    return df

def kwh(x: float) -> str:
    return f"{x:,.2f} kWh".replace(",", "X").replace(".", ",").replace("X", ".")

def kw(x: float) -> str:
    return f"{x:,.2f} kW".replace(",", "X").replace(".", ",").replace("X", ".")

# Tema customizado GoodWe (dark mode + botões estilizados)
st.markdown("""
    <style>
    body {
        background-color: #121212;
        color: #FFFFFF;
    }
    p, li, .stMetric-value, .stMetric-label {
        color: #FAFAFA !important; /* Um branco levemente acinzentado */
    }
    .stButton>button {
        background-color: #E60012; /* vermelho GoodWe */
        color: white;
        border: 2px solid #E60012; /* Adiciona borda para consistência */
        border-radius: 12px;
        height: 3.2em;
        width: auto; 
        padding: 0 2em; 
        font-size: 18px;
        font-weight: bold;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #B5000E; /* vermelho escuro GoodWe */
        border-color: #B5000E;
        color: white; /* Manter branco no hover para melhor contraste */
    }
    .secondary-button .stButton>button {
        background-color: transparent;
        color: #E60012; /* Texto na cor da borda */
        border: 2px solid #E60012;
    }

    .secondary-button .stButton>button:hover {
        background-color: rgba(230, 0, 18, 0.1); /* Um fundo levemente avermelhado no hover */
        color: #B5000E;
        border-color: #B5000E;
    }
    .sidebar .sidebar-content {
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .sidebar .sidebar-content .logo-footer {
            margin-top: auto;
            text-align: center;
        }
    </style>
""", unsafe_allow_html=True)

def resumo_dia(df: pd.DataFrame) -> dict:
    """Calcula agregados simples para a análise."""
    if df.empty:
        return {}
    
    # Usar as colunas corretas do mock
    if "geracao_acumulada_kWh" in df.columns and not df["geracao_acumulada_kWh"].dropna().empty:
        energia_dia = float(df["geracao_acumulada_kWh"].dropna().iloc[-1])
    else:
        energia_dia = 0.0
        
    if "geracao_atual_kW" in df.columns and not df["geracao_atual_kW"].dropna().empty:
        idx_max = df["geracao_atual_kW"].idxmax()
        pico_p = float(df.loc[idx_max, "geracao_atual_kW"])
        pico_h = df.loc[idx_max, "time"] if "time" in df.columns else None
    else:
        pico_p, pico_h = 0.0, None
        
    # Como não temos dados de bateria no novo mock, vamos simular
    soc_ini = 40  # Valor simulado
    soc_fim = 85  # Valor simulado
    
    return {
        "energia_dia": energia_dia,
        "pico_potencia": pico_p,
        "hora_pico": pico_h,
        "soc_ini": soc_ini,
        "soc_fim": soc_fim,
    }

def resumo_semanal(df: pd.DataFrame) -> dict:
    """
    Calcula agregados para análise semanal.
    """
    if df.empty:
        return {}
    
    # Garantir que temos dados de uma semana completa
    df_semana = df.copy()
    df_semana['data'] = pd.to_datetime(df_semana['data'])
    
    # Agrupar por dia
    daily_stats = df_semana.groupby('data').agg({
        'geracao_acumulada_kWh': 'max',
        'consumo_acumulado_kWh': 'max',
        'geracao_atual_kW': 'max',
        'consumo_atual_kW': 'max',
        'excedente_kW': lambda x: (x > 0).sum()  # contar horas com excedente
    }).reset_index()
    
    # Calcular totais e médias
    total_geracao = daily_stats['geracao_acumulada_kWh'].sum()
    total_consumo = daily_stats['consumo_acumulado_kWh'].sum()
    media_geracao_diaria = daily_stats['geracao_acumulada_kWh'].mean()
    media_consumo_diario = daily_stats['consumo_acumulado_kWh'].mean()
    
    # Calcular autossuficiência
    autossuficiencia = (total_geracao / total_consumo) * 100 if total_consumo > 0 else 0
    
    # Encontrar melhor e pior dia
    melhor_dia = daily_stats.loc[daily_stats['geracao_acumulada_kWh'].idxmax()]
    pior_dia = daily_stats.loc[daily_stats['geracao_acumulada_kWh'].idxmin()]
    
    # Calcular horas de excedente em média por dia
    horas_excedente_media = daily_stats['excedente_kW'].mean()
    
    return {
        'total_geracao': total_geracao,
        'total_consumo': total_consumo,
        'autossuficiencia': autossuficiencia,
        'media_geracao_diaria': media_geracao_diaria,
        'media_consumo_diario': media_consumo_diario,
        'melhor_dia': {
            'data': melhor_dia['data'],
            'geracao': melhor_dia['geracao_acumulada_kWh'],
            'pico_geracao': melhor_dia['geracao_atual_kW']
        },
        'pior_dia': {
            'data': pior_dia['data'],
            'geracao': pior_dia['geracao_acumulada_kWh'],
            'pico_geracao': pior_dia['geracao_atual_kW']
        },
        'horas_excedente_media': horas_excedente_media,
        'dias_analisados': len(daily_stats)
    }


# ---------------------------- UI -----------------------------------
st.set_page_config(page_title="GoodWe Assistant (MVP)", layout="wide", page_icon="⚡")
st.image("data\Gemini_Generated_Image_1rw6f31rw6f31rw6 (1)-Photoroom.png", width='stretch')
st.caption("1CCR - Grupo 3")

# Adicionar abas para organizar o conteúdo
tab1, tab2 = st.tabs(["📊 Dashboard", "🔋 Fluxo de Energia"])

with tab1:
    # (Conteúdo atual do dashboard mantido aqui)
    with st.sidebar:
        st.image("data\images.png", width='stretch')
        st.header("Configuração")
        modo = "Mock"
        # Adicionar seletor de visualização
        visualizacao = st.selectbox("Visualização", ["Diária", "Semanal"], index=0)
        # Comuns
        data_ref = st.date_input("Data", value=date(2025, 9, 1))
        


    # Carrega dados conforme modo
    if modo == "Mock":
        df = carregar_mock(MOCK_PATH)
        if not df.empty:
            if visualizacao == "Diária":
                # Filtrar pela data selecionada
                df = df[df["time"].dt.date == data_ref]
            else:
                # Para visualização semanal, usar toda a semana da data de referência
                start_of_week = data_ref - timedelta(days=data_ref.weekday())
                end_of_week = start_of_week + timedelta(days=6)
                df = df[(df["time"].dt.date >= start_of_week) & (df["time"].dt.date <= end_of_week)]
    # KPIs
    if df is not None and not df.empty:
        if visualizacao == "Diária":
            col1, col2, col3 = st.columns(3)
            res = resumo_dia(df)
            col1.metric("Energia do dia", kwh(res.get("energia_dia", 0.0)))
            if res.get("hora_pico"):
                col2.metric("Pico de potência", kw(res.get("pico_potencia", 0.0)), res["hora_pico"].strftime("%H:%M"))
            else:
                col2.metric("Pico de potência", "—")
            soc_ini = res.get("soc_ini")
            soc_fim = res.get("soc_fim")
            soc_txt = f"{soc_ini}% → {soc_fim}%" if soc_ini is not None and soc_fim is not None else "—"
            col3.metric("Bateria (início → fim)", soc_txt)

            # Gráficos

            st.subheader("Geração vs. Consumo (kW)")

            fig_diario_comparativo = go.Figure()

            # Adicionar linha de Geração
            if "geracao_atual_kW" in df.columns:
                fig_diario_comparativo.add_trace(go.Scatter(
                    x=df["time"], y=df["geracao_atual_kW"],
                    mode='lines+markers', name='Geração', line=dict(color='#00CC96')
                ))

            # Adicionar linha de Consumo
            if "consumo_atual_kW" in df.columns:
                fig_diario_comparativo.add_trace(go.Scatter(
                    x=df["time"], y=df["consumo_atual_kW"],
                    mode='lines+markers', name='Consumo', line=dict(color='#EF553B', dash='dash')
                ))

            fig_diario_comparativo.update_layout(
                yaxis_title='Potência (kW)',
                margin=dict(l=10, r=10, t=50, b=10)
            )
            st.plotly_chart(fig_diario_comparativo, use_container_width=True)

               # Botão Analisar  (determinístico)
            st.markdown("---")
            
            st.subheader("Análise do Dia")
            st.caption("Clique aqui para receber uma interpretação detalhada dos dados desta semana.")
            if st.button("Gerar Análise Dia", type="primary"): # Usar o tipo "primary" do Streamlit
                res_dia = resumo_dia(df)
                resposta = analisar_com_deterministico(res_dia, tipo="dia")
                st.markdown(resposta)
            
        else:  # Visualização Semanal
            st.header("📊 Análise Semanal")
            
            # Calcular resumo semanal
            res_semana = resumo_semanal(df)
            
            # KPIs da semana
            col1, col2, col3 = st.columns(3)
            col1.metric("Energia Total Gerada", kwh(res_semana['total_geracao']))
            col2.metric("Energia Total Consumida", kwh(res_semana['total_consumo']))
            col3.metric("Autossuficiência", f"{res_semana['autossuficiencia']:.1f}%")
            
            col4, col5, col6 = st.columns(3)
            col4.metric("Média Diária de Geração", kwh(res_semana['media_geracao_diaria']))
            col5.metric("Média Diária de Consumo", kwh(res_semana['media_consumo_diario']))
            col6.metric("Horas com Excedente/dia", f"{res_semana['horas_excedente_media']:.1f}")
            
            with st.expander("Ver gráfico detalhado de evolução"):
            # Mova o código dos gráficos para cá
            
                st.subheader("Evolução Diária")
                df_daily = df.groupby(df['data']).agg({
                    'geracao_acumulada_kWh': 'max',
                    'consumo_acumulado_kWh': 'max'
                }).reset_index()
                
                fig_daily = go.Figure()
                fig_daily.add_trace(go.Scatter(x=df_daily['data'], y=df_daily['geracao_acumulada_kWh'], 
                                        mode='lines+markers', name='Geração', 
                                        line=dict(color='#00CC96'), 
                                        marker=dict(symbol='circle'))) # Marcador circular
                fig_daily.add_trace(go.Scatter(x=df_daily['data'], y=df_daily['consumo_acumulado_kWh'], 
                                        mode='lines+markers', name='Consumo', 
                                        line=dict(color='#EF553B', dash='dash'), # Linha tracejada
                                        marker=dict(symbol='square'))) # Marcador quadrado
                fig_daily.update_layout(title='Geração e Consumo Diários',
                                    xaxis_title='Data',
                                    yaxis_title='Energia (kWh)')
                st.plotly_chart(fig_daily, use_container_width=True)
                #-------------------------------------------------------------------------------------------------
                
            
            # Gráfico de comparação entre melhor e pior dia
            st.subheader("Comparativo: Melhor vs Pior Dia")
            col7, col8 = st.columns(2)
            
            with col7:
                st.metric("Melhor Dia", res_semana['melhor_dia']['data'].strftime('%d/%m/%Y'),
                         delta=f"{res_semana['melhor_dia']['geracao']:.1f} kWh")
                st.write(f"Pico de geração: {res_semana['melhor_dia']['pico_geracao']:.2f} kW")
                
            with col8:
                st.metric("Pior Dia", res_semana['pior_dia']['data'].strftime('%d/%m/%Y'),
                        delta=f"-{res_semana['pior_dia']['geracao']:.1f} kWh")
                st.write(f"Pico de geração: {res_semana['pior_dia']['pico_geracao']:.2f} kW")
                      
                      
            # Agrupar por hora para ver padrões diários
            
            st.markdown("---")

            # 1. Botão de Ação Primária
            st.subheader("Análise da Semana")
            st.caption("Clique aqui para receber uma interpretação detalhada dos dados desta semana.")
            if 'info_visivel_1' not in st.session_state:
                st.session_state.info_visivel_1 = False
                
            if st.button("Gerar Análise Semanal", type="primary"): # Usar o tipo "primary" do Streamlit
                st.session_state.info_visivel_1 = not st.session_state.info_visivel_1
            if st.session_state.info_visivel_1:
                res_semana = resumo_semanal(df)
                resposta = analisar_com_deterministico(res_semana, tipo="semana")
                st.markdown(resposta)

            st.markdown("---")

            # 2. Botão de Ação Secundária (dentro de um expander para organização)
            with st.expander("Ver Análise de Planejamento Futuro"):
                st.caption("Avalie se seu sistema atual atende ao seu consumo e veja sugestões para o futuro.")
                if 'info_visivel' not in st.session_state:
                    st.session_state.info_visivel = False
                st.markdown('<div class = "secondary-button">', unsafe_allow_html=True )
                
                if st.button("Analisar Necessidade de Expansão"): # Estilo padrão/secundário
                    st.session_state.info_visivel = not st.session_state.info_visivel
                if st.session_state.info_visivel:
                    consumo_total = df["consumo_acumulado_kWh"].max()
                    producao_semanal_kwh = df["geracao_acumulada_kWh"].max()
                    resultado = analisar_expansao_deterministico(consumo_total, producao_semanal_kwh, periodo="7d")
                    st.markdown(resultado)
                st.markdown('</div>', unsafe_allow_html=True)




with tab2:
    st.header("🔋 Fluxo de Energia em Tempo Real")
    st.caption("Visualização simplificada do fluxo de energia dos painéis solares para os aparelhos")
    
    # Verificar se temos dados para mostrar
    if df is not None and not df.empty and visualizacao == "Diária":
        # Selecionar a hora atual para a visualização (última hora com dados)
        hora_atual = st.select_slider(
            "Selecione a hora para visualizar:",
            options=df['hora'].unique(),
            value=df['hora'].iloc[-1] if not df.empty else "06:00"
        )
        
        # Filtrar dados para a hora selecionada
        dados_hora = df[df['hora'] == hora_atual].iloc[0]
        
        # Calcular porcentagens para a visualização
        geracao_atual = dados_hora.get('geracao_atual_kW', 0)
        consumo_atual = dados_hora.get('consumo_atual_kW', 0)
        
        # Determinar se há excedente ou déficit
        excedente = max(0, geracao_atual - consumo_atual)
        deficit = max(0, consumo_atual - geracao_atual)
        #------------------------------
        carga_bateria = soc_fim
    
        # Adicionar diagrama simplificado
        st.subheader(f"Diagrama de Fluxo às {hora_atual}")

    # Focar e enriquecer este diagrama
        diagrama_col1, diagrama_col2, diagrama_col3, diagrama_col4 = st.columns(4)

        with diagrama_col1:
            st.markdown(f"### ☀️ Painéis")
            st.metric("Gerando", f"{geracao_atual:.2f} kW")

        with diagrama_col2:
            # Lógica das setas de fluxo pode ser melhorada aqui
            st.markdown(f"### ⚡ Inversor")
            if deficit > 0:
                st.markdown(f"**Importando da Rede:** {deficit:.2f} kW")

        with diagrama_col3:
            st.markdown(f"### 🔋 Bateria")
            # Mostrar o estado da bateria de forma mais clara
            estado_bateria = "Carregando ↗" if "06:00" <= hora_atual <= "18:00" else "Descarregando ↘" 
            st.markdown(f"**Estado:** {estado_bateria}")
            st.markdown(f"**Carga:** {carga_bateria}%") 

        with diagrama_col4:
            st.markdown(f"### 🏠 Casa")
            st.metric("Consumindo", f"{consumo_atual:.2f} kW")
            # Listar aparelhos ativos aqui
            aparelhos_bateria = dados_hora.get('aparelhos_bateria', 0)
            if aparelhos_bateria:
                st.write("**Ativos:**")
                for aparelho in aparelhos_bateria:
                    st.caption(f"- {aparelho['nome']}")
    else:
        st.info("Selecione a visualização 'Diária' e certifique-se de ter dados disponíveis para ver o fluxo de energia.")
