import streamlit as st
import requests
import sqlite3
import pandas as pd
import io
import plotly.express as px
from datetime import datetime

# --- 1. CONFIGURAÇÃO E BANCO DE DADOS ---
st.set_page_config(page_title="INFOMED - HUOL", page_icon="🏥", layout="wide")

def iniciar_db():
    conn = sqlite3.connect('feedback_ic.db')
    c = conn.cursor()
    # Adicionada coluna 'analise_erro' para a nova funcionalidade
    c.execute('''CREATE TABLE IF NOT EXISTS avaliacoes 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  data TEXT, farmaco TEXT, pergunta TEXT, 
                  resposta TEXT, status TEXT, observacao TEXT, analise_erro TEXT)''')
    conn.commit()
    conn.close()

def carregar_dados():
    try:
        conn = sqlite3.connect('feedback_ic.db')
        df = pd.read_sql_query("SELECT * FROM avaliacoes", conn)
        conn.close()
        return df
    except: return pd.DataFrame()

def registrar_feedback(status, obs="", analise=""):
    if st.session_state.get('resposta_atual'):
        try:
            conn = sqlite3.connect('feedback_ic.db')
            c = conn.cursor()
            data_atual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            farmaco_label = st.session_state.pergunta_atual.split()[0].upper()
            texto_excel = st.session_state.resposta_atual.replace("**", "").replace("#", "").replace("`", "")
            texto_excel = " ".join(texto_excel.splitlines()) 
            c.execute("INSERT INTO avaliacoes (data, farmaco, pergunta, resposta, status, observacao, analise_erro) VALUES (?,?,?,?,?,?,?)",
                      (data_atual, farmaco_label, st.session_state.pergunta_atual, texto_excel, status, obs, analise))
            conn.commit()
            conn.close()
            st.toast(f"✅ Registro salvo com sucesso!", icon="💾")
            st.rerun()
        except Exception as e: st.error(f"Erro ao salvar: {e}")

iniciar_db()

# --- 2. CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #0e1117; }
    .sidebar-label { color: #5dade2; font-weight: 700; font-size: 0.8rem; margin-top: 25px; text-transform: uppercase; }
    .res-card { background: #1c1f26; padding: 25px; border-radius: 12px; border: 1px solid #30363d; color: #e6edf3; line-height: 1.8; }
    .debug-card { background: #2d1b1b; padding: 20px; border-radius: 8px; border: 1px solid #ff4b4b; color: #ffbcbc; margin-top: 15px; font-size: 0.9rem; }
    div.stButton > button { background-color: #2d333b !important; color: #adb5bd !important; font-weight: 600 !important; border-radius: 6px !important; }
    .analyze-btn button { background-color: #1a202c !important; color: #5dade2 !important; border: 1px solid #5dade2 !important; height: 50px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SIDEBAR ---
df_logs = carregar_dados()
with st.sidebar:
    st.markdown("### 🔬 PESQUISADOR")
    st.info(f"**Matheus Thierry**\n\nUFRN / HUOL")
    st.metric("Total de Registros", len(df_logs))

    if st.button("➕ Nova Consulta", use_container_width=True):
        st.session_state.pergunta_atual, st.session_state.resposta_atual, st.session_state.analise_erro = "", "", ""
        st.rerun()
    
    st.markdown('<p class="sidebar-label">✅ AVALIAÇÃO</p>', unsafe_allow_html=True)
    col_a, col_b = st.columns(2, gap="small")
    with col_a:
        if st.button("👍 Acordo", use_container_width=True): registrar_feedback("De Acordo")
    with col_b:
        if st.button("👎 Divergente", use_container_width=True): st.session_state.show_obs = True
    
    if st.session_state.get('show_obs', False):
        obs_input = st.text_input("Justificativa da Divergência:")
        if obs_input:
            if st.button("🤖 Analisar Causa do Erro", use_container_width=True):
                with st.spinner('IA analisando a falha...'):
                    try:
                        CHAVE = st.secrets["GEMINI_KEY"]
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={CHAVE}"
                        prompt_debug = (
                            f"Aja como um auditor de IA farmacêutica. Compare sua resposta anterior com a justificativa do especialista.\n"
                            f"Sua Resposta: {st.session_state.resposta_atual}\n"
                            f"Justificativa do Especialista: {obs_input}\n"
                            f"Explique de forma técnica e breve por que houve a divergência (ex: falta de dados locais, erro de interpretação)."
                        )
                        r = requests.post(url, json={"contents": [{"parts": [{"text": prompt_debug}]}]}, timeout=30)
                        if r.status_code == 200:
                            st.session_state.analise_erro = r.json()['candidates'][0]['content']['parts'][0]['text']
                            st.session_state.justificativa_temp = obs_input
                        else: st.error("Erro na auditoria.")
                    except: st.error("Falha na conexão.")
            
            if st.session_state.get('analise_erro'):
                st.warning("Auditoria concluída!")
                if st.button("Finalizar e Salvar Registro"):
                    registrar_feedback("Divergente", st.session_state.justificativa_temp, st.session_state.analise_erro)
                    st.session_state.show_obs = False

    st.markdown('<p class="sidebar-label">📊 EXPORTAR</p>', unsafe_allow_html=True)
    if st.button("Gerar Planilha (.xlsx)", use_container_width=True):
        if not df_logs.empty:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_logs.to_excel(writer, index=False, sheet_name='Feedback_IC')
            st.download_button(label="📥 Baixar Excel", data=output.getvalue(), 
                               file_name=f"relatorio_huol_{datetime.now().strftime('%d_%m')}.xlsx", use_container_width=True)

# --- 4. CORPO PRINCIPAL ---
st.markdown('<h2 style="color:#5dade2; margin-bottom:0; font-weight:800;">INFOMED - SISTEMA DE PESQUISA HUOL</h2>', unsafe_allow_html=True)
st.caption("UFRN - EBSERH | Inteligência Artificial e Farmacovigilância")

tab1, tab2, tab3 = st.tabs(["🔬 Consulta Técnica", "📚 Repositório Validado", "📊 Dashboard"])

with tab1:
    st.markdown("---")
    if st.session_state.get('resposta_atual'):
        c_in, c_out = st.columns([1, 2], gap="large")
    else:
        c_in, c_out = st.container(), None

    with c_in:
        p_input = st.text_area("Dúvida técnica:", value=st.session_state.get('pergunta_atual', ""), height=250, label_visibility="collapsed")
        st.markdown('<div class="analyze-btn">', unsafe_allow_html=True)
        if st.button("▶️ Analisar Evidências (Gemini 3)", use_container_width=True):
            if p_input:
                with st.spinner('Processando...'):
                    try:
                        CHAVE = st.secrets["GEMINI_KEY"]
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={CHAVE}"
                        prompt = "Aja como farmacêutico do HUOL. Estrutura: Alerta, Parecer (Confiança % e Fontes), Tabela, Referência ABNT."
                        r = requests.post(url, json={"contents": [{"parts": [{"text": f"{prompt}\n\nPergunta: {p_input}"}]}]}, timeout=30)
                        if r.status_code == 200:
                            res = r.json()['candidates'][0]['content']['parts'][0]['text']
                            st.session_state.resposta_atual, st.session_state.pergunta_atual = res, p_input
                            label = p_input.split()[0].upper()
                            if 'historico' not in st.session_state: st.session_state.historico = []
                            st.session_state.historico.append({"label": label, "pergunta": p_input, "resposta": res})
                            st.rerun()
                    except: st.error("Erro na API.")
        st.markdown('</div>', unsafe_allow_html=True)

    if c_out:
        with c_out:
            st.markdown("##### 📄 Resultado Técnico")
            st.markdown(f'<div class="res-card">{st.session_state.resposta_atual}</div>', unsafe_allow_html=True)
            if st.session_state.get('analise_erro'):
                st.markdown('<div class="debug-card"><b>🕵️ Auditoria de IA:</b><br>' + st.session_state.analise_erro + '</div>', unsafe_allow_html=True)

# --- ABA 2 E 3 (CÓDIGO MANTIDO DAS VERSÕES ANTERIORES) ---
with tab2:
    df_v = df_logs[df_logs['status'] == 'De Acordo']
    if df_v.empty: st.info("Repositório vazio.")
    else:
        for _, r in df_v[::-1].iterrows():
            with st.expander(f"💊 {r['farmaco']} - {r['data']}"):
                st.write(r['resposta'])

with tab3:
    if not df_logs.empty:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(px.pie(df_logs, names='status', color='status', hole=0.4, color_discrete_map={'De Acordo':'#5dade2', 'Divergente':'#e74c3c'}).update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)'), use_container_width=True)
        with col2:
            st.plotly_chart(px.bar(df_logs['farmaco'].value_counts().head(5).reset_index(), x='farmaco', y='count', color_discrete_sequence=['#5dade2']).update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)'), use_container_width=True)

st.markdown('<br><div style="text-align: center; font-size: 0.7rem; color: gray;">Matheus Thierry | UFRN 2026</div>', unsafe_allow_html=True)