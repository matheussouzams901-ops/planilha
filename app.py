import base64
from datetime import datetime
import hashlib
from io import BytesIO
import re
import sqlite3
from fpdf import FPDF
from google import genai
import openpyxl
import pandas as pd
import plotly.express as px
import streamlit as st

# -----------------------------------------------------------------------------
# Configuração da Página
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="DataSight Analytics Pro Enterprise",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp { background-color: #fafafa; }
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    }
    </style>
""",
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# Criptografia Nativa
# -----------------------------------------------------------------------------
def gerar_hash_senha(senha: str) -> str:
  return hashlib.sha256(senha.encode("utf-8")).hexdigest()


# -----------------------------------------------------------------------------
# Banco de Dados (SQLite com Migração Automática)
# -----------------------------------------------------------------------------
def init_db():
  conn = sqlite3.connect("datasight_users.db")
  cursor = conn.cursor()

  # Recria/Garante a tabela de usuários com a estrutura correta
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            username TEXT PRIMARY KEY,
            password_hash TEXT,
            api_key TEXT,
            sheet_url TEXT
        )
    """)

  # Trata caso a tabela antiga usava a coluna 'password'
  cursor.execute("PRAGMA table_info(usuarios)")
  colunas = [col[1] for col in cursor.fetchall()]
  if "password_hash" not in colunas:
    cursor.execute("DROP TABLE usuarios")
    cursor.execute("""
            CREATE TABLE usuarios (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                api_key TEXT,
                sheet_url TEXT
            )
        """)

  # Tabela de histórico de chat
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
    return False, "Nome de usuário já existe. Escolha outro."
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
# Autenticação e Login
# -----------------------------------------------------------------------------
def gerenciar_autenticacao():
  if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

  if not st.session_state["logged_in"]:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
      st.title("⚡ DataSight Enterprise")
      st.caption("Acesse sua conta para visualizar seus painéis.")

      aba_login, aba_cadastro = st.tabs(["🔑 Login", "📝 Novo Cadastro"])

      with aba_login:
        usuario = st.text_input("Usuário", key="login_user")
        senha = st.text_input("Senha", type="password", key="login_pass")

        if st.button("Entrar no Sistema", use_container_width=True):
          dados_user = autenticar_usuario(usuario, senha)
          if dados_user:
            st.session_state["logged_in"] = True
            st.session_state["username"] = dados_user[0]
            st.session_state["api_key"] = dados_user[2] or ""
            st.session_state["sheet_url"] = dados_user[3] or ""
            st.session_state["messages"] = carregar_historico_chat(
                dados_user[0]
            )
            st.success("Login efetuado com sucesso!")
            st.rerun()
          else:
            st.error("Usuário ou senha incorretos.")

      with aba_cadastro:
        novo_user = st.text_input("Escolha um Usuário", key="cad_user")
        nova_senha = st.text_input(
            "Escolha uma Senha", type="password", key="cad_pass"
        )
        nova_api_key = st.text_input(
            "Sua Gemini API Key", type="password", key="cad_key"
        )
        nova_sheet_url = st.text_input(
            "Link do Google Sheets", key="cad_url"
        )

        if st.button("Cadastrar e Salvar Dados", use_container_width=True):
          if not novo_user or not nova_senha:
            st.warning("Preencha ao menos usuário e senha.")
          else:
            sucesso, msg = cadastrar_usuario(
                novo_user, nova_senha, nova_api_key, nova_sheet_url
            )
            if sucesso:
              st.success(msg)
              st.info("Agora faça login na aba 'Login'.")
            else:
              st.error(msg)
    return False
  return True


if not gerenciar_autenticacao():
  st.stop()


# -----------------------------------------------------------------------------
# Suporte a Dados (Google Sheets e Upload Local)
# -----------------------------------------------------------------------------
def get_export_url(url: str) -> str:
  match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
  if match:
    sheet_id = match.group(1)
    return (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
    )
  return None


@st.cache_data(ttl=300)
def carregar_todas_abas(url: str):
  export_url = get_export_url(url)
  if not export_url:
    raise ValueError("Link do Google Sheets inválido.")
  return pd.read_excel(export_url, sheet_name=None, engine="openpyxl")


def preparar_contexto_completo(dict_dfs, aba_atual_nome, prompt_usuario):
  contexto_partes = []
  match_dia = re.search(r"\bdia\s*(\d{1,2})\b", prompt_usuario, re.IGNORECASE)

  for nome_aba, dataframe in dict_dfs.items():
    contexto_partes.append(
        f"\n--- ABA: {nome_aba} (Total de {len(dataframe)} linhas) ---"
    )
    df_filtrado_dia = pd.DataFrame()
    if match_dia:
      num_dia = match_dia.group(1).zfill(2)
      num_dia_int = int(match_dia.group(1))
      mascara = (
          dataframe.astype(str)
          .apply(
              lambda col: col.str.contains(
                  rf"\b{num_dia}\b|\b{num_dia_int}\b", regex=True, na=False
              )
          )
          .any(axis=1)
      )
      df_filtrado_dia = dataframe[mascara]

    if not df_filtrado_dia.empty:
      contexto_partes.append(
          f"REGISTROS ENCONTRADOS PARA O DIA {match_dia.group(1)} NESSA ABA"
          f" ({len(df_filtrado_dia)} registros):\n"
          + df_filtrado_dia.head(50).to_string()
      )
    else:
      contexto_partes.append(
          "AMOSTRA DE DADOS:\n" + dataframe.head(200).to_string()
      )

  return "\n".join(contexto_partes)


def gerar_pdf(
    df: pd.DataFrame, resumo_ia: str, titulo: str = "Relatório Executivo"
) -> bytes:
  pdf = FPDF()
  pdf.add_page()
  pdf.set_font("Helvetica", "B", 18)
  pdf.set_text_color(30, 41, 59)
  pdf.cell(0, 10, titulo, new_x="LMARGIN", new_y="NEXT", align="L")

  pdf.set_font("Helvetica", "", 10)
  pdf.set_text_color(100, 116, 139)
  pdf.cell(
      0,
      10,
      "Gerado por DataSight Analytics Pro",
      new_x="LMARGIN",
      new_y="NEXT",
      align="L",
  )
  pdf.ln(5)

  pdf.set_font("Helvetica", "B", 14)
  pdf.set_text_color(15, 23, 42)
  pdf.cell(0, 10, "1. Métricas Chave", new_x="LMARGIN", new_y="NEXT")

  pdf.set_font("Helvetica", "", 11)
  pdf.set_text_color(51, 65, 85)
  pdf.multi_cell(
      0,
      8,
      f"- Total de Registros Analisados: {len(df):,}\n- Total de Colunas:"
      f" {len(df.columns)}",
  )
  pdf.ln(5)

  if resumo_ia:
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(
        0, 10, "2. Diagnóstico Executivo de IA", new_x="LMARGIN", new_y="NEXT"
    )
    texto_limpo = resumo_ia.encode("latin-1", "replace").decode("latin-1")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(51, 65, 85)
    pdf.multi_cell(0, 6, texto_limpo)

  return pdf.output()


# -----------------------------------------------------------------------------
# Barra Lateral
# -----------------------------------------------------------------------------
with st.sidebar:
  st.title("⚡ DataSight Pro")
  st.write(f"👤 Conectado como: **{st.session_state.get('username')}**")

  if st.button("🚪 Sair / Logout", use_container_width=True):
    st.session_state.clear()
    st.rerun()

  st.divider()

  st.subheader("⚙️ Suas Credenciais")
  api_key = st.text_input(
      "Gemini API Key",
      value=st.session_state.get("api_key", ""),
      type="password",
  )
  sheet_url = st.text_input(
      "Google Sheets URL", value=st.session_state.get("sheet_url", "")
  )

  if st.button("💾 Salvar Credenciais", use_container_width=True):
    atualizar_configuracoes_usuario(
        st.session_state["username"], api_key, sheet_url
    )
    st.session_state["api_key"] = api_key
    st.session_state["sheet_url"] = sheet_url
    st.success("Salvo com sucesso!")

  st.divider()

  st.subheader("📁 Arquivo Local (.xlsx / .csv)")
  arquivo_local = st.file_uploader(
      "Ou envie uma planilha:", type=["xlsx", "csv"]
  )

  btn_carregar = st.button("🔄 Conectar Dados", use_container_width=True)

# -----------------------------------------------------------------------------
# Processamento dos Dados
# -----------------------------------------------------------------------------
if btn_carregar or ("dict_dfs" not in st.session_state):
  if arquivo_local:
    try:
      if arquivo_local.name.endswith(".csv"):
        st.session_state["dict_dfs"] = {"Dados": pd.read_csv(arquivo_local)}
      else:
        st.session_state["dict_dfs"] = pd.read_excel(
            arquivo_local, sheet_name=None
        )
      st.toast("Planilha local carregada!", icon="⚡")
    except Exception as e:
      st.error(f"Erro ao ler arquivo: {e}")
  elif sheet_url:
    try:
      with st.spinner("Baixando abas do Google Sheets..."):
        st.session_state["dict_dfs"] = carregar_todas_abas(sheet_url)
        st.toast("Google Sheets conectado!", icon="⚡")
    except Exception as e:
      st.error(f"Falha na conexão: {e}")

# -----------------------------------------------------------------------------
# Dashboard Principal
# -----------------------------------------------------------------------------
if "dict_dfs" in st.session_state:
  lista_abas = list(st.session_state["dict_dfs"].keys())
  aba_nome = st.sidebar.selectbox("📑 Aba Ativa:", lista_abas)
  df = st.session_state["dict_dfs"][aba_nome].copy()

  st.title(f"📊 Painel Executivo — Aba: {aba_nome}")

  kpi1, kpi2, kpi3 = st.columns(3)
  with kpi1:
    st.metric(label="Registros Exibidos", value=f"{len(df):,}")
  with kpi2:
    st.metric(label="Total de Atributos", value=len(df.columns))
  with kpi3:
    cols_num = df.select_dtypes(include=["number"]).columns
    if len(cols_num) > 0:
      st.metric(
          label=f"Soma ({cols_num[0]})", value=f"{df[cols_num[0]].sum():,.2f}"
      )
    else:
      st.metric(label="Status da Base", value="Ativo")

  st.divider()

  tab_copilot, tab_bi, tab_explorer, tab_export = st.tabs([
      "💬 Copilot IA (Chat)",
      "📈 Analytics & Gráficos",
      "🗃️ Data Explorer",
      "📄 Exportar PDF",
  ])

  # --- MÓDULO 1: CHAT ---
  with tab_copilot:
    st.caption("Converse interativamente com suas planilhas.")

    if "messages" not in st.session_state:
      st.session_state["messages"] = carregar_historico_chat(
          st.session_state["username"]
      )

    for msg in st.session_state["messages"]:
      with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

    if prompt_user := st.chat_input("Pergunte sobre qualquer dia, aba ou valor..."):
      if not api_key:
        st.error("Insira sua Gemini API Key na barra lateral.")
      else:
        st.session_state["messages"].append(
            {"role": "user", "content": prompt_user}
        )
        with st.chat_message("user"):
          st.markdown(prompt_user)

        with st.chat_message("assistant"):
          with st.spinner("Buscando dados em todas as abas..."):
            try:
              client = genai.Client(api_key=api_key)
              dados_contexto = preparar_contexto_completo(
                  st.session_state["dict_dfs"], aba_nome, prompt_user
              )

              contexto_prompt = f"""
Você é um analista executivo de dados sênior. Responda à pergunta do usuário analisando os dados abaixo.
Busque atentamente por datas ou dias específicos (como dia 05, dia 06) caso o usuário pergunte por eles.

DADOS DA PLANILHA:
{dados_contexto}

PERGUNTA DO USUÁRIO: {prompt_user}
"""
              res = client.models.generate_content(
                  model="gemini-3.6-flash", contents=contexto_prompt
              )
              st.markdown(res.text)

              st.session_state["messages"].append(
                  {"role": "assistant", "content": res.text}
              )
              st.session_state["ultimo_resumo_ia"] = res.text

              salvar_historico_chat(
                  st.session_state["username"], prompt_user, res.text
              )
            except Exception as e:
              st.error(f"Erro ao gerar resposta: {e}")

  # --- MÓDULO 2: GRÁFICOS ---
  with tab_bi:
    st.subheader(f"Geração de Gráficos (Aba: {aba_nome})")
    with st.form("form_chart"):
      prompt_chart = st.text_input("Descreva o gráfico desejado:")
      btn_chart = st.form_submit_button(
          "Gerar Gráfico", use_container_width=True
      )

    if btn_chart and prompt_chart:
      if not api_key:
        st.error("Insira sua API Key na barra lateral.")
      else:
        with st.spinner("Gerando visualização..."):
          try:
            client = genai.Client(api_key=api_key)
            prompt_code = f"""
Escreva APENAS código Python executável usando plotly.express (px) para criar o gráfico solicitado.
Armazene o objeto na variável 'fig'.
DataFrame 'df':
{df.head(100).to_string()}

Solicitação: {prompt_chart}
Retorne APENAS o bloco dentro de ```python ... ``` sem explicações.
"""
            res = client.models.generate_content(
                model="gemini-3.6-flash", contents=prompt_code
            )
            match = re.search(r"```python\s*(.*?)\s*```", res.text, re.DOTALL)
            if match:
              scope = {"df": df, "px": px}
              exec(match.group(1), globals(), scope)
              if "fig" in scope:
                st.plotly_chart(scope["fig"], use_container_width=True)
          except Exception as e:
            st.error(f"Erro ao gerar gráfico: {e}")

  # --- MÓDULO 3: EXPLORADOR DE DADOS ---
  with tab_explorer:
    st.subheader(f"Tabela de Dados — {aba_nome}")
    st.dataframe(df, use_container_width=True, height=450)

  # --- MÓDULO 4: EXPORTAÇÃO DE PDF ---
  with tab_export:
    st.subheader("📄 Exportar Relatório Executivo")
    resumo_pdf = st.text_area(
        "Diagnóstico / Resumo da IA",
        value=st.session_state.get("ultimo_resumo_ia", ""),
        height=150,
    )

    if st.button("🔨 Gerar PDF", use_container_width=True):
      try:
        pdf_bytes = gerar_pdf(
            df=df,
            resumo_ia=resumo_pdf,
            titulo=f"Relatório Executivo - {aba_nome}",
        )
        st.download_button(
            label="📥 Baixar PDF",
            data=bytes(pdf_bytes),
            file_name=f"Relatorio_{aba_nome}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
      except Exception as e:
        st.error(f"Erro ao gerar PDF: {e}")

else:
  st.info(
      "👈 Conecte-se ao Google Sheets ou faça upload de um arquivo local na"
      " barra lateral."
  )
