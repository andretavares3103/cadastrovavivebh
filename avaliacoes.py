import streamlit as st
import pandas as pd
import re
import os
import uuid
from datetime import datetime
from io import BytesIO

# Google Auth/Sheets/Drive
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ========== CONFIGURAÇÃO GOOGLE ==========
st.sidebar.header("Configuração Google API")
google_creds_file = st.sidebar.file_uploader("Upload credenciais Google (JSON)", type="json")
sheet_url = st.sidebar.text_input("URL da Google Sheet", value="https://docs.google.com/spreadsheets/d/SEU_ID_AQUI")
folder_id = st.sidebar.text_input("ID da pasta Google Drive para anexos", value="PASTA_ID_AQUI")

# Carregar credenciais
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

# ===== Função salvar anexo no Drive e retornar URL =====
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

# =============== Máscara e Validação CPF/Celular ===============
def formatar_cpf(valor):
    valor = re.sub(r'\D', '', valor)
    if len(valor) == 11:
        return "%s.%s.%s-%s" % (valor[:3], valor[3:6], valor[6:9], valor[9:])
    return valor

def validar_cpf(cpf):
    cpf = re.sub(r'\D', '', cpf)
    return len(cpf) == 11

# =============== FORMULÁRIO ===============
st.title("Cadastro de Profissional (Google Sheets + Drive)")

with st.form("cadastro_prof"):
    st.markdown("#### **Informações Pessoais**")
    nome = st.text_input("Nome *")
    cpf = st.text_input("CPF *", max_chars=14, help="Apenas números")
    email = st.text_input("E-mail *")
    data_nascimento = st.date_input("Data de nascimento *")

    st.markdown("#### **Arquivos do profissional**")
    arquivos = st.file_uploader("Upload de documentos (PDF/JPG)", accept_multiple_files=True)

    submitted = st.form_submit_button("Finalizar Cadastro")

if submitted:
    cpf_format = formatar_cpf(cpf)
    obrigatorios = [nome, cpf, email, data_nascimento]
    if any([not campo for campo in obrigatorios]):
        st.error("Preencha todos os campos obrigatórios (*).")
    elif not validar_cpf(cpf):
        st.error("CPF inválido! Deve conter 11 dígitos.")
    elif not SHEET_OK:
        st.error("Configure o acesso à Google API no menu lateral.")
    else:
        # Salvar arquivos no Drive e pegar links
        links_arquivos = []
        if arquivos:
            for arquivo in arquivos:
                url = salvar_arquivo_drive(arquivo, folder_id, cpf, nome)
                links_arquivos.append(url if url else "Falha no upload")

        # Salvar dados na Google Sheets
        sh = gc.open_by_url(sheet_url)
        worksheet = sh.sheet1
        dados = [
            nome,
            cpf_format,
            email,
            str(data_nascimento),
            "; ".join(links_arquivos),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ]
        worksheet.append_row(dados)
        st.success("Cadastro realizado com sucesso!")
        st.write("Links dos anexos enviados:", links_arquivos)

# =============== VISUALIZAÇÃO ADMIN (SIMPLES) ===============
st.markdown("---")
if SHEET_OK and st.checkbox("Mostrar todos cadastros"):
    sh = gc.open_by_url(sheet_url)
    worksheet = sh.sheet1
    df = pd.DataFrame(worksheet.get_all_records())
    st.dataframe(df, use_container_width=True)
