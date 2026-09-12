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
# Configuração da Página e Estilização Visual Avançada
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
    /* Estilo Geral da Aplicação */
    .stApp {
        background-color: #f8fafc;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Cartões KPI Customizados */
    .kpi-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }
    .kpi-title {
        font-size: 0.8rem;
        color: #64748b;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .kpi-value {
        font-size: 1.8rem;
        color: #0f172a;
        font-weight: 700;
        margin-top: 4px;
    }
    .kpi-sub-pos {
        font-size: 0.8rem;
        color: #10b981;
        font-weight: 600;
        margin-top: 4px;
    }
    .kpi-sub-neg {
        font-size: 0.8rem;
        color: #ef4444;
        font-weight: 600;
        margin-top: 4px;
    }
    .kpi-sub-neu {
        font-size: 0.8rem;
        color: #64748b;
        font-weight: 500;
        margin-top: 4px;
    }

    /* Ajustes Finos de Botões e Tabs */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
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
# Banco de Dados
# -----------------------------------------------------------------------------
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
# Autenticação
# -----------------------------------------------------------------------------
def gerenciar_autenticacao():
  if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

  if not st.session_state["logged_in"]:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
      st.markdown(
          "<h1 style='text-align: center;'>⚡ DataSight Pro</h1>",
          unsafe_allow_html=True,
      )
      st.caption("Plataforma Executiva de Analytics & Inteligência de Dados")

      aba_login, aba_cadastro = st.tabs(["🔑 Login", "📝 Novo Cadastro"])

      with aba_login:
        usuario = st.text_input("Usuário", key="login_user")
        senha = st.text_input("Senha", type="password", key="login_pass")

        if st.button(
            "Entrar no Sistema", use_container_width=True, type="primary"
        ):
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
            st.error("Usuário ou senha incorretos.")

      with aba_cadastro:
        novo_user = st.text_input("Usuário", key="cad_user")
        nova_senha = st.text_input(
            "Senha", type="password", key="cad_pass"
        )
        nova_api_key = st.text_input(
            "Gemini API Key", type="password", key="cad_key"
        )
        nova_sheet_url = st.text_input(
            "Link Google Sheets", key="cad_url"
        )

        if st.button("Cadastrar Conta", use_container_width=True):
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
# Processamento de Dados
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
      "Gerado por DataSight Analytics Pro Enterprise",
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
      f"- Registros Analisados: {len(df):,}\n- Atributos Mapeados:"
      f" {len(df.columns)}",
  )
  pdf.ln(5)

  if resumo_ia:
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(
        0, 10, "2. Diagnóstico da Inteligência", new_x="LMARGIN", new_y="NEXT"
    )
    texto_limpo = resumo_ia.encode("latin-1", "replace").decode("latin-1")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(51, 65, 85)
    pdf.multi_cell(0, 6, texto_limpo)

  return pdf.output()


# -----------------------------------------------------------------------------
# Barra Lateral Estilizada
# -----------------------------------------------------------------------------
with st.sidebar:
  st.markdown("### ⚡ DataSight Pro")
  st.write(f"👤 **{st.session_state.get('username')}**")

  if st.button("🚪 Sair", use_container_width=True):
    st.session_state.clear()
    st.rerun()

  st.divider()

  with st.expander("⚙️ Configurações & Conexões", expanded=False):
    api_key = st.text_input(
        "Gemini API Key",
        value=st.session_state.get("api_key", ""),
        type="password",
    )
    sheet_url = st.text_input(
        "Google Sheets URL", value=st.session_state.get("sheet_url", "")
    )
    if st.button("Salvar Credenciais", use_container_width=True):
      atualizar_configuracoes_usuario(
          st.session_state["username"], api_key, sheet_url
      )
      st.session_state["api_key"] = api_key
      st.session_state["sheet_url"] = sheet_url
      st.success("Salvo com sucesso!")

  st.subheader("📁 Conectar Dados")
  arquivo_local = st.file_uploader("Upload de Planilha", type=["xlsx", "csv"])
  btn_carregar = st.button(
      "🔄 Sincronizar Fonte de Dados",
      use_container_width=True,
      type="primary",
  )

# -----------------------------------------------------------------------------
# Carregamento de Dados
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
      with st.spinner("Conectando ao Google Sheets..."):
        st.session_state["dict_dfs"] = carregar_todas_abas(sheet_url)
        st.toast("Google Sheets sincronizado!", icon="⚡")
    except Exception as e:
      st.error(f"Erro na conexão: {e}")

# -----------------------------------------------------------------------------
# Painel Principal
# -----------------------------------------------------------------------------
if "dict_dfs" in st.session_state:
  lista_abas = list(st.session_state["dict_dfs"].keys())

  c_title, c_aba = st.columns([3, 1])
  with c_aba:
    aba_nome = st.selectbox("📑 Aba do Excel:", lista_abas)

  df_original = st.session_state["dict_dfs"][aba_nome].copy()

  # --- NOVO: FILTROS AVANÇADOS (CATEGÓRICOS + TEMPORAIS) ---
  with st.expander("🔍 Filtros Globais Avançados (Data e Categorias)", expanded=True):
    f_col1, f_col2 = st.columns(2)
    
    df_filtrado = df_original.copy()
    
    # Detecção automática de colunas de data
    cols_data = []
    for c in df_original.columns:
      if pd.api.types.is_datetime64_any_dtype(df_original[c]):
        cols_data.append(c)
      else:
        # Tenta converter para datetime para testar
        try:
          parsed = pd.to_datetime(df_original[c], errors="coerce")
          if parsed.notna().sum() > len(df_original) * 0.5:
            df_original[c] = parsed
            cols_data.append(c)
        except Exception:
          pass

    with f_col1:
      if cols_data:
        col_data_sel = st.selectbox("📅 Coluna Temporal Detectada:", cols_data)
        min_date = df_original[col_data_sel].min()
        max_date = df_original[col_data_sel].max()
        
        if pd.notna(min_date) and pd.notna(max_date):
          intervalo_data = st.date_input(
              "Intervalo de Datas:",
              value=(min_date.date(), max_date.date()),
              min_value=min_date.date(),
              max_value=max_date.date()
          )
          if len(intervalo_data) == 2:
            data_ini, data_fim = intervalo_data
            mask_data = (df_original[col_data_sel].dt.date >= data_ini) & (df_original[col_data_sel].dt.date <= data_fim)
            df_filtrado = df_filtrado[mask_data]
      else:
        st.info("Nenhuma coluna do tipo Data/Datetime identificada automaticamente.")

    with f_col2:
      col_filtro = st.selectbox(
          "Categorias / Coluna de Atributo:",
          ["(Nenhum)"] + list(df_original.columns),
      )
      if col_filtro != "(Nenhum)":
        valores_unicos = df_original[col_filtro].dropna().unique().tolist()
        val_selecionados = st.multiselect(
            f"Valores de '{col_filtro}':", valores_unicos
        )
        if val_selecionados:
          df_filtrado = df_filtrado[df_filtrado[col_filtro].isin(val_selecionados)]

  df = df_filtrado

  with c_title:
    st.title(f"📊 Dashboard Executivo — {aba_nome}")

  # --- NOVOS KPIs COM VARIAÇÃO (DELTA) AUTOMÁTICA ---
  k1, k2, k3, k4 = st.columns(4)
  cols_num = df.select_dtypes(include=["number"]).columns

  # Cálculo de variação da métrica principal (1ª metade x 2ª metade do conjunto)
  delta_text = "Em relação ao período"
  delta_class = "kpi-sub-neu"
  soma_val = "N/A"
  media_val = "N/A"
  nome_col = cols_num[0] if len(cols_num) > 0 else "Métrica"

  if len(cols_num) > 0:
    val_total = df[cols_num[0]].sum()
    soma_val = f"{val_total:,.2f}"
    media_val = f"{df[cols_num[0]].mean():,.2f}"

    # Dividir em duas metades para calcular variação percentual
    metade = len(df) // 2
    if metade > 0:
      val_ant = df[cols_num[0]].iloc[:metade].sum()
      val_rec = df[cols_num[0]].iloc[metade:].sum()
      if val_ant > 0:
        var_pct = ((val_rec - val_ant) / val_ant) * 100
        if var_pct > 0:
          delta_text = f"↑ +{var_pct:.1f}% vs período anterior"
          delta_class = "kpi-sub-pos"
        elif var_pct < 0:
          delta_text = f"↓ {var_pct:.1f}% vs período anterior"
          delta_class = "kpi-sub-neg"
        else:
          delta_text = "→ 0.0% sem variação"

  with k1:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-title">Linhas Filtradas</div>
            <div class="kpi-value">{len(df):,}</div>
            <div class="kpi-sub-neu">Base total: {len(df_original):,}</div>
        </div>
    """,
        unsafe_allow_html=True,
    )

  with k2:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-title">Atributos</div>
            <div class="kpi-value">{len(df.columns)}</div>
            <div class="kpi-sub-neu">Colunas disponíveis</div>
        </div>
    """,
        unsafe_allow_html=True,
    )

  with k3:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-title">Soma ({nome_col})</div>
            <div class="kpi-value">{soma_val}</div>
            <div class="{delta_class}">{delta_text}</div>
        </div>
    """,
        unsafe_allow_html=True,
    )

  with k4:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-title">Média ({nome_col})</div>
            <div class="kpi-value">{media_val}</div>
            <div class="kpi-sub-neu">Média por item</div>
        </div>
    """,
        unsafe_allow_html=True,
    )

  st.divider()

  # --- ABAS DE NAVEGAÇÃO ---
  tab_copilot, tab_bi, tab_geo, tab_explorer, tab_export = st.tabs([
      "💬 Copilot IA (Chat)",
      "📈 Analytics & Visualizações",
      "🗺️ Análise Geográfica / Locais",
      "🗃️ Explorador de Dados",
      "📄 Relatório Executivo PDF",
  ])

  # --- MÓDULO 1: COPILOT IA ---
  with tab_copilot:
    st.caption("Converse em tempo real sobre os seus dados.")

    if "messages" not in st.session_state:
      st.session_state["messages"] = carregar_historico_chat(
          st.session_state["username"]
      )

    for msg in st.session_state["messages"]:
      with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

    if prompt_user := st.chat_input("Pergunte sobre qualquer dado ou aba..."):
      if not api_key:
        st.error("Insira sua Gemini API Key no menu lateral.")
      else:
        st.session_state["messages"].append(
            {"role": "user", "content": prompt_user}
        )
        with st.chat_message("user"):
          st.markdown(prompt_user)

        with st.chat_message("assistant"):
          with st.spinner("Analisando com IA..."):
            try:
              client = genai.Client(api_key=api_key)
              dados_contexto = preparar_contexto_completo(
                  st.session_state["dict_dfs"], aba_nome, prompt_user
              )

              contexto_prompt = f"""
Você é um analista executivo de dados sênior. Responda à pergunta do usuário analisando os dados abaixo.
DADOS DA PLANILHA:
{dados_contexto}

PERGUNTA: {prompt_user}
"""
              res = client.models.generate_content(
                  model="gemini-2.5-flash", contents=contexto_prompt
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
              st.error(f"Erro ao consultar IA: {e}")

  # --- MÓDULO 2: ANALYTICS & GRÁFICOS ---
  with tab_bi:
    st.subheader(f"Geração de Gráficos Inteligentes — {aba_nome}")

    c_g1, c_g2 = st.columns([1, 2])
    with c_g1:
      with st.form("form_chart"):
        prompt_chart = st.text_area(
            "Descreva o gráfico desejado:",
            placeholder="Ex: Crie um gráfico de linhas mostrando a evolução de vendas no tempo",
        )
        btn_chart = st.form_submit_button(
            "Gerar Visualização", use_container_width=True, type="primary"
        )

    with c_g2:
      if btn_chart and prompt_chart:
        if not api_key:
          st.error("Insira sua API Key na barra lateral.")
        else:
          with st.spinner("Desenhando gráfico..."):
            try:
              client = genai.Client(api_key=api_key)
              prompt_code = f"""
Escreva APENAS código Python executável usando plotly.express (px) para criar o gráfico solicitado.
Armazene o objeto na variável 'fig'.
Use o tema 'plotly_white' para um visual limpo e profissional.
DataFrame 'df':
{df.head(100).to_string()}

Solicitação: {prompt_chart}
Retorne APENAS o bloco dentro de ```python ... ``` sem explicações.
"""
              res = client.models.generate_content(
                  model="gemini-2.5-flash", contents=prompt_code
              )
              match = re.search(r"```python\s*(.*?)\s*```", res.text, re.DOTALL)
              if match:
                scope = {"df": df, "px": px}
                exec(match.group(1), globals(), scope)
                if "fig" in scope:
                  scope["fig"].update_layout(template="plotly_white")
                  st.plotly_chart(scope["fig"], use_container_width=True)
            except Exception as e:
              st.error(f"Erro ao gerar gráfico: {e}")

  # --- MÓDULO 3: NOVO - ANÁLISE GEOGRÁFICA ---
  with tab_geo:
    st.subheader("🗺️ Análise de Distribuição por Localidade")
    cols_geo = [c for c in df.columns if any(p in c.lower() for p in ["estado", "uf", "cidade", "pais", "regiao", "local"])]
    
    if cols_geo and len(cols_num) > 0:
      col_geo_sel = st.selectbox("Selecione a Coluna de Localidade:", cols_geo)
      col_val_sel = st.selectbox("Selecione o Valor Métrica:", cols_num)
      
      df_geo = df.groupby(col_geo_sel)[col_val_sel].sum().reset_index().sort_values(by=col_val_sel, ascending=False)
      fig_geo = px.bar(
          df_geo, 
          x=col_geo_sel, 
          y=col_val_sel, 
          color=col_val_sel,
          title=f"Distribuição de {col_val_sel} por {col_geo_sel}",
          template="plotly_white",
          color_continuous_scale="Blues"
      )
      st.plotly_chart(fig_geo, use_container_width=True)
    else:
      st.info("Para ativar este mapa/visão, certifique-se de ter colunas de local (ex: Estado, Cidade, UF) e métricas numéricas na sua planilha.")

  # --- MÓDULO 4: EXPLORADOR DE DADOS ---
  with tab_explorer:
    st.subheader(f"Tabela de Dados — {aba_nome}")
    st.dataframe(df, use_container_width=True, height=450)

  # --- MÓDULO 5: EXPORTAÇÃO PDF ---
  with tab_export:
    st.subheader("📄 Gerador de Relatório Executivo")
    resumo_pdf = st.text_area(
        "Diagnóstico / Notas do Relatório",
        value=st.session_state.get("ultimo_resumo_ia", ""),
        height=150,
    )

    if st.button("🔨 Gerar PDF Profissional", use_container_width=True):
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
  st.info("👈 Conecte uma planilha na barra lateral para iniciar.")
