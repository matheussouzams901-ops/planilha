import re
from google import genai
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Gerenciador com IA e Gráficos", layout="wide")

st.title("📊 Gerenciador de Planilhas com IA e Gráficos")

# Configurações na barra lateral
st.sidebar.header("Configurações")
api_key = st.sidebar.text_input("Cole sua Gemini API Key", type="password")

st.markdown("### 1. Conectar Google Planilhas")
sheet_url = st.text_input(
    "Cole o link público da sua planilha do Google Sheets:"
)


def get_csv_url(url):
  match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
  if match:
    sheet_id = match.group(1)
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv"
  return None


# Botão para carregar os dados
if st.button("Carregar / Atualizar Planilha"):
  if sheet_url:
    try:
      csv_url = get_csv_url(sheet_url)
      if csv_url:
        st.session_state["df"] = pd.read_csv(csv_url)
        st.success("Planilha carregada com sucesso!")
      else:
        st.error("Link inválido do Google Sheets.")
    except Exception as e:
      st.error(f"Erro ao carregar a planilha: {e}")
  else:
    st.warning("Por favor, cole o link da planilha.")

# Se a planilha estiver na memória
if "df" in st.session_state:
  df = st.session_state["df"]

  with st.expander("Ver dados da planilha", expanded=False):
    st.dataframe(df)

  st.markdown("---")
  st.markdown("### 2. Pergunte ou peça um gráfico para a IA")

  with st.form("form_pergunta"):
    tipo_resposta = st.radio(
        "O que deseja gerar?", ["Texto / Análise", "Gráfico Interativo"]
    )
    query = st.text_input(
        "Exemplo: 'Mostre um gráfico de barras da produção por cliente' ou 'Qual"
        " o total de serviços?'"
    )
    submitted = st.form_submit_button("Gerar")

    if submitted:
      if not query:
        st.warning("Digite uma solicitação.")
      elif not api_key:
        st.error("Por favor, insira sua API Key do Gemini na barra lateral.")
      else:
        with st.spinner("Processando..."):
          try:
            client = genai.Client(api_key=api_key)

            if tipo_resposta == "Gráfico Interativo":
              prompt = f"""
Você é um programador especialista em Python e Plotly.
Com base nestes dados da planilha:
{df.head(100).to_string()}

A solicitação do usuário é: {query}

Escreva APENAS o código Python necessário usando 'plotly.express' (como px) para criar o gráfico desejado.
Armazene o objeto da figura na variável 'fig'.
NÃO adicione explicações, NÃO inclua 'fig.show()', retorne APENAS o bloco de código Python dentro de marcadores ```python.
"""
              response = client.models.generate_content(
                  model="gemini-3.6-flash", contents=prompt
              )

              # Extrai o código Python da resposta da IA
              code_match = re.search(
                  r"```python\s*(.*?)\s*```", response.text, re.DOTALL
              )
              if code_match:
                code = code_match.group(1)
                # Executa o código gerado no contexto local onde 'df' e 'px' estão disponíveis
                local_vars = {"df": df, "px": px}
                exec(code, globals(), local_vars)

                if "fig" in local_vars:
                  st.plotly_chart(local_vars["fig"], use_container_width=True)
                else:
                  st.error("A IA não gerou a variável 'fig' esperada.")
              else:
                st.write(response.text)

            else:
              prompt = f"Com base nos dados a seguir:\n\n{df.to_string()}\n\nResponda: {query}"
              response = client.models.generate_content(
                  model="gemini-3.6-flash", contents=prompt
              )
              st.markdown("### 🤖 Resposta da IA:")
              st.write(response.text)

          except Exception as e:
            st.error(f"Erro ao processar: {e}")
