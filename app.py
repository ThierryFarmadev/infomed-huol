import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="INFOMED - HUOL", layout="wide", page_icon="💊")

# --- FUNÇÕES DO BANCO DE DATAS (SQLite) ---
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
    # Ordena pelo ID de forma decrescente para mostrar o mais recente primeiro
    df = pd.read_sql_query("SELECT id, data, evidencia, resultado_ia, avaliacao FROM registros ORDER BY id DESC", conn)
    conn.close()
    return df

# Inicializar o banco ao carregar o app
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

# --- LÓGICA DE API KEY ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    st.error("Erro: Chave de API não configurada nos Secrets.")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### :material/person_search: PESQUISADOR")
    with st.container(border=True):
        st.markdown(f"**Matheus Thierry**")
        st.caption("UFRN / HUOL")
    
    st.markdown("---")
    
    # Contador dinâmico do banco de dados
    total_db = contar_registros()
    st.metric(label="Total de Registros", value=total_db)
    
    if st.button(":material/add_circle: Nova Consulta"):
        st.rerun()

    st.markdown("### :material/fact_check: AVALIAÇÃO")
    col_acordo, col_div = st.columns(2)
    
    # Só permite avaliar se houver uma análise feita nesta sessão
    with col_acordo:
        if st.button(":material/thumb_up: Acordo"):
            if 'ultima_analise' in st.session_state:
                salvar_registro(st.session_state.texto_enviado, st.session_state.ultima_analise, "Acordo")
                st.toast("Salvo no banco de dados!", icon="✅")
                st.rerun()
            else:
                st.warning("Faça uma análise primeiro.")
            
    with col_div:
        if st.button(":material/thumb_down: Divergente"):
            if 'ultima_analise' in st.session_state:
                salvar_registro(st.session_state.texto_enviado, st.session_state.ultima_analise, "Divergente")
                st.toast("Divergência registrada!", icon="⚠️")
                st.rerun()
            else:
                st.warning("Faça uma análise primeiro.")

    st.markdown("---")
    st.markdown("### :material/download: EXPORTAR")
    
    # Lógica de Exportação para Excel
    df_export = extrair_dados()
    if not df_export.empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_export.to_excel(writer, index=False, sheet_name='Registros')
        processed_data = output.getvalue()
        st.download_button(
            label=":material/description: Baixar Planilha (.xlsx)",
            data=processed_data,
            file_name=f'infomed_huol_{datetime.now().strftime("%Y%m%d")}.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

# --- CONTEÚDO PRINCIPAL ---
st.title("INFOMED - SISTEMA DE PESQUISA HUOL")
st.caption("UFRN - EBSERH | Inteligência Artificial e Farmacovigilância")

tab1, tab2, tab3 = st.tabs([
    ":material/manage_search: Consulta Técnica", 
    ":material/folder_managed: Repositório Validado", 
    ":material/dashboard: Dashboard"
])

with tab1:
    evidencias = st.text_area("Insira as evidências:", height=200, placeholder="Texto para análise...")
    
if st.button(":material/analytics: Analisar Evidências", use_container_width=True):
        if evidencias:
            with st.spinner("IA processando..."):
                # --- AQUI É ONDE VOCÊ CHAMA SUA LÓGICA DA GEMINI ---
                # Supondo que você use o SDK do google-generativeai:
                # model = genai.GenerativeModel('gemini-1.5-flash')
                # response = model.generate_content(evidencias)
                # resultado_ia = response.text
                
                # Para testar agora, garanta que a variável abaixo receba a resposta da API:
                resultado_ia = realizar_chamada_gemini(evidencias) # Chame sua função aqui
                
                # Guardamos na memória temporária para poder salvar no banco depois
                st.session_state.ultima_analise = resultado_ia
                st.session_state.texto_enviado = evidencias
                
                st.success("Análise concluída!")
                st.write(resultado_ia)

with tab2:
    st.markdown("### :material/database: Histórico de Consultas Validadas")
    
    dados_repositorio = extrair_dados()
    
    if not dados_repositorio.empty:
        # Configuração avançada da tabela (st.column_config)
        st.dataframe(
            dados_repositorio,
            use_container_width=True,
            hide_index=True, # Esconde a coluna de índice do pandas
            column_config={
                "id": st.column_config.NumberColumn("Ref.", width="small"),
                "data": st.column_config.TextColumn("Data/Hora", width="medium"),
                "evidencia": st.column_config.TextColumn("Texto Submetido", width="large"),
                "resultado_ia": st.column_config.TextColumn("Análise da Gemini", width="large"),
                "avaliacao": st.column_config.SelectboxColumn(
                    "Status",
                    options=["Acordo", "Divergente"],
                    width="medium",
                )
            }
        )
        
        # Resumo rápido abaixo da tabela
        col_res1, col_res2 = st.columns(2)
        acordos = len(dados_repositorio[dados_repositorio['avaliacao'] == 'Acordo'])
        divergentes = len(dados_repositorio[dados_repositorio['avaliacao'] == 'Divergente'])
        
        col_res1.info(f"✅ **Acordos:** {acordos}")
        col_res2.warning(f"⚠️ **Divergências:** {divergentes}")
        
    else:
        st.info("O repositório ainda está vazio. Realize uma análise na aba 'Consulta Técnica'.")

with tab3:
    if not df_export.empty:
        st.subheader("Estatísticas de Avaliação")
        st.bar_chart(df_export['avaliacao'].value_counts())
    else:
        st.info("Aguardando dados para gerar gráficos.")