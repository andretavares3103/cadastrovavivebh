import streamlit as st
import pandas as pd
import re
import os
import uuid
from datetime import datetime
from io import BytesIO

# --- Google Sheets/Drive ---
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# =============== CONFIGURAR GOOGLE API ===============
st.sidebar.header("🔒 Configuração Google API")
st.sidebar.write("Suba o arquivo de credenciais (JSON) do Google Service Account.")

google_creds_file = st.sidebar.file_uploader("Upload credenciais Google", type="json")
sheet_url = st.sidebar.text_input("URL da Google Sheet (com permissão de edição)", value="https://docs.google.com/spreadsheets/d/...")
folder_id = st.sidebar.text_input("ID da pasta Google Drive para arquivos", value="SUA_FOLDER_ID_AQUI")

if google_creds_file:
    creds = Credentials.from_service_account_info(
        pd.read_json(google_creds_file).to_dict(),
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    gc = gspread.authorize(creds)
    service_drive = build('drive', 'v3', credentials=creds)
    SHEET_OK = True
else:
    creds = gc = service_drive = None
    SHEET_OK = False

# =============== MÁSCARA E VALIDAÇÃO CPF/CELULAR ===============
def formatar_cpf(valor):
    valor = re.sub(r'\D', '', valor)
    if len(valor) == 11:
        return "%s.%s.%s-%s" % (valor[:3], valor[3:6], valor[6:9], valor[9:])
    return valor

def formatar_celular(valor):
    valor = re.sub(r'\D', '', valor)
    if len(valor) == 11:
        return "(%s) %s-%s" % (valor[:2], valor[2:7], valor[7:])
    elif len(valor) == 10:
        return "(%s) %s-%s" % (valor[:2], valor[2:6], valor[6:])
    return valor

def validar_cpf(cpf):
    cpf = re.sub(r'\D', '', cpf)
    return len(cpf) == 11

def validar_celular(cel):
    cel = re.sub(r'\D', '', cel)
    return len(cel) in [10, 11]

# =============== CARREGAR DADOS EXISTENTES ===============
def carregar_registros(sheet_url, local_file="cadastros.csv"):
    if SHEET_OK and sheet_url.startswith("https://docs.google.com/spreadsheets"):
        sh = gc.open_by_url(sheet_url)
        worksheet = sh.sheet1
        df = pd.DataFrame(worksheet.get_all_records())
    elif os.path.exists(local_file):
        df = pd.read_csv(local_file)
    else:
        df = pd.DataFrame()
    return df

# =============== SALVAR DADOS ===============
def salvar_dados(dados, sheet_url, local_file="cadastros.csv"):
    # Google Sheets
    if SHEET_OK and sheet_url.startswith("https://docs.google.com/spreadsheets"):
        sh = gc.open_by_url(sheet_url)
        worksheet = sh.sheet1
        worksheet.append_row(dados)
    # Local CSV (fallback ou alternativa)
    if os.path.exists(local_file):
        df = pd.read_csv(local_file)
        df.loc[len(df)] = dados
    else:
        df = pd.DataFrame([dados])
    df.to_csv(local_file, index=False)

# =============== SALVAR ARQUIVO GOOGLE DRIVE ===============
def salvar_arquivo_drive(file, folder_id):
    if SHEET_OK and folder_id and file is not None:
        file_metadata = {
            'name': f"{uuid.uuid4()}_{file.name}",
            'parents': [folder_id]
        }
        media = MediaIoBaseUpload(BytesIO(file.read()), mimetype=file.type)
        uploaded_file = service_drive.files().create(body=file_metadata, media_body=media, fields='id,webViewLink').execute()
        return uploaded_file.get('webViewLink')
    return None

# =============== LAYOUT FORMULÁRIO ===============
st.title("Cadastro de Profissional (Simulação Completa)")

with st.form("cadastro_prof"):
    st.markdown("#### **Informações Pessoais**")
    nome = st.text_input("Nome *")
    cpf = st.text_input("CPF *", max_chars=14, help="Apenas números")
    rg = st.text_input("RG")
    celular = st.text_input("Celular *", max_chars=15)
    email = st.text_input("E-mail *")
    data_nascimento = st.date_input("Data de nascimento *")

    st.markdown("#### **Endereço**")
    cep = st.text_input("CEP")
    rua = st.text_input("Rua")
    numero = st.text_input("Número")
    bairro = st.text_input("Bairro")
    cidade = st.text_input("Cidade")
    estado = st.text_input("Estado")

    st.markdown("#### **Arquivos do profissional**")
    arquivos = st.file_uploader("Upload de documentos (PDF/JPG)", accept_multiple_files=True)

    st.markdown("#### **Opções de salvamento**")
    salvar_local = st.checkbox("Salvar localmente (CSV)", value=True)
    salvar_nuvem = st.checkbox("Salvar no Google Sheets/Drive", value=True)

    submitted = st.form_submit_button("Finalizar Cadastro")

if submitted:
    # Máscara e validação
    cpf_format = formatar_cpf(cpf)
    cel_format = formatar_celular(celular)

    # Carregar cadastros já existentes para evitar duplicidade
    df_existente = carregar_registros(sheet_url)
    duplicado = False
    if not df_existente.empty and cpf in df_existente.get("CPF", []):
        duplicado = True
        st.warning("CPF já cadastrado!")

    # Checagem de campos obrigatórios
    obrigatorios = [nome, cpf, celular, email, data_nascimento]
    if any([not campo for campo in obrigatorios]):
        st.error("Preencha todos os campos obrigatórios (*).")
    elif not validar_cpf(cpf):
        st.error("CPF inválido! Deve conter 11 dígitos.")
    elif not validar_celular(celular):
        st.error("Celular inválido! Deve conter DDD e número.")
    elif duplicado:
        st.error("Não é possível cadastrar duplicado.")
    else:
        # Salvar arquivos em nuvem/local
        links_arquivos = []
        if arquivos:
            for arquivo in arquivos:
                url = None
                if salvar_nuvem:
                    url = salvar_arquivo_drive(arquivo, folder_id)
                # No modo local, salvar em 'uploads/'
                if salvar_local:
                    os.makedirs("uploads", exist_ok=True)
                    with open(os.path.join("uploads", arquivo.name), "wb") as f:
                        f.write(arquivo.read())
                links_arquivos.append(url if url else f"uploads/{arquivo.name}")
        
        # Dados para salvar
        dados = [
            nome, cpf_format, rg, cel_format, email, str(data_nascimento),
            cep, rua, numero, bairro, cidade, estado,
            "; ".join(links_arquivos)
        ]
        salvar_ok = False
        if salvar_nuvem or salvar_local:
            salvar_dados(dados, sheet_url)
            salvar_ok = True
        if salvar_ok:
            st.success("Cadastro realizado com sucesso!")
            st.write("Visualizar cadastros:", df_existente.append(pd.Series(dados, index=df_existente.columns), ignore_index=True))
        else:
            st.warning("Nenhuma opção de salvamento selecionada.")

# =============== ESTILO (CSS STREAMLIT BÁSICO) ===============
st.markdown("""
<style>
    .css-1cpxqw2 {background-color: #f5f7ff;}
    .stButton>button {background-color: #1936b0; color: white;}
    .stForm {border-radius: 10px; border: 2px solid #f09595;}
</style>
""", unsafe_allow_html=True)
