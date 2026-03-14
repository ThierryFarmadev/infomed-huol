import streamlit as st
import requests
import sqlite3
import pandas as pd
import io
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

def contar_registros():
    try:
        conn = sqlite3.connect('feedback_ic.db')
        df = pd.read_sql_query("SELECT id FROM avaliacoes", conn)
        conn.close()
        return len(df)
    except: return 0

def registrar_feedback(status, obs=""):
    if st.session_state.get('resposta_atual'):
        try:
            conn = sqlite3.connect('feedback_ic.db')
            c = conn.cursor()
            data_atual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            farmaco_label = st.session_state.pergunta_atual.split()[0].upper()
            # Limpeza básica para o Excel
            texto_excel = st.session_state.resposta_atual.replace("**", "").replace("#", "").replace("`", "")
            texto_excel = " ".join(texto_excel.splitlines()) 
            c.execute("INSERT INTO avaliacoes (data, farmaco, pergunta, resposta, status, observacao) VALUES (?,?,?,?,?,?)",
                      (data_atual, farmaco_label, st.session_state.pergunta_atual, texto_excel, status, obs))
            conn.commit()
            conn.close()
            st.toast(f"✅ Feedback registrado!", icon="💾")
        except Exception as e: st.error(f"Erro ao salvar: {e}")

iniciar_db()

# --- 2. CSS PARA DESIGN DARK (HUOL) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #0e1117; }
    .sidebar-label { color: #5dade2; font-weight: 700; font-size: 0.8rem; margin-top: 25px; text-transform: uppercase; letter-spacing: 1px; }
    .res-card { background: #1c1f26; padding: 30px; border-radius: 12px; border: 1px solid #30363d; color: #e6edf3; line-height: 1.8; }
    div.stButton > button:first-child { background-color: #004a87 !important; color: white !important; font-weight: 700 !important; border-radius: 8px !important; }
    .stButton button { font-size: 0.8rem !important; min-height: 40px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SIDEBAR (CONTROLES) ---
with st.sidebar:
    st.markdown("### 🔬 PESQUISADOR")
    st.info(f"**Matheus Thierry**\n\nUFRN / HUOL")
    st.metric("Consultas Salvas", contar_registros())

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
        conn = sqlite3.connect('feedback_ic.db')
        df = pd.read_sql_query("SELECT * FROM avaliacoes", conn)
        conn.close()
        if not df.empty:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Feedback_IC')
            st.download_button(label="📥 Baixar Excel", data=output.getvalue(), 
                               file_name=f"relatorio_huol_{datetime.now().strftime('%d_%m')}.xlsx", use_container_width=True)

    # --- HISTÓRICO COM BUSCA ---
    st.markdown('<p class="sidebar-label">📂 HISTÓRICO</p>', unsafe_allow_html=True)
    busca = st.text_input("🔍 Buscar...", placeholder="Ex: Vancomicina", label_visibility="collapsed")
    
    if 'historico' in st.session_state:
        hist_filtrado = [h for h in st.session_state.historico if busca.upper() in h['label'].upper()]
        for idx, item in enumerate(reversed(hist_filtrado)):
            if st.button(f"📄 {item['label']}", key=f"h_{idx}", use_container_width=True):
                st.session_state.pergunta_atual, st.session_state.resposta_atual = item['pergunta'], item['resposta']
                st.rerun()

# --- 4. CORPO PRINCIPAL ---
st.markdown('<h2 style="color:#5dade2; margin-bottom:0; font-weight:800;">INFOMED - PROTÓTIPO PARA O HUOL</h2>', unsafe_allow_html=True)
st.caption("UFRN - EBSERH | Suporte à Decisão Farmacêutica")
st.markdown("---")

# Layout dinâmico: se houver resposta, divide a tela
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
    
    if st.button("▶️ Analisar Evidências"):
        if p_input:
            with st.spinner('Acessando literaturas (Gemini 3)...'):
                try:
                    CHAVE = st.secrets["GEMINI_KEY"]
                except:
                    CHAVE = "AIzaSyCOhKK1vnm98_UUD63X2UZNPYUhmfwWOeE"
                
                # URL ATUALIZADA PARA GEMINI 3 FLASH PREVIEW
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={CHAVE}"
                
                try:
                    prompt = "Aja como farmacêutico do HUOL. Estrutura: Alerta, Parecer (Confiança % e Fontes), Tabela, Referência ABNT."
                    payload = {"contents": [{"parts": [{"text": f"{prompt}\n\nPergunta: {p_input}"}]}]}
                    r = requests.post(url, json=payload, timeout=30)
                    data = r.json()
                    
                    if r.status_code == 200 and 'candidates' in data:
                        res = data['candidates'][0]['content']['parts'][0]['text']
                        st.session_state.resposta_atual, st.session_state.pergunta_atual = res, p_input
                        
                        # Adiciona ao histórico
                        label = p_input.split()[0].upper()
                        if 'historico' not in st.session_state: st.session_state.historico = []
                        if not any(h['pergunta'] == p_input for h in st.session_state.historico):
                            st.session_state.historico.append({"label": label, "pergunta": p_input, "resposta": res})
                        st.rerun()
                    else:
                        erro_msg = data.get('error', {}).get('message', 'Erro desconhecido na API')
                        st.error(f"Erro na API 2026: {erro_msg}")
                except Exception as e: st.error(f"Erro de conexão: {e}")

if col_output:
    with col_output:
        st.markdown("##### 📄 Resultado Técnico")
        st.markdown(f'<div class="res-card">{st.session_state.resposta_atual}</div>', unsafe_allow_html=True)
        st.download_button("📥 Baixar Parecer (.txt)", st.session_state.resposta_atual, file_name="parecer_tecnico.txt")

st.markdown('<br><div style="font-size: 0.75rem; color: #5c6370; text-align: center;">Projeto de Iniciação Científica - Matheus Thierry / UFRN 2026.</div>', unsafe_allow_html=True)