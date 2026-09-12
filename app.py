import re
from google import genai
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Gerenciador de Planilhas com IA", layout="wide")

st.title("📊 Gerenciador de Planilhas Google com IA")

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
  st.markdown("### 2. Pergunte para a IA")

  with st.form("form_pergunta"):
    query = st.text_input("O que deseja analisar ou consultar nesta planilha?")
    submitted = st.form_submit_button("Enviar Pergunta")

    if submitted:
      if not query:
        st.warning("Digite uma pergunta.")
      elif not api_key:
        st.error("Por favor, insira sua API Key do Gemini na barra lateral.")
      else:
        with st.spinner("Analisando dados..."):
          try:
            client = genai.Client(api_key=api_key)

            prompt = (
                "Você é um especialista em análise de dados. Com base nos"
                f" dados a seguir:\n\n{df.to_string()}\n\nResponda: {query}"
            )

            # Atualizado para o modelo gemini-3.6-flash
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
            )

            st.markdown("### 🤖 Resposta da IA:")
            st.write(response.text)
          except Exception as e:
            st.error(f"Erro ao processar a pergunta: {e}")
