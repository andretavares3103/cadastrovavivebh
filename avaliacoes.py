import streamlit as st
import pandas as pd
import re
from datetime import datetime
from io import BytesIO

# ... (Google API setup igual ao exemplo anterior) ...

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
    rg = st.text_input("RG")
    celular = st.text_input("Celular *", max_chars=15, help="Apenas números")
    email = st.text_input("E-mail *")
    data_nascimento = st.date_input("Data de nascimento *", format="DD/MM/YYYY")

    st.markdown("#### **Endereço**")
    cep = st.text_input("CEP", max_chars=9, help="Apenas números")
    rua = st.text_input("Rua")
    numero = st.text_input("Número")
    bairro = st.text_input("Bairro")
    cidade = st.text_input("Cidade")
    estado = st.text_input("Estado")

    st.markdown("#### **Arquivos do profissional**")
    arquivos = st.file_uploader("Upload de documentos (PDF/JPG)", accept_multiple_files=True)

    submitted = st.form_submit_button("Finalizar Cadastro")

if submitted:
    cpf_format = formatar_cpf(cpf)
    celular_format = formatar_celular(celular)
    data_nascimento_br = data_nascimento.strftime("%d/%m/%Y")
    cep_format = formatar_cep(cep)

    obrigatorios = {
        "Nome": nome,
        "CPF": cpf,
        "Celular": celular,
        "E-mail": email,
        "Data de nascimento": data_nascimento
    }
    faltando = [campo for campo, valor in obrigatorios.items() if not valor]
    if faltando:
        st.error("Preencha todos os campos obrigatórios: " + ", ".join(faltando))
    elif not validar_cpf(cpf):
        st.error("CPF inválido! Deve conter 11 dígitos.")
    elif not validar_celular(celular):
        st.error("Celular inválido! Deve conter DDD e número.")
    elif cep and not validar_cep(cep):
        st.error("CEP inválido! Deve conter 8 dígitos.")
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
            "; ".join(links_arquivos),
            datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        ]
        worksheet.append_row(dados)
        st.success("Cadastro realizado com sucesso!")
        st.write("Links dos anexos enviados:", links_arquivos)

# ... painel admin opcional igual ao anterior ...
