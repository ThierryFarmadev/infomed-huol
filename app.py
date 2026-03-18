import streamlit as st
import requests
import sqlite3
import pandas as pd
import io
import time
import plotly.express as px
from datetime import datetime

# --- 1. CONFIGURAÇÃO E BANCO DE DADOS ---
st.set_page_config(page_title="INFOMED - HUOL", page_icon="🏥", layout="wide")

def iniciar_db():
    conn = sqlite3.connect('feedback_ic.db')
    c = conn.cursor()
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
            farmaco_label = st.session_state.get('farmaco_atual', 'LOTE/MULTIPLO')
            texto_excel = st.session_state.resposta_atual.replace("**", "").replace("#", "").replace("`", "")
            texto_excel = " ".join(texto_excel.splitlines()) 
            c.execute("INSERT INTO avaliacoes (data, farmaco, pergunta, resposta, status, observacao, analise_erro) VALUES (?,?,?,?,?,?,?)",
                      (data_atual, farmaco_label, st.session_state.pergunta_atual, texto_excel, status, obs, analise))
            conn.commit()
            conn.close()
            st.toast(f"✅ Registro salvo com sucesso!", icon="💾")
            st.rerun()
        except Exception as e: st.error(f"Erro ao salvar: {e}")

# Função centralizada para chamar a API
def consultar_gemini(prompt_completo):
    try:
        if "GEMINI_KEY" in st.secrets:
            CHAVE = st.secrets["GEMINI_KEY"]
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={CHAVE}"
            payload = {"contents": [{"parts": [{"text": prompt_completo}]}]}
            r = requests.post(url, json=payload, timeout=40)
            if r.status_code == 200:
                return r.json()['candidates'][0]['content']['parts'][0]['text'], None
            else:
                return None, f"Erro Google: {r.json().get('error', {}).get('message', 'Falha na API')}"
        else:
            return None, "Chave API não configurada nos Secrets."
    except Exception as e:
        return None, str(e)

iniciar_db()

# --- 2. CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #0e1117; }
    .sidebar-label { color: #5dade2; font-weight: 700; font-size: 0.8rem; margin-top: 25px; text-transform: uppercase; }
    .res-card { background: #1c1f26; padding: 25px; border-radius: 12px; border: 1px solid #30363d; color: #e6edf3; line-height: 1.8; margin-bottom: 20px;}
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
        obs_input = st.text_input("Justificativa:")
        if obs_input:
            if st.button("🤖 Analisar Causa do Erro", use_container_width=True):
                with st.spinner('IA analisando a falha...'):
                    prompt_debug = f"Compare sua resposta com a justificativa do especialista. Resposta: {st.session_state.resposta_atual}. Justificativa: {obs_input}. Explique a causa da divergência."
                    analise, erro = consultar_gemini(prompt_debug)
                    if analise:
                        st.session_state.analise_erro = analise
                        st.session_state.justificativa_temp = obs_input
                    else: st.error(erro)
            
            if st.session_state.get('analise_erro'):
                if st.button("Finalizar e Salvar"):
                    registrar_feedback("Divergente", st.session_state.justificativa_temp, st.session_state.analise_erro)
                    st.session_state.show_obs = False

    st.markdown('<p class="sidebar-label">📊 EXPORTAR</p>', unsafe_allow_html=True)
    if st.button("Gerar Planilha (.xlsx)", use_container_width=True):
        if not df_logs.empty:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_logs.to_excel(writer, index=False, sheet_name='Feedback_IC')
            st.download_button(label="📥 Baixar Excel", data=output.getvalue(), file_name=f"relatorio_huol_{datetime.now().strftime('%d_%m')}.xlsx", use_container_width=True)

# --- 4. CORPO PRINCIPAL ---
st.markdown('<h2 style="color:#5dade2; margin-bottom:0; font-weight:800;">INFOMED - SISTEMA DE PESQUISA HUOL</h2>', unsafe_allow_html=True)
st.caption("UFRN - EBSERH | Inteligência Artificial e Farmacovigilância")

# Abas com ícones mais discretos
tab1, tab2, tab3, tab4 = st.tabs(["🔍 Consulta Estruturada", "🔄 Processamento em Lote", "📚 Repositório", "📊 Dashboard"])

# --- ABA 1: CONSULTA ESTRUTURADA ---
with tab1:
    st.markdown("---")
    col1, col2 = st.columns([1, 1.5], gap="large")
    
    with col1:
        st.markdown("##### Entradas Clínicas")
        f_input = st.text_input("Fármaco(s) envolvido(s):", placeholder="Ex: Toxina Botulínica")
        p_input = st.text_area("Dúvida Técnica Específica:", placeholder="Ex: Tempo de exposição em TA por 12h...", height=120)
        c_input = st.text_input("Perfil do Paciente (Opcional):", placeholder="Ex: Adulto, sem comorbidades")
        
        st.markdown('<div class="analyze-btn">', unsafe_allow_html=True)
        # Botão sem emojis chamativos, foco na ação
        if st.button("Analisar Evidências (Gemini 3)", use_container_width=True):
            if f_input and p_input:
                with st.spinner('Construindo evidências (Gemini 3)...'):
                    contexto_paciente = f"Perfil do Paciente: {c_input}" if c_input else "Perfil do Paciente: Não especificado ou padrão adulto."
                    prompt_base = (
                        "Aja como farmacêutico clínico do HUOL. Estrutura obrigatória: 1. Alerta de Segurança, 2. Parecer Técnico (com % de Confiança), 3. Tabela Resumo, 4. Referência ABNT.\n\n"
                        f"Fármaco: {f_input}\n{contexto_paciente}\nDúvida: {p_input}"
                    )
                    
                    resposta, erro = consultar_gemini(prompt_base)
                    
                    if resposta:
                        pergunta_salva = f"Fármaco: {f_input} | Paciente: {c_input if c_input else 'N/A'}\nDúvida: {p_input}"
                        st.session_state.resposta_atual = resposta
                        st.session_state.pergunta_atual = pergunta_salva
                        st.session_state.farmaco_atual = f_input.upper()
                        st.rerun()
                    else:
                        st.error(erro)
            else:
                st.warning("Preencha ao menos o Fármaco e a Dúvida Técnica.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown("##### Resultado Técnico")
        if st.session_state.get('resposta_atual'):
            st.markdown(f'<div class="res-card">{st.session_state.resposta_atual}</div>', unsafe_allow_html=True)
            if st.session_state.get('analise_erro'):
                st.markdown('<div class="debug-card"><b>🕵️ Auditoria de IA:</b><br>' + st.session_state.analise_erro + '</div>', unsafe_allow_html=True)
        else:
            st.info("Preencha os dados e clique em Analisar Evidências para visualizar os resultados aqui.")

# --- ABA 2: PROCESSAMENTO EM LOTE ---
with tab2:
    st.markdown("---")
    st.markdown("### Processamento Automático de Planilhas")
    st.info("Suba um arquivo Excel (.xlsx) contendo uma coluna exatamente com o nome **Pergunta**. O sistema irá processar todas as linhas e gerar um arquivo para download.")
    
    arquivo_upload = st.file_uploader("Selecione sua planilha de testes", type=['xlsx'])
    
    if arquivo_upload is not None:
        try:
            df_lote = pd.read_excel(arquivo_upload)
            if 'Pergunta' not in df_lote.columns:
                st.error("Aviso: A planilha precisa ter uma coluna chamada 'Pergunta'.")
            else:
                st.success(f"Planilha carregada com sucesso! {len(df_lote)} itens encontrados.")
                if st.button("Iniciar Processamento em Lote"):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    respostas_lote = []
                    
                    prompt_lote = "Aja como farmacêutico do HUOL. Estrutura: Alerta, Parecer, Tabela, Referência ABNT.\n\nPergunta: "
                    
                    for index, row in df_lote.iterrows():
                        pergunta_atual = row['Pergunta']
                        status_text.text(f"Processando item {index + 1} de {len(df_lote)}...")
                        
                        resposta, erro = consultar_gemini(f"{prompt_lote} {pergunta_atual}")
                        
                        if resposta:
                            respostas_lote.append(resposta)
                        else:
                            respostas_lote.append(f"ERRO DE API: {erro}")
                            
                        progress_bar.progress((index + 1) / len(df_lote))
                        time.sleep(2) 
                    
                    df_lote['Resposta_IA'] = respostas_lote
                    df_lote['Avaliacao_Pesquisador'] = ""
                    
                    output_lote = io.BytesIO()
                    with pd.ExcelWriter(output_lote, engine='openpyxl') as writer:
                        df_lote.to_excel(writer, index=False, sheet_name='Resultados_IA')
                    
                    status_text.text("✅ Processamento concluído!")
                    st.download_button(label="Baixar Resultados do Lote", data=output_lote.getvalue(), file_name=f"lote_processado_{datetime.now().strftime('%d_%m')}.xlsx")
        except Exception as e:
            st.error(f"Erro ao ler arquivo: {e}")

# --- ABA 3 E 4 (Mantidos Iguais) ---
with tab3:
    st.markdown("---")
    df_v = df_logs[df_logs['status'] == 'De Acordo']
    if df_v.empty: st.info("Repositório vazio. Valide respostas para populá-lo.")
    else:
        for _, r in df_v[::-1].iterrows():
            with st.expander(f"💊 {r['farmaco']} - {r['data']}"):
                st.write(r['resposta'])

with tab4:
    st.markdown("---")
    if not df_logs.empty:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(px.pie(df_logs, names='status', color='status', hole=0.4, color_discrete_map={'De Acordo':'#5dade2', 'Divergente':'#e74c3c'}).update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)'), use_container_width=True)
        with col2:
            st.plotly_chart(px.bar(df_logs['farmaco'].value_counts().head(5).reset_index(), x='farmaco', y='count', color_discrete_sequence=['#5dade2']).update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)'), use_container_width=True)
    else:
        st.warning("Sem dados para exibir estatísticas.")

st.markdown('<br><div style="text-align: center; font-size: 0.7rem; color: gray;">Matheus Thierry | Pesquisador UFRN 2026</div>', unsafe_allow_html=True)