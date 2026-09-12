import re
from google import genai
import pandas as pd
import plotly.express as px
import streamlit as st

# -----------------------------------------------------------------------------
# Configuração da Página
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="DataSight AI | BI & Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilização CSS Customizada (Visual Clean & Profissional)
st.markdown(
    """
    <style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .stMetric {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    div[data-testid="stSidebarHeader"] {
        padding-top: 1rem;
    }
    </style>
""",
    unsafe_allow_allow_html=True,
)


# -----------------------------------------------------------------------------
# Funções Auxiliares
# -----------------------------------------------------------------------------
def get_csv_url(url: str) -> str:
  """Extrai o ID do Google Sheets e retorna a URL de exportação em CSV."""
  match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
  if match:
    sheet_id = match.group(1)
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv"
  return None


def carregar_dados(url: str) -> pd.DataFrame:
  """Carrega os dados do CSV público do Google Sheets."""
  csv_url = get_csv_url(url)
  if not csv_url:
    raise ValueError(
        "Link do Google Sheets inválido. Certifique-se de que é um link válido."
    )
  df = pd.read_csv(csv_url)
  return df


# -----------------------------------------------------------------------------
# Barra Lateral (Configurações)
# -----------------------------------------------------------------------------
with st.sidebar:
  st.title("⚙️ Configurações")
  api_key = st.text_input(
      "Gemini API Key",
      type="password",
      help="Obtenha sua chave gratuita em aistudio.google.com",
  )

  st.divider()
  st.subheader("🔗 Conexão de Dados")
  sheet_url = st.text_input(
      "Link do Google Sheets",
      placeholder="https://docs.google.com/spreadsheets/d/...",
  )

  btn_carregar = st.button("🔄 Conectar / Atualizar Dados", use_container_width=True)

  st.divider()
  st.caption("🤖 Powered by Gemini 3.8 Flash & Streamlit")

# -----------------------------------------------------------------------------
# Lógica Principal do App
# -----------------------------------------------------------------------------
if btn_carregar:
  if sheet_url:
    try:
      with st.spinner("Conectando ao Google Sheets..."):
        st.session_state["df"] = carregar_dados(sheet_url)
        st.toast("Dados atualizados com sucesso!", icon="✅")
    except Exception as e:
      st.error(f"Erro ao carregar planilha: {e}")
  else:
    st.warning("Insira o link da planilha na barra lateral.")

# Verificação de estado dos dados
if "df" in st.session_state:
  df = st.session_state["df"]

  # Cabeçalho Principal
  st.title("📊 Painel de Análise de Dados")
  st.caption("Visualize métricas, consulte informações e gere gráficos com Inteligência Artificial.")

  # ---------------------------------------------------------------------------
  # Destaques / KPIs Automáticos
  # ---------------------------------------------------------------------------
  col1, col2, col3, col4 = st.columns(4)
  with col1:
    st.metric(label="Total de Linhas", value=f"{len(df):,}")
  with col2:
    st.metric(label="Total de Colunas", value=len(df.columns))
  with col3:
    # Tenta identificar colunas numéricas para exibir soma/média
    cols_num = df.select_dtypes(include=["number"]).columns
    if len(cols_num) > 0:
      val = df[cols_num[0]].sum()
      st.metric(
          label=f"Soma ({cols_num[0]})",
          value=f"{val:,.2f}" if isinstance(val, (int, float)) else str(val),
      )
    else:
      st.metric(label="Campos Numéricos", value="0")
  with col4:
    st.metric(
        label="Memória Utilizada", value=f"{df.memory_usage().sum() / 1024:.1f} KB"
    )

  st.divider()

  # ---------------------------------------------------------------------------
  # Abas de Funcionalidades
  # ---------------------------------------------------------------------------
  tab_ia, tab_graficos, tab_dados = st.tabs([
      "🤖 Copiloto de IA",
      "📈 Gerador de Gráficos",
      "📋 Visualizar Planilha",
  ])

  # --- ABA 1: Copiloto de IA ---
  with tab_ia:
    st.subheader("Faça perguntas sobre seus dados")
    st.write(
        "A IA irá analisar toda a estrutura da planilha para responder suas"
        " dúvidas."
    )

    with st.form("form_ia"):
      pergunta = st.text_input(
          "O que você deseja saber?",
          placeholder="Ex: Qual cliente teve o maior faturamento? Qual a média de atendimento?",
      )
      btn_enviar_ia = st.form_submit_button(
          "Analisar Dados", use_container_width=True
      )

    if btn_enviar_ia:
      if not api_key:
        st.error("Por favor, insira sua Gemini API Key na barra lateral.")
      elif not pergunta:
        st.warning("Digite uma pergunta.")
      else:
        with st.spinner("O Gemini está analisando sua solicitação..."):
          try:
            client = genai.Client(api_key=api_key)

            prompt = f"""
Você é um consultor sênior em Business Intelligence e Análise de Dados.
Analise a seguinte estrutura e amostra de dados:

AMOSTRA DOS DADOS (Primeiras 100 linhas):
{df.head(100).to_string()}

SOLICITAÇÃO DO USUÁRIO:
{pergunta}

INSTRUÇÕES DE RESPOSTA:
1. Seja direto, claro e profissional.
2. Apresente números formatados e legíveis.
3. Se fizer sentido, estruture a resposta usando marcadores (bullet points) ou tabelas em Markdown.
"""
            response = client.models.generate_content(
                model="gemini-3.8-flash", contents=prompt
            )

            st.markdown("### 💡 Diagnóstico da IA")
            st.info(response.text)
          except Exception as e:
            st.error(f"Erro ao processar consulta: {e}")

  # --- ABA 2: Gerador de Gráficos ---
  with tab_graficos:
    st.subheader("Geração Automática de Gráficos")
    st.write("Descreva o gráfico que você precisa e a IA irá construí-lo.")

    with st.form("form_grafico"):
      pedi_grafico = st.text_input(
          "Como deseja visualizar os dados?",
          placeholder="Ex: Crie um gráfico de barras mostrando a produção por tipo de serviço.",
      )
      btn_enviar_grafico = st.form_submit_button(
          "Gerar Gráfico Interativo", use_container_width=True
      )

    if btn_enviar_grafico:
      if not api_key:
        st.error("Por favor, insira sua Gemini API Key na barra lateral.")
      elif not pedi_grafico:
        st.warning("Descreva o gráfico desejado.")
      else:
        with st.spinner("Construindo visualização..."):
          try:
            client = genai.Client(api_key=api_key)

            prompt = f"""
Você é um desenvolvedor Python especialista em Plotly Express.
Com base nesta estrutura de dados:
{df.head(50).to_string()}

A solicitação de gráfico é: {pedi_grafico}

REGRAS RÍGIDAS:
1. Escreva APENAS código Python executável usando `plotly.express` (como `px`).
2. Atribua o gráfico final à variável `fig`.
3. Use estilos visuais limpos e profissionais (`template='plotly_white'`).
4. Retorne APENAS o bloco de código envolvido por ```python ... ``` sem explicações adicionais.
"""
            response = client.models.generate_content(
                model="gemini-3.8-flash", contents=prompt
            )

            # Extrai o código Python da resposta
            match = re.search(
                r"```python\s*(.*?)\s*```", response.text, re.DOTALL
            )
            if match:
              codigo = match.group(1)
              scope_local = {"df": df, "px": px}
              exec(codigo, globals(), scope_local)

              if "fig" in scope_local:
                st.plotly_chart(scope_local["fig"], use_container_width=True)
              else:
                st.error("Não foi possível gerar a variável do gráfico.")
            else:
              st.warning("Resposta da IA:")
              st.write(response.text)

          except Exception as e:
            st.error(f"Erro ao gerar gráfico: {e}")

  # --- ABA 3: Tabela de Dados ---
  with tab_dados:
    st.subheader("Explorador de Dados")

    # Filtro rápido de busca na tabela
    termo_busca = st.text_input(
        "🔎 Pesquisar termo na tabela:", placeholder="Digite para filtrar..."
    )

    df_display = df.copy()
    if termo_busca:
      mask = df_display.astype(str).apply(
          lambda x: x.str.contains(termo_busca, case=False, na=False)
      ).any(axis=1)
      df_display = df_display[mask]

    st.dataframe(df_display, use_container_width=True, height=450)

    # Botão de download dos dados filtrados
    csv = df_display.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Baixar Dados Exibidos em CSV",
        data=csv,
        file_name="dados_filtrados.csv",
        mime="text/csv",
    )

else:
  # Tela Inicial de Boas-Vindas (Quando nenhum dado foi carregado)
  st.info("👈 Para começar, conecte sua planilha do Google Sheets na barra lateral.")

  st.markdown("""
    ### 🚀 Como utilizar o Dashboard:
    1. **Abra sua planilha do Google Sheets** e certifique-se de que o acesso está como *"Qualquer pessoa com o link"*.
    2. **Copie o link** e cole no campo de conexão na barra lateral.
    3. Informe sua **Gemini API Key**.
    4. Clique em **Conectar / Atualizar Dados** para liberar todas as análises e gráficos!
    """)
