import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io
import google.generativeai as genai
import plotly.express as px # Adicionado para o gráfico colorido

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="INFOMED - HUOL", layout="wide", page_icon="💊")

# --- LÓGICA DE API KEY E MODELO (GEMINI 3 FLASH PREVIEW) ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    # Mantido o modelo conforme sua instrução para evitar erros no projeto
    model = genai.GenerativeModel('gemini-3-flash-preview')
except Exception as e:
    st.error(f"Erro de Configuração: {e}")
    st.stop()

# --- FUNÇÕES DO BANCO DE DADOS (SQLite) ---
def init_db():
    conn = sqlite3.connect('infomed_huol.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS registros 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  data TEXT, 
                  evidencia TEXT, 
                  resultado_ia TEXT, 
                  avaliacao TEXT)''')
    conn.commit()
    conn.close()

def salvar_registro(evidencia, resultado_ia, avaliacao):
    conn = sqlite3.connect('infomed_huol.db')
    c = conn.cursor()
    data_atual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    c.execute("INSERT INTO registros (data, evidencia, resultado_ia, avaliacao) VALUES (?, ?, ?, ?)",
              (data_atual, evidencia, resultado_ia, avaliacao))
    conn.commit()
    conn.close()

def contar_registros():
    try:
        conn = sqlite3.connect('infomed_huol.db')
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM registros")
        total = c.fetchone()[0]
        conn.close()
        return total
    except:
        return 0

def extrair_dados():
    conn = sqlite3.connect('infomed_huol.db')
    df = pd.read_sql_query("SELECT id, data, evidencia, resultado_ia, avaliacao FROM registros ORDER BY id DESC", conn)
    conn.close()
    return df

# Inicializar o banco
init_db()

# --- ESTILIZAÇÃO CSS CUSTOMIZADA ---
st.markdown("""
    <style>
    /* Estilização dos Botões */
    div.stButton > button {
        width: 100%;
        border-radius: 8px;
        background-color: #374151; /* Cinza Escuro */
        color: #ffffff;
        border: 1px solid #4b5563;
        height: 3em;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        background-color: #1f2937;
        border-color: #6b7280;
    }
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

# --- SIDEBAR (BARRA LATERAL) ---
with st.sidebar:
    st.markdown("### :material/person_search: PESQUISADOR")
    with st.container(border=True):
        st.markdown(f"**Matheus Thierry**")
        st.caption("UFRN / HUOL")
    
    st.markdown("---")
    
    # Métrica do Banco de Dados
    st.metric(label="Total de Registros", value=contar_registros())
    
    if st.button(":material/add_circle: Nova Consulta"):
        if 'ultima_analise' in st.session_state:
            del st.session_state.ultima_analise
        st.rerun()

    st.markdown("### :material/fact_check: AVALIAÇÃO")
    col_acordo, col_div = st.columns(2)
    
    with col_acordo:
        if st.button(":material/thumb_up: Acordo"):
            if 'ultima_analise' in st.session_state:
                salvar_registro(st.session_state.texto_enviado, st.session_state.ultima_analise, "Acordo")
                st.toast("Registrado com sucesso!", icon="✅")
                st.rerun()
            else:
                st.warning("Analise algo primeiro.")
            
    with col_div:
        if st.button(":material/thumb_down: Divergente"):
            if 'ultima_analise' in st.session_state:
                salvar_registro(st.session_state.texto_enviado, st.session_state.ultima_analise, "Divergente")
                st.toast("Divergência salva no banco.", icon="⚠️")
                st.rerun()
            else:
                st.warning("Analise algo primeiro.")

    st.markdown("---")
    st.markdown("### :material/download: EXPORTAR")
    
    # Lógica de Exportação Corrigida (Aparece mesmo sem dados, mas desativado)
    dados_para_exportar = extrair_dados()
    if not dados_para_exportar.empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            dados_para_exportar.to_excel(writer, index=False, sheet_name='Registros')
        st.download_button(
            label=":material/description: Gerar Planilha (.xlsx)",
            data=output.getvalue(),
            file_name=f'infomed_huol_{datetime.now().strftime("%Y%m%d")}.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    else:
        # Mostra um botão desativado se o banco estiver vazio
        st.button(":material/description: Gerar Planilha (.xlsx)", disabled=True, help="O banco de dados está vazio. Realize análises primeiro.")

# --- ÁREA PRINCIPAL ---
st.title("INFOMED - SISTEMA DE PESQUISA HUOL")
st.caption("UFRN - EBSERH | Inteligência Artificial e Farmacovigilância")

tab1, tab2, tab3 = st.tabs([
    ":material/manage_search: Consulta Técnica", 
    ":material/database: Repositório", 
    ":material/dashboard: Dashboard"
])

with tab1:
    evidencias = st.text_area("Insira as evidências farmacológicas:", height=250, placeholder="Cole o texto aqui...")
    
    if st.button(":material/analytics: Analisar Evidências (Gemini 3)", use_container_width=True):
        if evidencias:
            with st.spinner("Gemini 3 Flash analisando dados..."):
                try:
                    # Chamada ao modelo específico do preview
                    prompt = f"Atue como um especialista em farmacovigilância clínica. Analise o seguinte texto em busca de divergências terapêuticas, riscos ou alertas importantes: {evidencias}"
                    response = model.generate_content(prompt)
                    
                    # Armazena para persistência
                    st.session_state.ultima_analise = response.text
                    st.session_state.texto_enviado = evidencias
                    
                    st.success("Análise concluída!")
                    st.markdown("---")
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"Erro na análise da API: {e}")
        else:
            st.warning("Por favor, preencha o campo de evidências.")

with tab2:
    st.markdown("### :material/history: Histórico de Consultas")
    dados_tabela = extrair_dados()
    if not dados_tabela.empty:
        st.dataframe(
            dados_tabela,
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": "Ref.",
                "data": "Data/Hora",
                "evidencia": "Texto",
                "resultado_ia": "Análise Gemini",
                "avaliacao": "Status"
            }
        )
    else:
        st.info("Nenhum registro encontrado no banco de dados.")

with tab3:
    if not dados_para_exportar.empty:
        st.subheader("Distribuição de Avaliações")
        
        # Prepara os dados para o gráfico do Plotly
        contagem = dados_para_exportar['avaliacao'].value_counts().reset_index()
        contagem.columns = ['Avaliação', 'Quantidade']
        
        # Gráfico com cores personalizadas
        fig = px.bar(
            contagem, 
            x='Avaliação', 
            y='Quantidade',
            color='Avaliação',
            color_discrete_map={
                'Acordo': '#1f77b4',     # Azul
                'Divergente': '#d62728'  # Vermelho
            },
            text='Quantidade' # Mostra o número em cima da barra
        )
        
        # Oculta a legenda redundante e ajusta layout
        fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Quantidade de Registros")
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Realize avaliações para visualizar as estatísticas.")

# --- RODAPÉ ---
st.markdown("---")
st.markdown("<div style='text-align: center; color: gray; font-size: 12px;'>Matheus Thierry | Pesquisador UFRN 2026</div>", unsafe_allow_html=True)