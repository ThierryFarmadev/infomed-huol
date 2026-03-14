import streamlit as st
import requests
import sqlite3
import pandas as pd
import io
import plotly.express as px  # Nova biblioteca para gráficos
from datetime import datetime

# --- 1. CONFIGURAÇÃO E BANCO DE DADOS ---
st.set_page_config(page_title="INFOMED - HUOL", page_icon="🏥", layout="wide")

def iniciar_db():
    conn = sqlite3.connect('feedback_ic.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS avaliacoes 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  data TEXT, farmaco TEXT, pergunta TEXT, 
                  resposta TEXT, status TEXT, observacao TEXT)''')
    conn.commit()
    conn.close()

def carregar_dados():
    try:
        conn = sqlite3.connect('feedback_ic.db')
        df = pd.read_sql_query("SELECT * FROM avaliacoes", conn)
        conn.close()
        return df
    except: return pd.DataFrame()

def registrar_feedback(status, obs=""):
    if st.session_state.get('resposta_atual'):
        try:
            conn = sqlite3.connect('feedback_ic.db')
            c = conn.cursor()
            data_atual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            farmaco_label = st.session_state.pergunta_atual.split()[0].upper()
            texto_excel = st.session_state.resposta_atual.replace("**", "").replace("#", "").replace("`", "")
            texto_excel = " ".join(texto_excel.splitlines()) 
            c.execute("INSERT INTO avaliacoes (data, farmaco, pergunta, resposta, status, observacao) VALUES (?,?,?,?,?,?)",
                      (data_atual, farmaco_label, st.session_state.pergunta_atual, texto_excel, status, obs))
            conn.commit()
            conn.close()
            st.toast(f"✅ Feedback registrado!", icon="💾")
            st.rerun() # Atualiza para os gráficos mudarem na hora
        except Exception as e: st.error(f"Erro ao salvar: {e}")

iniciar_db()

# --- 2. CSS PARA DESIGN REFINADO ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #0e1117; }
    .sidebar-label { color: #5dade2; font-weight: 700; font-size: 0.8rem; margin-top: 25px; text-transform: uppercase; letter-spacing: 1px; }
    .res-card { background: #1c1f26; padding: 30px; border-radius: 12px; border: 1px solid #30363d; color: #e6edf3; line-height: 1.8; }
    
    /* BOTÕES GLOBAIS */
    div.stButton > button {
        background-color: #2d333b !important;
        color: #adb5bd !important;
        font-weight: 600 !important;
        border-radius: 6px !important;
        border: 1px solid #444c56 !important;
    }
    
    /* BOTÃO ANALISAR */
    .analyze-btn button {
        background-color: #1a202c !important;
        color: #5dade2 !important;
        border: 1px solid #5dade2 !important;
        height: 50px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SIDEBAR ---
df_logs = carregar_dados()

with st.sidebar:
    st.markdown("### 🔬 PESQUISADOR")
    st.info(f"**Matheus Thierry**\n\nUFRN / HUOL")
    st.metric("Consultas Salvas", len(df_logs))

    if st.button("➕ Nova Consulta", use_container_width=True):
        st.session_state.pergunta_atual, st.session_state.resposta_atual = "", ""
        st.rerun()
    
    st.markdown('<p class="sidebar-label">✅ AVALIAÇÃO</p>', unsafe_allow_html=True)
    col_a, col_b = st.columns(2, gap="small")
    with col_a:
        if st.button("👍 Acordo", use_container_width=True): registrar_feedback("De Acordo")
    with col_b:
        if st.button("👎 Divergente", use_container_width=True): st.session_state.show_obs = True
    
    if st.session_state.get('show_obs', False):
        obs = st.text_input("Justificativa:")
        if st.button("Confirmar Registro"):
            registrar_feedback("Divergente", obs)
            st.session_state.show_obs = False

    st.markdown('<p class="sidebar-label">📊 EXPORTAR</p>', unsafe_allow_html=True)
    if st.button("Gerar Planilha (.xlsx)", use_container_width=True):
        if not df_logs.empty:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_logs.to_excel(writer, index=False, sheet_name='Feedback_IC')
            st.download_button(label="📥 Baixar Excel", data=output.getvalue(), 
                               file_name=f"relatorio_huol_{datetime.now().strftime('%d_%m')}.xlsx", use_container_width=True)

    st.markdown('<p class="sidebar-label">📂 HISTÓRICO</p>', unsafe_allow_html=True)
    busca = st.text_input("🔍 Buscar...", placeholder="Ex: Vancomicina", label_visibility="collapsed")
    
    if 'historico' in st.session_state:
        hist_filtrado = [h for h in st.session_state.historico if busca.upper() in h['label'].upper()]
        for idx, item in enumerate(reversed(hist_filtrado)):
            if st.button(f"📄 {item['label']}", key=f"h_{idx}", use_container_width=True):
                st.session_state.pergunta_atual, st.session_state.resposta_atual = item['pergunta'], item['resposta']
                st.rerun()

# --- 4. CORPO PRINCIPAL COM ABAS ---
st.markdown('<h2 style="color:#5dade2; margin-bottom:0; font-weight:800;">INFOMED - SISTEMA DE PESQUISA HUOL</h2>', unsafe_allow_html=True)
st.caption("UFRN - EBSERH | Inteligência Artificial e Farmacovigilância")

aba_consulta, aba_stats = st.tabs(["🔬 Consulta Técnica", "📊 Dashboard de Pesquisa"])

# --- ABA 1: CONSULTA ---
with aba_consulta:
    st.markdown("---")
    if st.session_state.get('resposta_atual'):
        col_input, col_output = st.columns([1, 2], gap="large")
    else:
        col_input, col_output = st.container(), None

    with col_input:
        st.markdown("##### 📝 Entrada de Dados")
        p_input = st.text_area("Digite sua dúvida técnica:", 
                               value=st.session_state.get('pergunta_atual', ""), 
                               placeholder="Ex: Vancomicina - Estabilidade após reconstituição...", 
                               height=280, label_visibility="collapsed")
        
        st.markdown('<div class="analyze-btn">', unsafe_allow_html=True)
        if st.button("▶️ Analisar Evidências", use_container_width=True):
            if p_input:
                with st.spinner('Acessando Gemini 3 Flash Preview...'):
                    try:
                        CHAVE = st.secrets["GEMINI_KEY"]
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={CHAVE}"
                        prompt = "Aja como farmacêutico do HUOL. Estrutura: Alerta, Parecer (Confiança % e Fontes), Tabela, Referência ABNT."
                        payload = {"contents": [{"parts": [{"text": f"{prompt}\n\nPergunta: {p_input}"}]}]}
                        r = requests.post(url, json=payload, timeout=30)
                        data = r.json()
                        
                        if r.status_code == 200:
                            res = data['candidates'][0]['content']['parts'][0]['text']
                            st.session_state.resposta_atual, st.session_state.pergunta_atual = res, p_input
                            label = p_input.split()[0].upper()
                            if 'historico' not in st.session_state: st.session_state.historico = []
                            if not any(h['pergunta'] == p_input for h in st.session_state.historico):
                                st.session_state.historico.append({"label": label, "pergunta": p_input, "resposta": res})
                            st.rerun()
                        else: st.error(f"Erro na API: {data.get('error', {}).get('message')}")
                    except Exception as e: st.error(f"Erro: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

    if col_output:
        with col_output:
            st.markdown("##### 📄 Resultado Técnico")
            st.markdown(f'<div class="res-card">{st.session_state.resposta_atual}</div>', unsafe_allow_html=True)
            st.download_button("📥 Baixar Parecer (.txt)", st.session_state.resposta_atual, file_name="parecer.txt", use_container_width=True)

# --- ABA 2: DASHBOARD (ESTATÍSTICAS) ---
with aba_stats:
    st.markdown("---")
    if df_logs.empty:
        st.warning("Ainda não há dados suficientes para gerar estatísticas. Realize e avalie algumas consultas primeiro!")
    else:
        # Métricas de Topo
        m1, m2, m3 = st.columns(3)
        m1.metric("Total de Avaliações", len(df_logs))
        concordancia = (len(df_logs[df_logs['status'] == 'De Acordo']) / len(df_logs)) * 100
        m2.metric("Índice de Concordância", f"{concordancia:.1f}%")
        m3.metric("Fármacos Distintos", df_logs['farmaco'].nunique())

        st.markdown("### 📈 Análise de Performance Científica")
        c1, c2 = st.columns(2)

        with c1:
            st.markdown("**Distribuição de Feedbacks (Acordo vs Divergente)**")
            fig_pizza = px.pie(df_logs, names='status', color='status',
                               color_discrete_map={'De Acordo':'#5dade2', 'Divergente':'#e74c3c'},
                               hole=0.4)
            fig_pizza.update_layout(template="plotly_dark", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_pizza, use_container_width=True)

        with c2:
            st.markdown("**Top 5 Fármacos mais Consultados**")
            top_farmacos = df_logs['farmaco'].value_counts().head(5).reset_index()
            fig_barras = px.bar(top_farmacos, x='farmaco', y='count', 
                                labels={'count':'Consultas', 'farmaco':'Fármaco'},
                                color_discrete_sequence=['#5dade2'])
            fig_barras.update_layout(template="plotly_dark", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_barras, use_container_width=True)

st.markdown('<br><div style="font-size: 0.75rem; color: #5c6370; text-align: center;">Projeto de Iniciação Científica - Matheus Thierry / UFRN 2026.</div>', unsafe_allow_html=True)