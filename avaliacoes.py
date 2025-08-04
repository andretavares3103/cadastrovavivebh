import streamlit as st
import pandas as pd
import re
from datetime import datetime, date
from io import BytesIO
import json

# Google Auth/Sheets/Drive
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ======== CONFIGURAÇÃO GOOGLE ==========
sheet_url = st.sidebar.text_input("URL da Google Sheet", value="...")
folder_id = st.sidebar.text_input("ID da pasta Google Drive para anexos", value="...")

import json

creds = Credentials.from_service_account_info(
    json.loads(st.secrets["GOOGLE_CREDS"]),
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
)
gc = gspread.authorize(creds)
service_drive = build('drive', 'v3', credentials=creds)
SHEET_OK = True



def salvar_arquivo_drive(file, folder_id, cpf, nome, doc_type):
    if SHEET_OK and folder_id and file is not None:
        try:
            arquivo_nomeado = f"{cpf}_{nome}_{doc_type}_{file.name}"
            file_metadata = {
                'name': arquivo_nomeado,
                'parents': [folder_id]
            }
            media = MediaIoBaseUpload(BytesIO(file.read()), mimetype=file.type)
            uploaded_file = service_drive.files().create(
                body=file_metadata, 
                media_body=media, 
                fields='id,webViewLink',
                supportsAllDrives=True   # <-- ESSA LINHA É IMPORTANTE!
            ).execute()
            return uploaded_file.get('webViewLink')
        except Exception as e:
            st.error(f"Erro ao salvar no Google Drive: {e}")
            return None
    return None




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

def formatar_cep(valor):
    valor = re.sub(r'\D', '', valor)
    if len(valor) == 8:
        return "%s-%s" % (valor[:5], valor[5:])
    return valor

def validar_cpf(cpf):
    cpf = re.sub(r'\D', '', cpf)
    return len(cpf) == 11

def validar_celular(cel):
    cel = re.sub(r'\D', '', cel)
    return len(cel) in [10, 11]

def validar_cep(cep):
    cep = re.sub(r'\D', '', cep)
    return len(cep) == 8

def validar_data_nascimento(data_str):
    try:
        return datetime.strptime(data_str, "%d/%m/%Y")
    except:
        return None

st.title("Cadastro de Profissional (Google Sheets + Drive)")

with st.form("cadastro_prof"):
    st.markdown("#### **Informações Pessoais**")
    nome = st.text_input("Nome *")
    cpf = st.text_input("CPF *", max_chars=14, help="Apenas números")
    rg = st.text_input("RG *")
    celular = st.text_input("Celular *", max_chars=15, help="Apenas números")
    email = st.text_input("E-mail *")
    data_nascimento = st.text_input("Data de nascimento *", placeholder="DD/MM/AAAA")
    
    st.markdown("#### **Endereço**")
    cep = st.text_input("CEP *", max_chars=9, help="Apenas números")
    rua = st.text_input("Rua")
    numero = st.text_input("Número")
    bairro = st.text_input("Bairro")
    cidade = st.text_input("Cidade")
    estado = st.text_input("Estado")

    st.markdown("#### **Documentos obrigatórios**")
    arquivos_rg_cpf = st.file_uploader("RG + CPF (frente e verso, PDF/JPG) *", accept_multiple_files=True)
    comprovante_residencia = st.file_uploader("Comprovante de Residência (PDF/JPG) *", accept_multiple_files=True)

    submitted = st.form_submit_button("Finalizar Cadastro")

if submitted:
    cpf_format = formatar_cpf(cpf)
    celular_format = formatar_celular(celular)
    data_nasc_dt = validar_data_nascimento(data_nascimento)
    cep_format = formatar_cep(cep)

    obrigatorios = {
        "Nome": nome,
        "CPF": cpf,
        "RG": rg,
        "Celular": celular,
        "E-mail": email,
        "Data de nascimento": data_nascimento,
        "CEP": cep
    }
    faltando = [campo for campo, valor in obrigatorios.items() if not valor]
    if faltando:
        st.error("Preencha todos os campos obrigatórios: " + ", ".join(faltando))
    elif not data_nasc_dt:
        st.error("Data de nascimento inválida! Use o formato DD/MM/AAAA.")
    elif not arquivos_rg_cpf:
        st.error("É obrigatório anexar pelo menos 1 arquivo de RG/CPF (frente e verso).")
    elif not comprovante_residencia:
        st.error("É obrigatório anexar pelo menos 1 arquivo de comprovante de residência.")
    elif not validar_cpf(cpf):
        st.error("CPF inválido! Deve conter 11 dígitos.")
    elif not validar_celular(celular):
        st.error("Celular inválido! Deve conter DDD e número.")
    elif not validar_cep(cep):
        st.error("CEP inválido! Deve conter 8 dígitos.")
    elif not SHEET_OK:
        st.error("Configure o acesso à Google API no menu lateral.")
    else:
        # Salvar RG/CPF
        links_rg_cpf = []
        for arquivo in arquivos_rg_cpf:
            url = salvar_arquivo_drive(
                arquivo, folder_id, cpf, nome, "RG_CPF"
            )
            links_rg_cpf.append(url if url else "Falha no upload")

        # Salvar Comprovante de Residência
        links_comprovante = []
        for arquivo in comprovante_residencia:
            url = salvar_arquivo_drive(
                arquivo, folder_id, cpf, nome, "Comprovante"
            )
            links_comprovante.append(url if url else "Falha no upload")

        # Salvar dados na Google Sheets
        sh = gc.open_by_url(sheet_url)
        worksheet = sh.sheet1
        dados = [
            nome,
            cpf_format,
            rg,
            celular_format,
            email,
            data_nasc_dt.strftime("%d/%m/%Y"),
            cep_format,
            rua,
            numero,
            bairro,
            cidade,
            estado,
            "; ".join(links_rg_cpf),
            "; ".join(links_comprovante),
            datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        ]
        worksheet.append_row(dados)
        st.success("Cadastro realizado com sucesso!")
        st.write("RG/CPF enviados:", links_rg_cpf)
        st.write("Comprovante de residência enviado:", links_comprovante)

# =============== VISUALIZAÇÃO ADMIN (simples, opcional) ===============
st.markdown("---")
if SHEET_OK and st.checkbox("Mostrar todos cadastros"):
    sh = gc.open_by_url(sheet_url)
    worksheet = sh.sheet1
    df = pd.DataFrame(worksheet.get_all_records())
    st.dataframe(df, use_container_width=True)
















