import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io
import google.generativeai as genai

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="INFOMED - HUOL", layout="wide", page_icon="💊")

# --- LÓGICA DE API KEY E MODELO ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    # Usando o modelo flash que é rápido e eficiente
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception:
    st.error("Erro: Chave de API não configurada nos Secrets.")
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
    conn = sqlite3.connect('infomed_huol.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM registros")
    total = c.fetchone()[0]
    conn.close()
    return total

def extrair_dados():
    conn = sqlite3.connect('infomed_huol.db')
    df = pd.read_sql_query("SELECT id, data, evidencia, resultado_ia, avaliacao FROM registros ORDER BY id DESC", conn)
    conn.close()
    return df

# Inicializar o banco
init_db()

# --- ESTILIZAÇÃO CSS ---
st.markdown("""
    <style>
    div.stButton > button {
        width: 100%;
        border-radius: 8px;
        background-color: #374151;
        color: #ffffff;
        border: 1px solid #4b5563;
        height: 3em;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover { background-color: #1f2937; }
    div.stButton > button p { font-size: 13px !important; font-weight: 500; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### :material/person_search: PESQUISADOR")
    with st.container(border=True):
        st.markdown(f"**Matheus Thierry**")
        st.caption("UFRN / HUOL")
    
    st.markdown("---")
    
    total_db = contar_registros()
    st.metric(label="Total de Registros", value=total_db)
    
    if st.button(":material/add_circle: Nova Consulta"):
        st.rerun()

    st.markdown("### :material/fact_check: AVALIAÇÃO")
    col_acordo, col_div = st.columns(2)
    
    with col_acordo:
        if st.button(":material/thumb_up: Acordo"):
            if 'ultima_analise' in st.session_state:
                salvar_registro(st.session_state.texto_enviado, st.session_state.ultima_analise, "Acordo")
                st.toast("Salvo no banco!", icon="✅")
                st.rerun()
            else:
                st.warning("Analise algo primeiro.")
            
    with col_div:
        if st.button(":material/thumb_down: Divergente"):
            if 'ultima_analise' in st.session_state:
                salvar_registro(st.session_state.texto_enviado, st.session_state.ultima_analise, "Divergente")
                st.toast("Divergência salva!", icon="⚠️")
                st.rerun()
            else:
                st.warning("Analise algo primeiro.")

    st.markdown("---")
    st.markdown("### :material/download: EXPORTAR")
    
    df_export = extrair_dados()
    if not df_export.empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_export.to_excel(writer, index=False)
        st.download_button(
            label=":material/description: Baixar Planilha",
            data=output.getvalue(),
            file_name=f'infomed_{datetime.now().strftime("%Y%m%d")}.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

# --- ÁREA PRINCIPAL ---
st.title("INFOMED - SISTEMA DE PESQUISA HUOL")
st.caption("UFRN - EBSERH | Inteligência Artificial e Farmacovigilância")

tab1, tab2, tab3 = st.tabs([":material/manage_search: Consulta Técnica", ":material/database: Repositório", ":material/dashboard: Dashboard"])

with tab1:
    evidencias = st.text_area("Insira as evidências:", height=200)
    
    if st.button(":material/analytics: Analisar Evidências", use_container_width=True):
        if evidencias:
            with st.spinner("Gemini analisando..."):
                try:
                    # CHAMADA REAL À API
                    response = model.generate_content(f"Analise as seguintes evidências farmacológicas e busque por divergências ou alertas de farmacovigilância: {evidencias}")
                    resultado_ia = response.text
                    
                    st.session_state.ultima_analise = resultado_ia
                    st.session_state.texto_enviado = evidencias
                    
                    st.success("Análise concluída!")
                    st.markdown(resultado_ia)
                except Exception as e:
                    st.error(f"Erro na API: {e}")
        else:
            st.warning("O campo está vazio.")

with tab2:
    st.markdown("### Histórico de Consultas")
    dados = extrair_dados()
    if not dados.empty:
        st.dataframe(dados, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum dado salvo.")

with tab3:
    if not df_export.empty:
        st.bar_chart(df_export['avaliacao'].value_counts())
    else:
        st.info("Sem dados para gráficos.")