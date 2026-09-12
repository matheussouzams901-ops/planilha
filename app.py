import re
import pandas as pd
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
        # Salva o DataFrame na sessão do Streamlit
        st.session_state["df"] = pd.read_csv(csv_url)
        st.success("Planilha carregada com sucesso!")
      else:
        st.error("Link inválido do Google Sheets.")
    except Exception as e:
      st.error(
          "Erro ao carregar a planilha. Verifique se a permissão está como"
          " 'Qualquer pessoa com o link'."
      )
  else:
    st.warning("Por favor, cole o link da planilha.")

# Se a planilha já estiver salva na memória, exibe e permite perguntas
if "df" in st.session_state:
  df = st.session_state["df"]

  with st.expander("Ver dados da planilha", expanded=False):
    st.dataframe(df)

  st.markdown("---")
  st.markdown("### 2. Pergunte para a IA")

  # Formulário para evitar que a página recarrega antes de terminar de digitar
  with st.form("form_pergunta"):
    query = st.text_input("O que deseja analisar ou consultar nesta planilha?")
    submitted = st.form_submit_button("Enviar Pergunta")

    if submitted:
      if not query:
        st.warning("Digite uma pergunta.")
      elif not api_key:
        st.error("Por favor, insira sua API Key do Gemini na barra lateral.")
      else:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        with st.spinner("Analisando dados..."):
          try:
            prompt = (
                "Você é um assistente especialista em análise de dados. Com"
                f" base nos dados a seguir:\n\n{df.to_string()}\n\nResponda:"
                f" {query}"
            )
            response = model.generate_content(prompt)

            st.markdown("### 🤖 Resposta da IA:")
            st.write(response.text)
          except Exception as e:
            st.error(f"Erro ao processar a pergunta: {e}")
