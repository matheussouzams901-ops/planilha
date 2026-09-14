import base64
from datetime import datetime
import hashlib
from io import BytesIO
import re
import sqlite3
from fpdf import FPDF
from google import genai
from google.genai import types
import openpyxl
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# -----------------------------------------------------------------------------
# Configuração da Página
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="DataSight Analytics Enterprise",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# Design System & Estilização CSS Enterprise
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .stApp {
        background-color: #F8FAFC;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    .executive-header {
        background: #ffffff;
        padding: 20px 28px;
        border-radius: 16px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.03);
        margin-bottom: 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .header-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #0F172A;
        letter-spacing: -0.02em;
        margin: 0;
    }
    .header-badge {
        background: #EFF6FF;
        color: #2563EB;
        padding: 6px 12px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        border: 1px solid #BFDBFE;
    }

    .kpi-container {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;
        margin-bottom: 24px;
    }
    .kpi-card-pro {
        background: #FFFFFF;
        padding: 20px;
        border-radius: 14px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        transition: all 0.2s ease-in-out;
        position: relative;
        overflow: hidden;
    }
    .kpi-card-pro::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
        background: #2563EB;
    }
    .kpi-card-pro:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.08);
        border-color: #CBD5E1;
    }
    .kpi-label {
        font-size: 0.75rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .kpi-num {
        font-size: 1.75rem;
        font-weight: 700;
        color: #0F172A;
        margin: 6px 0 4px 0;
        letter-spacing: -0.02em;
    }
    .kpi-footer {
        font-size: 0.78rem;
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 4px;
    }
    .kpi-pos { color: #16A34A; }
    .kpi-neg { color: #DC2626; }
    .kpi-neu { color: #64748B; }

    .stChatMessage {
        background-color: transparent !important;
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 12px;
    }
    
    [data-testid="stChatMessage"]:nth-child(even) {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-left: 4px solid #2563EB !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
    }
    
    [data-testid="stChatMessage"]:nth-child(odd) {
        background-color: #F1F5F9 !important;
        border: 1px solid #E2E8F0 !important;
        border-left: 4px solid #0F172A !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 16px !important;
        background-color: #E2E8F0 !important;
        padding: 10px !important;
        border-radius: 16px !important;
        border: 1px solid #CBD5E1 !important;
        margin-bottom: 24px !important;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 12px !important;
        padding: 16px 32px !important;
        font-weight: 800 !important;
        font-size: 1.3rem !important;
        color: #334155 !important;
        transition: all 0.2s ease-in-out !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2563EB !important;
        color: #FFFFFF !important;
        box-shadow: 0 6px 16px rgba(37, 99, 235, 0.3) !important;
    }
    .stTabs [data-baseweb="tab-border"] {
        display: none !important;
    }

    .stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] > button {
        background-color: #2563EB !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.6rem 1.2rem !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2);
    }
    .stButton > button[kind="primary"]:hover, [data-testid="stFormSubmitButton"] > button:hover {
        background-color: #1D4ED8 !important;
    }

    [data-testid="stForm"] {
        border: none !important;
        padding: 0 !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# Criptografia & Banco de Dados
# -----------------------------------------------------------------------------
def gerar_hash_senha(senha: str) -> str:
  return hashlib.sha256(senha.encode("utf-8")).hexdigest()


def init_db():
  conn = sqlite3.connect("datasight_users.db")
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            api_key TEXT,
            sheet_url TEXT
        )
    """)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS historico_chat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            pergunta TEXT,
            resposta TEXT,
            data_hora DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
  conn.commit()
  conn.close()


def cadastrar_usuario(username, password, api_key, sheet_url):
  conn = sqlite3.connect("datasight_users.db")
  cursor = conn.cursor()
  pw_hash = gerar_hash_senha(password)
  try:
    cursor.execute(
        """
            INSERT INTO usuarios (username, password_hash, api_key, sheet_url)
            VALUES (?, ?, ?, ?)
        """,
        (username, pw_hash, api_key, sheet_url),
    )
    conn.commit()
    return True, "Usuário cadastrado com sucesso!"
  except sqlite3.IntegrityError:
    return False, "Nome de usuário já existe."
  except Exception as e:
    return False, f"Erro no banco: {e}"
  finally:
    conn.close()


def autenticar_usuario(username, password):
  conn = sqlite3.connect("datasight_users.db")
  cursor = conn.cursor()
  pw_hash = gerar_hash_senha(password)
  cursor.execute(
      """
        SELECT username, password_hash, api_key, sheet_url FROM usuarios 
        WHERE username = ? AND password_hash = ?
    """,
      (username, pw_hash),
  )
  user = cursor.fetchone()
  conn.close()
  return user


def salvar_historico_chat(username, pergunta, resposta):
  conn = sqlite3.connect("datasight_users.db")
  cursor = conn.cursor()
  cursor.execute(
      """
        INSERT INTO historico_chat (username, pergunta, resposta)
        VALUES (?, ?, ?)
    """,
      (username, pergunta, resposta),
  )
  conn.commit()
  conn.close()


def carregar_historico_chat(username):
  conn = sqlite3.connect("datasight_users.db")
  cursor = conn.cursor()
  cursor.execute(
      """
        SELECT pergunta, resposta FROM historico_chat 
        WHERE username = ? ORDER BY id ASC
    """,
      (username,),
  )
  rows = cursor.fetchall()
  conn.close()
  messages = []
  for req, resp in rows:
    messages.append({"role": "user", "content": req})
    messages.append({"role": "assistant", "content": resp})
  return messages


def atualizar_configuracoes_usuario(username, api_key, sheet_url):
  conn = sqlite3.connect("datasight_users.db")
  cursor = conn.cursor()
  cursor.execute(
      """
        UPDATE usuarios SET api_key = ?, sheet_url = ? WHERE username = ?
    """,
      (api_key, sheet_url, username),
  )
  conn.commit()
  conn.close()


init_db()


# -----------------------------------------------------------------------------
# Módulo de Autenticação
# -----------------------------------------------------------------------------
def gerenciar_autenticacao():
  if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

  if not st.session_state["logged_in"]:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
      st.markdown(
          """
            <div style="text-align: center; margin-bottom: 24px;">
                <h1 style="font-size: 2.2rem; font-weight: 800; color: #0F172A; margin: 0;">💎 DataSight</h1>
                <p style="color: #64748B; font-size: 0.95rem; margin-top: 4px;">Plataforma Executiva de Analytics & Inteligência</p>
            </div>
        """,
          unsafe_allow_html=True,
      )

      aba_login, aba_cadastro = st.tabs(["🔒 Login", "✨ Criar Conta"])

      with aba_login:
        with st.form(key="login_form", clear_on_submit=False):
          usuario = st.text_input("Usuário", key="login_user")
          senha = st.text_input("Senha", type="password", key="login_pass")
          submit_login = st.form_submit_button(
              "Acessar Plataforma", use_container_width=True
          )

          if submit_login:
            dados_user = autenticar_usuario(usuario, senha)
            if dados_user:
              st.session_state["logged_in"] = True
              st.session_state["username"] = dados_user[0]
              st.session_state["api_key"] = dados_user[2] or ""
              st.session_state["sheet_url"] = dados_user[3] or ""
              st.session_state["messages"] = carregar_historico_chat(
                  dados_user[0]
              )
              st.rerun()
            else:
              st.error("Credenciais inválidas.")

      with aba_cadastro:
        with st.form(key="cadastro_form", clear_on_submit=False):
          novo_user = st.text_input("Novo Usuário", key="cad_user")
          nova_senha = st.text_input(
              "Sua Senha", type="password", key="cad_pass"
          )
          nova_api_key = st.text_input(
              "Gemini API Key", type="password", key="cad_key"
          )
          nova_sheet_url = st.text_input(
              "Link Google Sheets", key="cad_url"
          )
          submit_cad = st.form_submit_button(
              "Concluir Cadastro", use_container_width=True
          )

          if submit_cad:
            if not novo_user or not nova_senha:
              st.warning("Preencha usuário e senha.")
            else:
              sucesso, msg = cadastrar_usuario(
                  novo_user, nova_senha, nova_api_key, nova_sheet_url
              )
              if sucesso:
                st.success(msg)
              else:
                st.error(msg)
    return False
  return True


if not gerenciar_autenticacao():
  st.stop()


# -----------------------------------------------------------------------------
# Processamento e Tratamento de Dados
# -----------------------------------------------------------------------------
def get_export_url(url: str) -> str:
  match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
  if match:
    sheet_id = match.group(1)
    return (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
    )
  return None


def tratar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
  df_limpo = df.copy()
  for col in df_limpo.columns:
    if pd.api.types.is_numeric_dtype(df_limpo[col]):
      continue
    if df_limpo[col].dtype == "object":
      try:
        s_limpa = (
            df_limpo[col]
            .astype(str)
            .str.replace("R$", "", regex=False)
            .str.replace(" ", "", regex=False)
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
            .str.strip()
        )
        converted = pd.to_numeric(s_limpa, errors="coerce")
        if converted.notna().sum() > len(df_limpo) * 0.4:
          df_limpo[col] = converted
      except Exception:
        pass
  return df_limpo


@st.cache_data(ttl=300)
def carregar_todas_abas(url: str):
  export_url = get_export_url(url)
  if not export_url:
    raise ValueError("Link do Google Sheets inválido.")
  dict_raw = pd.read_excel(export_url, sheet_name=None, engine="openpyxl")
  return {nome: tratar_dataframe(df) for nome, df in dict_raw.items()}


def preparar_contexto_completo(dict_dfs):
  contexto_partes = []
  for nome_aba, dataframe in dict_dfs.items():
    contexto_partes.append(
        f"\n--- ABA: {nome_aba} ({len(dataframe)} linhas) ---"
    )
    contexto_partes.append(
        "AMOSTRA DE DADOS:\n" + dataframe.head(100).to_string()
    )
  return "\n".join(contexto_partes)


def gerar_pdf(
    df: pd.DataFrame, resumo_ia: str, titulo: str = "Relatório Executivo"
) -> bytes:
  pdf = FPDF()
  pdf.add_page()
  pdf.set_font("Helvetica", "B", 18)
  pdf.set_text_color(15, 23, 42)
  pdf.cell(0, 10, titulo, new_x="LMARGIN", new_y="NEXT", align="L")

  pdf.set_font("Helvetica", "", 10)
  pdf.set_text_color(100, 116, 139)
  pdf.cell(
      0,
      10,
      "Gerado por DataSight Analytics Enterprise",
      new_x="LMARGIN",
      new_y="NEXT",
      align="L",
  )
  pdf.ln(5)

  pdf.set_font("Helvetica", "B", 14)
  pdf.set_text_color(15, 23, 42)
  pdf.cell(0, 10, "1. Métricas da Base", new_x="LMARGIN", new_y="NEXT")

  pdf.set_font("Helvetica", "", 11)
  pdf.set_text_color(51, 65, 85)
  pdf.multi_cell(
      0,
      8,
      f"- Registros Analisados: {len(df):,}\n- Atributos Mapeados:"
      f" {len(df.columns)}",
  )
  pdf.ln(5)

  if resumo_ia:
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(
        0, 10, "2. Diagnóstico de IA", new_x="LMARGIN", new_y="NEXT"
    )
    texto_limpo = resumo_ia.encode("latin-1", "replace").decode("latin-1")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(51, 65, 85)
    pdf.multi_cell(0, 6, texto_limpo)

  return pdf.output()


# -----------------------------------------------------------------------------
# Sidebar
# -----------------------------------------------------------------------------
with st.sidebar:
  st.markdown("### 💎 DataSight Pro")
  st.caption(f"Usuário ativo: **{st.session_state.get('username')}**")

  if st.button("Sair da Sessão", use_container_width=True):
    st.session_state.clear()
    st.rerun()

  st.divider()

  with st.expander("⚙️ Integrações & API", expanded=False):
    api_key = st.text_input(
        "Gemini API Key",
        value=st.session_state.get("api_key", ""),
        type="password",
    )
    sheet_url = st.text_input(
        "Google Sheets URL", value=st.session_state.get("sheet_url", "")
    )
    if st.button("Salvar Conexões", use_container_width=True):
      atualizar_configuracoes_usuario(
          st.session_state["username"], api_key, sheet_url
      )
      st.session_state["api_key"] = api_key
      st.session_state["sheet_url"] = sheet_url
      st.success("Salvo!")

  st.markdown("#### 📂 Fonte de Dados")
  arquivo_local = st.file_uploader(
      "Upload Planilha (XLSX / CSV)", type=["xlsx", "csv"]
  )
  btn_carregar = st.button(
      "Sincronizar Dados", use_container_width=True, type="primary"
  )

# Carregamento de dados
if btn_carregar or ("dict_dfs" not in st.session_state):
  if arquivo_local:
    try:
      if arquivo_local.name.endswith(".csv"):
        st.session_state["dict_dfs"] = {
            "Dados": tratar_dataframe(pd.read_csv(arquivo_local))
        }
      else:
        dfs_raw = pd.read_excel(arquivo_local, sheet_name=None)
        st.session_state["dict_dfs"] = {
            k: tratar_dataframe(v) for k, v in dfs_raw.items()
        }
      st.toast("Planilha sincronizada e tratada!", icon="💎")
    except Exception as e:
      st.error(f"Erro ao ler arquivo: {e}")
  elif sheet_url:
    try:
      with st.spinner("Sincronizando Google Sheets..."):
        st.session_state["dict_dfs"] = carregar_todas_abas(sheet_url)
        st.toast("Google Sheets conectado!", icon="💎")
    except Exception as e:
      st.error(f"Erro na conexão: {e}")

# -----------------------------------------------------------------------------
# Painel Principal
# -----------------------------------------------------------------------------
if "dict_dfs" in st.session_state:
  lista_abas = list(st.session_state["dict_dfs"].keys())

  # Top Bar Executiva
  c_head1, c_head2 = st.columns([3, 1])
  with c_head1:
    st.markdown(
        """
        <div class="executive-header">
            <div>
                <h1 class="header-title">Dashboard Executivo</h1>
                <span style="color: #64748B; font-size: 0.85rem;">Inteligência de Dados e Analytics em Tempo Real</span>
            </div>
            <span class="header-badge">● Sistema Conectado</span>
        </div>
    """,
        unsafe_allow_html=True,
    )
  with c_head2:
    aba_nome = st.selectbox("Selecione a Aba Ativa:", lista_abas)

  df_original = st.session_state["dict_dfs"][aba_nome].copy()

  # Filtros Globais
  with st.expander("🔍 Filtros de Segmentação", expanded=False):
    f_col1, f_col2 = st.columns(2)
    df_filtrado = df_original.copy()

    cols_data = []
    for c in df_original.columns:
      if pd.api.types.is_datetime64_any_dtype(df_original[c]):
        cols_data.append(c)
      else:
        try:
          parsed = pd.to_datetime(df_original[c], errors="coerce")
          if parsed.notna().sum() > len(df_original) * 0.5:
            df_original[c] = parsed
            cols_data.append(c)
        except Exception:
          pass

    with f_col1:
      if cols_data:
        col_data_sel = st.selectbox("Filtrar por Data:", cols_data)
        min_date = df_original[col_data_sel].min()
        max_date = df_original[col_data_sel].max()

        if pd.notna(min_date) and pd.notna(max_date):
          intervalo_data = st.date_input(
              "Período:",
              value=(min_date.date(), max_date.date()),
              min_value=min_date.date(),
              max_value=max_date.date(),
          )
          if len(intervalo_data) == 2:
            data_ini, data_fim = intervalo_data
            mask_data = (df_original[col_data_sel].dt.date >= data_ini) & (
                df_original[col_data_sel].dt.date <= data_fim
            )
            df_filtrado = df_filtrado[mask_data]

    with f_col2:
      col_filtro = st.selectbox(
          "Filtrar por Atributo:", ["(Nenhum)"] + list(df_original.columns)
      )
      if col_filtro != "(Nenhum)":
        valores_unicos = df_original[col_filtro].dropna().unique().tolist()
        val_selecionados = st.multiselect("Valores:", valores_unicos)
        if val_selecionados:
          df_filtrado = df_filtrado[
              df_filtrado[col_filtro].isin(val_selecionados)
          ]

  df = df_filtrado

  # Cálculo Inteligente das Métricas
  cols_num = df.select_dtypes(include=["number"]).columns
  delta_text = "Estável"
  delta_class = "kpi-neu"
  soma_val = "N/A"
  media_val = "N/A"
  nome_col = cols_num[0] if len(cols_num) > 0 else "Métrica"

  if len(cols_num) > 0:
    val_total = df[cols_num[0]].sum()
    soma_val = f"{val_total:,.2f}"
    media_val = f"{df[cols_num[0]].mean():,.2f}"

    metade = len(df) // 2
    if metade > 0:
      val_ant = df[cols_num[0]].iloc[:metade].sum()
      val_rec = df[cols_num[0]].iloc[metade:].sum()
      if val_ant > 0:
        var_pct = ((val_rec - val_ant) / val_ant) * 100
        if var_pct > 0:
          delta_text = f"↑ +{var_pct:.1f}% vs período anterior"
          delta_class = "kpi-pos"
        elif var_pct < 0:
          delta_text = f"↓ {var_pct:.1f}% vs período anterior"
          delta_class = "kpi-neg"

  # KPI Cards em HTML Moderno
  st.markdown(
      f"""
    <div class="kpi-container">
        <div class="kpi-card-pro">
            <div class="kpi-label">Linhas Filtradas</div>
            <div class="kpi-num">{len(df):,}</div>
            <div class="kpi-footer kpi-neu">Base Total: {len(df_original):,}</div>
        </div>
        <div class="kpi-card-pro">
            <div class="kpi-label">Atributos (Colunas)</div>
            <div class="kpi-num">{len(df.columns)}</div>
            <div class="kpi-footer kpi-neu">Mapeamento concluído</div>
        </div>
        <div class="kpi-card-pro">
            <div class="kpi-label">Volume ({nome_col})</div>
            <div class="kpi-num">{soma_val}</div>
            <div class="kpi-footer {delta_class}">{delta_text}</div>
        </div>
        <div class="kpi-card-pro">
            <div class="kpi-label">Média ({nome_col})</div>
            <div class="kpi-num">{media_val}</div>
            <div class="kpi-footer kpi-neu">Média por registro</div>
        </div>
    </div>
    """,
      unsafe_allow_html=True,
  )

  # Tabs Corporativas
  tab_copilot, tab_bi, tab_geo, tab_explorer, tab_export = st.tabs([
      "💬 Copilot IA",
      "📈 Analytics & BI",
      "🗺️ Geográfico",
      "🗃️ Tabela de Dados",
      "📄 Exportar Relatório",
  ])

  # --- 1. COPILOT IA ---
  with tab_copilot:
    st.caption(
        "Consulte e analise os dados da sua organização em linguagem natural."
    )

    if "messages" not in st.session_state:
      st.session_state["messages"] = carregar_historico_chat(
          st.session_state["username"]
      )

    for msg in st.session_state["messages"]:
      avatar = "👤" if msg["role"] == "user" else "💎"
      with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

    if prompt_user := st.chat_input("Pergunte sobre os dados..."):
      if not api_key:
        st.error("Configure sua Gemini API Key na barra lateral para prosseguir.")
      else:
        with st.chat_message("user", avatar="👤"):
          st.markdown(prompt_user)

        with st.chat_message("assistant", avatar="💎"):
          with st.spinner("Analisando base de dados completa..."):
            try:
              client = genai.Client(api_key=api_key)
              dados_contexto = preparar_contexto_completo(
                  st.session_state["dict_dfs"]
              )

              system_instruction = f"""
Você é um consultor executivo de inteligência de dados. 
Responda de forma clara, profissional e mantenha o contexto completo da conversa para responder perguntas contínuas de acompanhamento.

BASE DE DADOS COMPLETA (TODAS AS ABAS):
{dados_contexto}
"""

              contents = []
              for msg in st.session_state["messages"]:
                role_name = "user" if msg["role"] == "user" else "model"
                contents.append(
                    types.Content(
                        role=role_name,
                        parts=[types.Part.from_text(text=msg["content"])],
                    )
                )

              contents.append(
                  types.Content(
                      role="user",
                      parts=[types.Part.from_text(text=prompt_user)],
                  )
              )

              res = client.models.generate_content(
                  model="gemini-3.6-flash",
                  contents=contents,
                  config=types.GenerateContentConfig(
                      system_instruction=system_instruction
                  ),
              )

              st.markdown(res.text)

              st.session_state["messages"].append(
                  {"role": "user", "content": prompt_user}
              )
              st.session_state["messages"].append(
                  {"role": "assistant", "content": res.text}
              )
              st.session_state["ultimo_resumo_ia"] = res.text

              salvar_historico_chat(
                  st.session_state["username"], prompt_user, res.text
              )

            except Exception as e:
              st.error(f"Erro na consulta: {e}")

  # --- 2. GERADOR DE GRÁFICOS (BUSCA MULTI-ABA INTELIGENTE) ---
  with tab_bi:
    c_g1, c_g2 = st.columns([1, 2])
    with c_g1:
      aba_fonte_grafico = st.selectbox(
          "Fonte dos Dados do Gráfico:",
          ["🔍 Buscar em Todas as Abas (Automático)"] + lista_abas,
      )

      with st.form("form_chart"):
        st.markdown("#### Gerar Visualização")
        prompt_chart = st.text_area(
            "Descreva o gráfico:",
            placeholder=(
                "Ex: quero um gráfico com as quantidades de pneus produzidos"
                " por cliente"
            ),
        )
        btn_chart = st.form_submit_button(
            "Gerar Gráfico", use_container_width=True
        )

    with c_g2:
      if btn_chart and prompt_chart:
        if not api_key:
          st.error("Informe a API Key na barra lateral.")
        else:
          with st.spinner(
              "Analisando a estrutura das abas e criando visualização..."
          ):
            try:
              client = genai.Client(api_key=api_key)

              # Mapeia a estrutura de TODAS as abas para enviar para a IA
              resumo_todas_abas = []
              for nome_a, df_a in st.session_state["dict_dfs"].items():
                cols_info = []
                for c in df_a.columns:
                  ex_vals = df_a[c].dropna().unique()[:3]
                  cols_info.append(f"    - '{c}' ({df_a[c].dtype}): ex {list(ex_vals)}")
                resumo_todas_abas.append(
                    f"ABA: '{nome_a}'\n" + "\n".join(cols_info)
                )

              contexto_abas_str = "\n\n".join(resumo_todas_abas)

              prompt_code = f"""
Você é um Especialista em Data Engineering e Plotly.
O usuário tem uma planilha contendo as seguintes abas e colunas:

{contexto_abas_str}

REGRAS OBRIGATÓRIAS:
1. O dicionário contendo todas as abas está carregado na variável 'dict_dfs' (onde a chave é o nome da aba e o valor é o DataFrame Pandas).
2. Se o usuário escolheu uma aba específica, use `df = dict_dfs['{aba_fonte_grafico}']`.
3. Se for 'Buscar em Todas as Abas (Automático)', escolha a ABA MAIS ADEQUADA que de fato contenha as colunas para atender ao pedido do usuário.
4. NUNCA escolha colunas de porcentagem ou de totais genéricos (como 'Variação vs...', 'Resultado Final') para o eixo de clientes ou nomes! Procure por colunas como 'Cliente', 'Razão Social', 'Nome', 'Vendedor', etc.
5. Faça o agrupamento correto .groupby().sum().reset_index(), ordene e mostre os dados.
6. A figura Plotly DEVE ser atribuída à variável `fig`.
7. Retorne APENAS o código Python válido dentro do bloco ```python ... ```.

SOLICITAÇÃO DO USUÁRIO: {prompt_chart}
"""

              res = client.models.generate_content(
                  model="gemini-3.6-flash", contents=prompt_code
              )
              match = re.search(r"```python\s*(.*?)\s*```", res.text, re.DOTALL)
              if match:
                codigo_gerado = match.group(1)
                scope = {
                    "dict_dfs": st.session_state["dict_dfs"],
                    "px": px,
                    "go": go,
                    "pd": pd,
                }
                exec(codigo_gerado, scope)
                if "fig" in scope:
                  scope["fig"].update_layout(template="plotly_white")
                  st.plotly_chart(scope["fig"], use_container_width=True)
                else:
                  st.error("Não foi possível gerar a figura Plotly ('fig').")
              else:
                st.error("Não foi possível processar o código gerado.")
            except Exception as e:
              st.error(f"Erro ao criar gráfico: {e}")

  # --- 3. ANÁLISE GEOGRÁFICA ---
  with tab_geo:
    cols_geo = [
        c
        for c in df.columns
        if any(
            p in c.lower()
            for p in ["estado", "uf", "cidade", "pais", "regiao", "local"]
        )
    ]

    if cols_geo and len(cols_num) > 0:
      col_geo_sel = st.selectbox("Coluna de Localidade:", cols_geo)
      col_val_sel = st.selectbox("Métrica:", cols_num)

      df_geo = (
          df.groupby(col_geo_sel)[col_val_sel]
          .sum()
          .reset_index()
          .sort_values(by=col_val_sel, ascending=False)
      )
      fig_geo = px.bar(
          df_geo,
          x=col_geo_sel,
          y=col_val_sel,
          color=col_val_sel,
          title=f"Distribuição por {col_geo_sel}",
          template="plotly_white",
          color_continuous_scale="Blues",
      )
      st.plotly_chart(fig_geo, use_container_width=True)
    else:
      st.info("Nenhuma coluna de localidade/geográfica detectada.")

  # --- 4. EXPLORADOR ---
  with tab_explorer:
    st.dataframe(df, use_container_width=True, height=450)

  # --- 5. EXPORTAR RELATÓRIO ---
  with tab_export:
    resumo_pdf = st.text_area(
        "Resumo Executivo para o PDF",
        value=st.session_state.get("ultimo_resumo_ia", ""),
        height=150,
    )

    if st.button("Gerar Relatório em PDF", use_container_width=True):
      try:
        pdf_bytes = gerar_pdf(
            df=df,
            resumo_ia=resumo_pdf,
            titulo=f"Relatório Executivo - {aba_nome}",
        )
        st.download_button(
            label="Baixar Arquivo PDF",
            data=bytes(pdf_bytes),
            file_name=f"Relatorio_{aba_nome}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
      except Exception as e:
        st.error(f"Erro ao gerar PDF: {e}")

else:
  st.info("👈 Conecte uma base de dados no menu lateral para visualizar.")
