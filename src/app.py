# src/app.py
import streamlit as st
import pandas as pd
from .api_client import APIFutebolClient
from .stats_engine import analisar_times
from .config import NUM_JOGOS_HISTORICO, CAMPEONATOS_BR, API_KEY

# Configurações da página Streamlit
st.set_page_config(page_title="Estatísticas Futebol BR", layout="wide")

st.title("⚽ Análise de Estatísticas do Futebol Brasileiro")
st.markdown("---")

# Verifica se a API_KEY está configurada
if not API_KEY:
    st.error("A chave da API (API_FUTEBOL_KEY) não está configurada. Por favor, defina-a nas variáveis de ambiente ou nos 'Secrets' do Streamlit Cloud.")
    st.stop() # Para a execução do app se a chave não estiver presente

# Funções com cache para evitar chamadas repetidas à API
@st.cache_data(ttl=3600, show_spinner="Buscando partidas de hoje...") # Cache por 1 hora
def obter_partidas_hoje():
    api = APIFutebolClient()
    return api.partidas_hoje_brasil()

@st.cache_data(ttl=3600, show_spinner="Analisando estatísticas históricas...") # Cache por 1 hora
def analisar_partida_completa(partida_info):
    api = APIFutebolClient()

    # Coletar histórico dos times
    hist_casa_info = api.partidas_anteriores_time(partida_info["time_casa_id"], NUM_JOGOS_HISTORICO)
    hist_fora_info = api.partidas_anteriores_time(partida_info["time_fora_id"], NUM_JOGOS_HISTORICO)

    if not hist_casa_info or not hist_fora_info:
        return None, "Histórico insuficiente para um ou ambos os times."

    # Coletar estatísticas detalhadas de cada partida histórica
    def coletar_stats_detalhadas(hist_list, time_id):
        stats = []
        for h in hist_list:
            est = api.estatisticas_partida_por_time(h["partida_id"])
            if not est:
                continue
            if h["mandante_id"] == time_id:
                stats.append(est["mandante"])
            else:
                stats.append(est["visitante"])
        return stats

    stats_casa = coletar_stats_detalhadas(hist_casa_info, partida_info["time_casa_id"])
    stats_fora = coletar_stats_detalhadas(hist_fora_info, partida_info["time_fora_id"])

    if not stats_casa or not stats_fora:
        return None, "Estatísticas detalhadas das partidas anteriores não encontradas."

    # Analisar e calcular probabilidades
    analise = analisar_times(stats_casa, stats_fora)
    return analise, None

# --- Interface do Streamlit ---

st.sidebar.header("Configurações")
# Exemplo de como listar campeonatos para o usuário escolher
# Para isso funcionar, CAMPEONATOS_BR precisa ser preenchido no config.py
if not CAMPEONATOS_BR:
    st.sidebar.warning("Nenhum ID de campeonato configurado em CAMPEONATOS_BR no `config.py`. O app pode não encontrar partidas.")
    if st.sidebar.button("Listar todos os Campeonatos (para pegar IDs)"):
        api_temp = APIFutebolClient()
        todos_camps = api_temp.listar_campeonatos()
        if todos_camps:
            st.sidebar.subheader("Todos os Campeonatos (IDs para `config.py`)")
            df_camps = pd.DataFrame(todos_camps)
            st.sidebar.dataframe(df_camps[['campeonato_id', 'nome']])
        else:
            st.sidebar.error("Não foi possível listar os campeonatos. Verifique sua chave da API.")


st.subheader("Partidas de Futebol Brasileiro para Hoje")

partidas_hoje = obter_partidas_hoje()

if not partidas_hoje:
    st.info("Nenhuma partida brasileira encontrada para hoje nos campeonatos configurados.")
else:
    # Cria uma lista de opções para o selectbox
    opcoes_partidas = [
        f"{p['time_casa_nome']} x {p['time_fora_nome']} - {p['campeonato_nome']} ({p['hora']})"
        for p in partidas_hoje
    ]

    partida_selecionada_idx = st.selectbox(
        "Selecione uma partida para analisar:",
        options=range(len(opcoes_partidas)),
        format_func=lambda x: opcoes_partidas[x]
    )

    partida_info = partidas_hoje[partida_selecionada_idx]

    st.markdown(f"**Partida:** {partida_info['time_casa_nome']} x {partida_info['time_fora_nome']}")
    st.markdown(f"**Campeonato:** {partida_info['campeonato_nome']}")
    st.markdown(f"**Data/Hora:** {partida_info['data']} às {partida_info['hora']}")
    st.markdown(f"**Status:** {partida_info['status']}")

    if st.button("Analisar Probabilidades"):
        with st.spinner("Calculando probabilidades... Isso pode levar alguns segundos."):
            analise_resultados, erro = analisar_partida_completa(partida_info)

        if erro:
            st.error(f"Erro na análise: {erro}")
        elif analise_resultados:
            st.subheader("Resultados da Análise")

            campos_analisados = ["chutes", "chutes_gol", "escanteios", "laterais"]

            for campo in campos_analisados:
                if campo in analise_resultados and analise_resultados[campo]["total"]["media"] is not None:
                    st.markdown(f"#### {campo.replace('_', ' ').title()}")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric(label=f"Média {partida_info['time_casa_nome']}", 
                                  value=f"{analise_resultados[campo]['casa']['media']:.2f}")
                    with col2:
                        st.metric(label=f"Média {partida_info['time_fora_nome']}", 
                                  value=f"{analise_resultados[campo]['fora']['media']:.2f}")
                    with col3:
                        st.metric(label="Média Total Estimada", 
                                  value=f"{analise_resultados[campo]['total']['media']:.2f}")
                    with col4:
                        if analise_resultados[campo]['total']['prob_gt_10'] is not None:
                            st.metric(label="Prob. Total > 10", 
                                      value=f"{analise_resultados[campo]['total']['prob_gt_10']*100:.1f}%")
                        if analise_resultados[campo]['total']['prob_gt_15'] is not None:
                            st.metric(label="Prob. Total > 15", 
                                      value=f"{analise_resultados[campo]['total']['prob_gt_15']*100:.1f}%")
                else:
                    st.info(f"Dados de {campo.replace('_', ' ').title()} não disponíveis ou insuficientes para análise.")
