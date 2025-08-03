import streamlit as st
import pandas as pd
import re
from datetime import datetime, date, timedelta
from io import BytesIO

# Google Auth/Sheets/Drive
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ======== CONFIGURAÇÃO GOOGLE ==========
st.sidebar.header("Configuração Google API")
google_creds_file = st.sidebar.file_uploader("Upload credenciais Google (JSON)", type="json")
sheet_url = st.sidebar.text_input("URL da Google Sheet", value="https://docs.google.com/spreadsheets/d/1eef9J3LerPGYIFzBtrP68GQbP6dQZy6umG195tGfveo/edit?gid=0#gid=0/edit")
folder_id = st.sidebar.text_input("ID da pasta Google Drive para anexos", value="1ABCdEfgHiJklmnOPqRsTuvWxyZ")

if google_creds_file:
    import json
    creds = Credentials.from_service_account_info(
        json.load(google_creds_file),
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )

    gc = gspread.authorize(creds)
    service_drive = build('drive', 'v3', credentials=creds)
    SHEET_OK = True
else:
    creds = gc = service_drive = None
    SHEET_OK = False

def salvar_arquivo_drive(file, folder_id, cpf, nome, doc_type):
    if SHEET_OK and folder_id and file is not None:
        arquivo_nomeado = f"{cpf}_{nome}_{doc_type}_{file.name}"
        file_metadata = {
            'name': arquivo_nomeado,
            'parents': [folder_id]
        }
        media = MediaIoBaseUpload(BytesIO(file.read()), mimetype=file.type)
        uploaded_file = service_drive.files().create(
            body=file_metadata, 
            media_body=media, 
            fields='id,webViewLink'
        ).execute()
        return uploaded_file.get('webViewLink')
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

st.title("Cadastro de Profissional (Google Sheets + Drive)")

with st.form("cadastro_prof"):
    st.markdown("#### **Informações Pessoais**")
    nome = st.text_input("Nome *")
    cpf = st.text_input("CPF *", max_chars=14, help="Apenas números")
    rg = st.text_input("RG *")
    celular = st.text_input("Celular *", max_chars=15, help="Apenas números")
    email = st.text_input("E-mail *")
    
    # Permite selecionar datas até HOJE - 18 anos
    from datetime import date, timedelta
    
    data_limite = date.today() - timedelta(days=18*365)
    data_nascimento = st.date_input(
        "Data de nascimento *",
        value=data_limite,  # sempre dentro do limite!
        format="DD/MM/YYYY",
        max_value=data_limite
    )
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
    data_nascimento_br = data_nascimento.strftime("%d/%m/%Y")
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
        # Validação de idade final e de data futura
        hoje = date.today()
        idade = hoje.year - data_nascimento.year - ((hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day))
        if data_nascimento > hoje:
            st.error("A data de nascimento não pode ser no futuro.")
        elif idade < 18:
            st.error("É necessário ter pelo menos 18 anos para se cadastrar.")
        else:
            # prossegue para salvar...

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
                data_nascimento_br,
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


