import streamlit as st

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="INFOMED - HUOL", layout="wide", page_icon="💊")

# --- ESTILIZAÇÃO CSS CUSTOMIZADA ---
st.markdown("""
    <style>
    /* Padronização dos botões da Sidebar */
    div.stButton > button {
        width: 100%;
        border-radius: 8px;
        background-color: #374151; /* Cinza escuro */
        color: #ffffff;
        border: 1px solid #4b5563;
        height: 3em;
        transition: all 0.3s ease;
    }
    
    div.stButton > button:hover {
        background-color: #1f2937; /* Cinza ainda mais escuro no hover */
        border-color: #6b7280;
    }

    /* Ajuste de tamanho da fonte para os botões de avaliação */
    div.stButton > button p {
        font-size: 13px !important;
        font-weight: 500;
    }

    /* Estilização da área de texto */
    .stTextArea textarea {
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- LÓGICA DE API KEY (GitHub Secrets / Local) ---
# No GitHub, você deve ir em Settings > Secrets and Variables > Actions
# E adicionar uma Secret chamada GEMINI_API_KEY
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    st.error("Erro: Chave de API não configurada. Verifique os Secrets do GitHub ou o arquivo .streamlit/secrets.toml")
    st.stop()

# --- SIDEBAR (BARRA LATERAL) ---
with st.sidebar:
    st.markdown("### :material/person_search: PESQUISADOR")
    with st.container(border=True):
        st.markdown(f"**Matheus Thierry**")
        st.caption("UFRN / HUOL")
    
    st.markdown("---")
    
    # Métrica de Registros
    st.metric(label="Total de Registros", value="0")
    
    if st.button(":material/add_circle: Nova Consulta"):
        st.rerun()

    st.markdown("### :material/fact_check: AVALIAÇÃO")
    
    # Colunas para alinhar Acordo e Divergente perfeitamente
    col_acordo, col_div = st.columns(2)
    with col_acordo:
        if st.button(":material/thumb_up: Acordo"):
            st.toast("Avaliação positiva registrada!", icon="✅")
            
    with col_div:
        if st.button(":material/thumb_down: Divergente"):
            st.toast("Divergência reportada.", icon="⚠️")

    st.markdown("---")
    st.markdown("### :material/download: EXPORTAR")
    if st.button(":material/description: Gerar Planilha"):
        st.info("Função de exportação em desenvolvimento.")

# --- CONTEÚDO PRINCIPAL ---
st.title("INFOMED - SISTEMA DE PESQUISA HUOL")
st.caption("UFRN - EBSERH | Inteligência Artificial e Farmacovigilância")

# Abas com ícones modernos
tab1, tab2, tab3 = st.tabs([
    ":material/manage_search: Consulta Técnica", 
    ":material/folder_managed: Repositório Validado", 
    ":material/dashboard: Dashboard"
])

with tab1:
    # Campo de entrada de evidências
    evidencias = st.text_area(
        "Insira as evidências farmacológicas para análise:", 
        height=250, 
        placeholder="Cole aqui o texto para a Gemini analisar divergências..."
    )
    
    # Botão de ação principal
    if st.button(":material/analytics: Analisar Evidências (Gemini 3)", use_container_width=True):
        if evidencias:
            with st.spinner("IA processando dados e verificando farmacovigilância..."):
                # Aqui entra sua chamada para a API da Gemini usando 'api_key'
                # Exemplo: response = model.generate_content(evidencias)
                st.success("Análise concluída com sucesso!")
                # Aqui você exibe o resultado do seu analisador de divergência
        else:
            st.warning("Por favor, insira algum texto para análise.")

with tab2:
    st.info("O repositório de evidências validadas será exibido aqui.")

with tab3:
    st.info("Gráficos e estatísticas de farmacovigilância em tempo real.")

# --- RODAPÉ ---
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray; font-size: 12px;'>"
    "Matheus Thierry | Pesquisador UFRN 2026"
    "</div>", 
    unsafe_allow_html=True
)