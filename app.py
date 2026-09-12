import base64
from io import BytesIO
import re
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

# Estilização CSS Customizada
st.markdown(
    """
    <style>
    .stApp {
        background-color: #fafafa;
    }
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 16px;
        background-color: #ffffff;
    }
    </style>
""",
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# Sistema de Autenticação / Login
# -----------------------------------------------------------------------------
def verificar_login():
  """Validação simples de credenciais de acesso."""
  if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

  if not st.session_state["logged_in"]:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
      st.subheader("🔐 Acesso Restrito | DataSight Enterprise")
      usuario = st.text_input("Usuário")
      senha = st.text_input("Senha", type="password")

      if st.button("Entrar", use_container_width=True):
        if usuario == "admin" and senha == "admin123":
          st.session_state["logged_in"] = True
          st.success("Login efetuado com sucesso!")
          st.rerun()
        else:
          st.error("Usuário ou senha incorretos.")
    return False
  return True


if not verificar_login():
  st.stop()


# -----------------------------------------------------------------------------
# Funções de Suporte (Carregamento de Múltiplas Abas e PDF)
# -----------------------------------------------------------------------------
def get_export_url(url: str) -> str:
  """Converte o link normal do Google Sheets no link de exportação XLSX completo."""
  match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
  if match:
    sheet_id = match.group(1)
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
  return None


@st.cache_data(ttl=300)
def carregar_todas_abas(url: str):
  """Baixa a planilha em formato Excel e lê todas as abas disponíveis."""
  export_url = get_export_url(url)
  if not export_url:
    raise ValueError("Link do Google Sheets inválido.")

  # Lê todas as abas e retorna um dicionário { "NomeDaAba": DataFrame }
  dict_dfs = pd.read_excel(export_url, sheet_name=None, engine="openpyxl")
  return dict_dfs


def gerar_pdf(
    df: pd.DataFrame, resumo_ia: str, titulo: str = "Relatório Executivo"
) -> bytes:
  """Gera um PDF formatado contendo resumo de IA e métricas gerais."""
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
      "Gerado automaticamente por DataSight Analytics Pro",
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
      f"- Total de Registros Analisados: {len(df):,}\n- Total de"
      f" Atributos/Colunas: {len(df.columns)}",
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
# Barra Lateral - Conexão, Seleção de Aba e Filtros
# -----------------------------------------------------------------------------
with st.sidebar:
  st.title("⚡ DataSight Pro")
  st.caption("Enterprise BI & AI Assistant")

  if st.button("🚪 Sair / Logout", use_container_width=True):
    st.session_state["logged_in"] = False
    st.rerun()

  st.divider()

  st.subheader("🔑 Autenticação AI")
  api_key = st.text_input(
      "Gemini API Key",
      type="password",
      help="Chave de API do Google AI Studio",
  )

  st.subheader("🔗 Fonte de Dados")
  sheet_url = st.text_input(
      "Google Sheets URL",
      placeholder="https://docs.google.com/spreadsheets/d/...",
  )

  col_btn1, col_btn2 = st.columns(2)
  with col_btn1:
    btn_carregar = st.button("🔄 Conectar", use_container_width=True)
  with col_btn2:
    if st.button("🧹 Limpar", use_container_width=True):
      st.session_state.clear()
      st.rerun()

  st.divider()

  # Seleção da Aba da Planilha
  if "dict_dfs" in st.session_state:
    st.subheader("📑 Selecionar Aba / Guia")
    lista_abas = list(st.session_state["dict_dfs"].keys())
    aba_selecionada = st.selectbox("Escolha a aba para análise:", lista_abas)
    st.session_state["aba_atual"] = aba_selecionada

    # Filtros Globais na Sidebar
    st.subheader("🎯 Filtros Globais")
    df_temp = st.session_state["dict_dfs"][aba_selecionada]

    cols_categ = df_temp.select_dtypes(include=["object"]).columns.tolist()

    filtros = {}
    if cols_categ:
      col_filtro = st.selectbox("Filtrar por coluna:", ["Nenhum"] + cols_categ)
      if col_filtro != "Nenhum":
        opcoes = df_temp[col_filtro].dropna().unique().tolist()
        selecionados = st.multiselect(f"Valores em {col_filtro}:", opcoes)
        if selecionados:
          filtros[col_filtro] = selecionados

    st.session_state["filtros"] = filtros

# -----------------------------------------------------------------------------
# Processamento de Dados
# -----------------------------------------------------------------------------
if btn_carregar:
  if sheet_url:
    try:
      with st.spinner("Carregando todas as abas da planilha..."):
        st.session_state["dict_dfs"] = carregar_todas_abas(sheet_url)
        st.session_state["messages"] = []
        st.session_state["ultimo_resumo_ia"] = ""
        st.toast("Todas as abas foram carregadas com sucesso!", icon="⚡")
    except Exception as e:
      st.error(f"Falha na conexão: {e}")
  else:
    st.warning("Insira o link da planilha.")

# Aplicação da Aba Escolhida e dos Filtros
if "dict_dfs" in st.session_state and "aba_atual" in st.session_state:
  aba_nome = st.session_state["aba_atual"]
  df = st.session_state["dict_dfs"][aba_nome].copy()

  if "filtros" in st.session_state and st.session_state["filtros"]:
    for col, vals in st.session_state["filtros"].items():
      df = df[df[col].isin(vals)]

  # ---------------------------------------------------------------------------
  # Cabeçalho e KPIs
  # ---------------------------------------------------------------------------
  st.title(f"📊 Painel Executivo — Aba: {aba_nome}")

  kpi1, kpi2, kpi3, kpi4 = st.columns(4)
  with kpi1:
    st.metric(label="Registros Exibidos", value=f"{len(df):,}")
  with kpi2:
    st.metric(label="Total de Atributos", value=len(df.columns))
  with kpi3:
    cols_num = df.select_dtypes(include=["number"]).columns
    if len(cols_num) > 0:
      soma_val = df[cols_num[0]].sum()
      st.metric(label=f"Total ({cols_num[0]})", value=f"{soma_val:,.2f}")
    else:
      st.metric(label="Volume de Dados", value="Ativo")
  with kpi4:
    st.metric(
        label="Status do Filtro",
        value=(
            "Ativo"
            if len(df) < len(st.session_state["dict_dfs"][aba_nome])
            else "Sem Filtro"
        ),
    )

  st.divider()

  # ---------------------------------------------------------------------------
  # Módulos Principais
  # ---------------------------------------------------------------------------
  tab_copilot, tab_bi, tab_explorer, tab_export = st.tabs([
      "💬 Copilot IA (Chat)",
      "📈 Analytics & Gráficos",
      "🗃️ Data Explorer",
      "📄 Exportar Relatórios PDF",
  ])

  # --- MÓDULO 1: CHAT INTERATIVO COM IA ---
  with tab_copilot:
    st.caption(
        f"Converse interativamente com a aba **{aba_nome}** em tempo real."
    )

    if "messages" not in st.session_state:
      st.session_state["messages"] = []

    for msg in st.session_state["messages"]:
      with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

    if prompt_user := st.chat_input(
        f"Faça uma pergunta sobre a aba {aba_nome}..."
    ):
      if not api_key:
        st.error("Insira sua Gemini API Key na barra lateral.")
      else:
        st.session_state["messages"].append(
            {"role": "user", "content": prompt_user}
        )
        with st.chat_message("user"):
          st.markdown(prompt_user)

        with st.chat_message("assistant"):
          with st.spinner("Analisando..."):
            try:
              client = genai.Client(api_key=api_key)
              contexto_prompt = f"""
Você é um analista executivo de dados. Responda à pergunta do usuário considerando os dados da aba '{aba_nome}':

AMOSTRA DA BASE (até 100 linhas):
{df.head(100).to_string()}

PERGUNTA: {prompt_user}
"""
              res = client.models.generate_content(
                  model="gemini-3.6-flash", contents=contexto_prompt
              )
              st.markdown(res.text)
              st.session_state["messages"].append(
                  {"role": "assistant", "content": res.text}
              )
              st.session_state["ultimo_resumo_ia"] = res.text
            except Exception as e:
              st.error(f"Erro ao gerar resposta: {e}")

  # --- MÓDULO 2: GERADOR DE GRÁFICOS ---
  with tab_bi:
    st.subheader(f"Geração de Visualizações (Aba: {aba_nome})")

    with st.form("form_chart"):
      prompt_chart = st.text_input(
          "Descreva o gráfico desejado:",
          placeholder="Ex: Monte um gráfico de rosca mostrando a distribuição de categorias.",
      )
      btn_chart = st.form_submit_button(
          "Construir Gráfico", use_container_width=True
      )

    if btn_chart:
      if not api_key:
        st.error("Insira sua API Key na barra lateral.")
      elif not prompt_chart:
        st.warning("Descreva o gráfico.")
      else:
        with st.spinner("Gerando código de visualização..."):
          try:
            client = genai.Client(api_key=api_key)
            prompt_code = f"""
Escreva APENAS código Python executável usando plotly.express (px) para criar o gráfico solicitado.
Armazene o objeto final do gráfico na variável 'fig'.
Base de dados disponível no DataFrame 'df' (relativo à aba {aba_nome}):
{df.head(30).to_string()}

Solicitação: {prompt_chart}
Retorne APENAS o bloco de código dentro de ```python ... ``` sem explicações.
"""
            res = client.models.generate_content(
                model="gemini-3.6-flash", contents=prompt_code
            )
            match = re.search(r"```python\s*(.*?)\s*```", res.text, re.DOTALL)

            if match:
              codigo = match.group(1)
              scope = {"df": df, "px": px}
              exec(codigo, globals(), scope)
              if "fig" in scope:
                st.plotly_chart(scope["fig"], use_container_width=True)
            else:
              st.write(res.text)
          except Exception as e:
            st.error(f"Erro ao construir gráfico: {e}")

  # --- MÓDULO 3: EXPLORADOR DE DADOS ---
  with tab_explorer:
    st.subheader(f"Visão Detalhada dos Dados — {aba_nome}")
    st.dataframe(df, use_container_width=True, height=450)

    col_down1, col_down2 = st.columns([1, 4])
    with col_down1:
      csv_data = df.to_csv(index=False).encode("utf-8")
      st.download_button(
          "📥 Exportar CSV da Aba",
          data=csv_data,
          file_name=f"relatorio_{aba_nome}.csv",
          mime="text/csv",
          use_container_width=True,
      )

  # --- MÓDULO 4: EXPORTAÇÃO DE RELATÓRIOS PDF ---
  with tab_export:
    st.subheader("📄 Geração de Relatório Executivo em PDF")
    st.write(
        "Gere um arquivo PDF formal contendo as métricas chave e o diagnóstico"
        " gerado pela IA."
    )

    titulo_relatorio = st.text_input(
        "Título do Relatório",
        value=f"Relatório Executivo - Aba {aba_nome}",
    )
    resumo_pdf = st.text_area(
        "Conteúdo / Diagnóstico para incluir no PDF",
        value=st.session_state.get("ultimo_resumo_ia", ""),
        height=150,
        help="A última resposta gerada no Chat de IA é importada automaticamente aqui.",
    )

    if st.button("🔨 Gerar Arquivo PDF", use_container_width=True):
      try:
        pdf_bytes = gerar_pdf(
            df=df, resumo_ia=resumo_pdf, titulo=titulo_relatorio
        )
        st.download_button(
            label="📥 Baixar Relatório em PDF",
            data=bytes(pdf_bytes),
            file_name=f"Relatorio_{aba_nome}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
        st.success("PDF gerado com sucesso!")
      except Exception as e:
        st.error(f"Erro ao criar PDF: {e}")

else:
  st.info(
      "👈 Conecte uma planilha do Google Sheets na barra lateral para iniciar."
  )
