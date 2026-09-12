import pandas as pd
import streamlit as st
import google.generativeai as genai

st.title("Gerenciador de Planilhas com IA")

# Configurar chave da API
api_key = st.sidebar.text_input("Cole sua Gemini API Key", type="password")

uploaded_file = st.file_uploader(
    "Envie sua planilha (CSV ou Excel)", type=["csv", "xlsx"]
)

if uploaded_file and api_key:
  genai.configure(api_key=api_key)
  model = genai.GenerativeModel("gemini-1.5-flash")

  # Carregar dados
  df = (
      pd.read_csv(uploaded_file)
      if uploaded_file.name.endswith(".csv")
      else pd.read_excel(uploaded_file)
  )
  st.dataframe(df.head())

  # Pergunta para a IA
  query = st.text_input("O que deseja analisar ou consultar nesta planilha?")

  if query:
    prompt = (
        f"Com base nos dados a seguir:\n{df.to_string()}\n\nResponda à seguinte"
        f" solicitação: {query}"
    )
    response = model.generate_content(prompt)
    st.write("### Resposta da IA:")
    st.write(response.text)