import pandas as pd
import re
import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="Gerenciador de Planilhas com IA", layout="wide")

st.title("📊 Gerenciador de Planilhas Google com IA")

# Configurações na barra lateral
st.sidebar.header("Configurações")
api_key = st.sidebar.text_input("Cole sua Gemini API Key", type="password")

st.markdown("### 1. Conectar Google Planilhas")
sheet_url = st.text_input(
    "Cole o link público da sua planilha do Google Sheets:"
)


# Função para extrair a chave da planilha e transformar em link CSV público
def get_csv_url(url):
  # Extrai o ID da planilha do link
  match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
  if match:
    sheet_id = match.group(1)
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
  return None


if sheet_url:
  try:
    csv_url = get_csv_url(sheet_url)

    if csv_url:
      # Lê a planilha diretamente da nuvem
      df = pd.read_csv(csv_url)

      st.success("Planilha carregada com sucesso!")

      # Exibe os dados
      with st.expander("Ver dados da planilha", expanded=True):
        st.dataframe(df)

      # Área de perguntas para a IA
      st.markdown("### 2. Pergunte para a IA")
      query = st.text_input(
          "O que deseja analisar ou consultar nesta planilha?"
      )

      if query:
        if not api_key:
          st.error("Por favor, insira sua API Key do Gemini na barra lateral.")
        else:
          genai.configure(api_key=api_key)
          model = genai.GenerativeModel("gemini-1.5-flash")

          with st.spinner("Analisando dados..."):
            prompt = (
                "Você é um assistente especialista em análise de dados. Com"
                f" base nos dados da planilha a seguir:\n\n{df.to_string()}\n\nResponda"
                f" à seguinte solicitação: {query}"
            )

            response = model.generate_content(prompt)

            st.markdown("---")
            st.markdown("### 🤖 Resposta da IA:")
            st.write(response.text)
    else:
      st.error(
          "Link inválido. Verifique se o link informado é do Google Planilhas."
      )

  except Exception as e:
    st.error(
        "Erro ao carregar a planilha. Certifique-se de que o acesso da planilha"
        " está configurado como 'Qualquer pessoa com o link'."
    )
