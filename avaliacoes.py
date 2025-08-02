import streamlit as st
import pandas as pd
import re
from datetime import datetime
from io import BytesIO

# Google Auth/Sheets/Drive
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ======== CONFIGURAÇÃO GOOGLE ==========
st.sidebar.header("Configuração Google API")
google_creds_file = st.sidebar.file_uploader("Upload credenciais Google (JSON)", type="json")
sheet_url = st.sidebar.text_input("URL da Google Sheet", value="https://docs.google.com/spreadsheets/d/SEU_ID_AQUI")
folder_id = st.sidebar.text_input("ID da pasta Google Drive para anexos", value="PASTA_ID_AQUI")

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

# ===== Função para salvar anexo no Drive =====
def salvar_arquivo_drive(file, folder_id, cpf, nome):
    if SHEET_OK and folder_id and file is not None:
        arquivo_nomeado = f"{cpf}_{nome}_{file.name}"
        file_metadata = {
            'name': arquivo_nomeado,
            'parents': [folder_id]
        }
        media = MediaIoBaseUpload(BytesIO(file.read()), mimetype=file.type)
        uploaded_file = service_drive.files().create(body=file_metadata, media_body=media, fields='id,webViewLink').execute()
        return uploaded_file.get('webViewLink')
    return None

# ===== Máscara e Validação CPF/Celular =====
def formatar_cpf(valor):
    valor = re.sub(r'\D', '', valor)
    if len(valor) == 11:
        return "%s.%s.%s-%s" % (valor[:3], valor[3:6], valor[6:9], valor[9:])
    return valor

def validar_cpf(cpf):
    cpf = re.sub(r'\D', '', cpf)
    return len(cpf) == 11

def validar_celular(cel):
    cel = re.sub(r'\D', '', cel)
    return len(cel) in [10, 11]

# =============== FORMULÁRIO COMPLETO ===============
st.title("Cadastro de Profissional (Google Sheets + Drive)")

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

    submitted = st.form_subm_
