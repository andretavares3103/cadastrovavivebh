import streamlit as st
import pandas as pd
import re
from datetime import datetime
from io import BytesIO
import json

# ========== CONFIGURAÇÕES FIXAS ==========
SHEET_ID = "10PiH_xBokxZUH-hVvLsrUmNNQnpsfkdOwLhjNkAibnA"
FOLDER_ID = "135edeOCoqfVtV1AOTdUYKhgivom07InY"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"

# ======= CREDENCIAIS GOOGLE PELO st.secrets =======
creds_dict = json.loads(st.secrets["GOOGLE_CREDS"])
from google.oauth2.service_account import Credentials
creds = Credentials.from_service_account_info(
    creds_dict,
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
)
import gspread
gc = gspread.authorize(creds)
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
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
                supportsAllDrives=True
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

# ================= TELA INICIAL ====================
if "tela" not in st.session_state:
    st.session_state["tela"] = "inicio"
if "cadastro_finalizado" not in st.session_state:
    st.session_state["cadastro_finalizado"] = False

st.title("Recrutamento e treinamento de Profissional VAVIVÊ BH")

if st.session_state["tela"] == "inicio":
    st.markdown("## O que você deseja fazer?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Novo Cadastro"):
            st.session_state["tela"] = "cadastro"
    with col2:
        if st.button("Já tenho cadastro (Agendar horário)"):
            st.session_state["tela"] = "agendamento"
    st.stop()

# ================== FLUXO NOVO CADASTRO ==================
if st.session_state["tela"] == "cadastro":
    if not st.session_state["cadastro_finalizado"]:
        with st.form("cadastro_prof"):
            st.markdown("#### **Informações Pessoais**")
            nome = st.text_input("*Nome")
            cpf = st.text_input("*CPF sem pontos ou traços", max_chars=14, help="Apenas números")
            rg = st.text_input("*RG")
            celular = st.text_input("*Celular (Apenas números com DDD)", max_chars=15, help="Apenas números")
            email = st.text_input("*E-mail")
            data_nascimento = st.text_input("*Data de nascimento (Incluir barras)", placeholder="DD/MM/AAAA")
            
            st.markdown("#### **Endereço**")
            cep = st.text_input("*CEP", max_chars=9, help="Apenas números")
            rua = st.text_input("Rua")
            numero = st.text_input("*Número")
            bairro = st.text_input("Bairro")
            cidade = st.text_input("Cidade")
            estado = st.text_input("Estado")

            st.markdown("#### **Documentos obrigatórios**")
            arquivos_rg_cpf = st.file_uploader("RG + CPF (frente e verso, PDF/JPG) *", accept_multiple_files=True)
            comprovante_residencia = st.file_uploader("Comprovante de Residência (PDF/JPG) *", accept_multiple_files=True)

            # --- Configuração da sua planilha de horários
            HORARIOS_SHEET_ID = SHEET_ID
            ABA_HORARIOS = "Página2"
            sh_horarios = gc.open_by_key(HORARIOS_SHEET_ID)
            worksheet_horarios = sh_horarios.worksheet(ABA_HORARIOS)
            df_horarios = pd.DataFrame(worksheet_horarios.get_all_records())
            disponiveis = df_horarios[df_horarios["Disponivel"].str.upper() == "SIM"]
            disponiveis["Opção"] = (
                disponiveis["Data"] + " (" + disponiveis["Dia Semana"] + ") - " + disponiveis["Horario"]
            )
            st.markdown("### Treinamento Presencial Obrigatório (Selecione um horário disponível)")
            if not disponiveis.empty:
                horario_escolhido = st.selectbox(
                    "Horários disponíveis:",
                    disponiveis["Opção"].tolist()
                )
            else:
                horario_escolhido = ""
                st.warning("Nenhum horário disponível no momento.")

            submitted = st.form_submit_button("Finalizar Cadastro")

        if submitted:
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
            else:
                # ------------- BLOQUEIO DE CPF DUPLICADO -------------------
                sh = gc.open_by_key(SHEET_ID)
                worksheet = sh.worksheet("Página1")
                df_cadastros = pd.DataFrame(worksheet.get_all_records())
                cpfs_ja_cadastrados = df_cadastros["CPF"].astype(str).str.replace(r'\D', '', regex=True).tolist()
                cpf_digitado = re.sub(r'\D', '', cpf)
                if cpf_digitado in cpfs_ja_cadastrados:
                    st.error("Já existe um cadastro com esse CPF. Se precisar atualizar algum dado ou trocar de horário, entre em contato conosco via WhatsApp.")
                    st.stop()
                # ----------------------------------------------------------
                cpf_format = formatar_cpf(cpf)
                celular_format = formatar_celular(celular)
                data_nasc_dt = validar_data_nascimento(data_nascimento)
                cep_format = formatar_cep(cep)

                if not data_nasc_dt:
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
                elif not horario_escolhido:
                    st.error("Selecione um horário disponível para treinamento!")
                else:
                    # Salvar RG/CPF
                    links_rg_cpf = []
                    for arquivo in arquivos_rg_cpf:
                        url = salvar_arquivo_drive(
                            arquivo, FOLDER_ID, cpf, nome, "RG_CPF"
                        )
                        links_rg_cpf.append(url if url else "Falha no upload")
                    # Salvar Comprovante de Residência
                    links_comprovante = []
                    for arquivo in comprovante_residencia:
                        url = salvar_arquivo_drive(
                            arquivo, FOLDER_ID, cpf, nome, "Comprovante"
                        )
                        links_comprovante.append(url if url else "Falha no upload")
                    # Debug: veja qual valor está chegando do selectbox
                    m = re.match(r"(\d{1,2}/\d{1,2}/\d{2,4}) \((.*?)\) - (.+)", horario_escolhido)
                    if m:
                        data_selecionada = m.group(1)
                        dia_semana = m.group(2)
                        horario = m.group(3)
                    else:
                        data_selecionada = horario = dia_semana = ""
                        st.warning("Não foi possível extrair data, dia e horário do horário selecionado!")
                    # Salvar dados na Google Sheets (na primeira aba da planilha)
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
                        data_selecionada,
                        horario,
                        dia_semana,
                        datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    ]
                    worksheet.append_row(dados)
                    st.session_state["cadastro_finalizado"] = True
                    st.rerun()
    else:
        st.success("Cadastro finalizado com sucesso! Entraremos em contato para validar o seu horário escolhido.")
        if st.button("Novo cadastro"):
            st.session_state["cadastro_finalizado"] = False
            st.session_state["tela"] = "inicio"
        if st.button("Agendar novo horário"):
            st.session_state["cadastro_finalizado"] = False
            st.session_state["tela"] = "agendamento"

# =========== FLUXO APENAS AGENDAMENTO DE HORÁRIO ==============
if st.session_state["tela"] == "agendamento":
    st.header("Agendamento de Horário para Profissional já cadastrada")
    cpf_agendamento = st.text_input("Digite seu CPF (apenas números):", max_chars=11)
    buscar = st.button("Buscar cadastro")
    if buscar and cpf_agendamento and len(re.sub(r'\D', '', cpf_agendamento)) == 11:
        sh = gc.open_by_key(SHEET_ID)
        worksheet = sh.worksheet("Página1")
        df_cadastros = pd.DataFrame(worksheet.get_all_records())
        cpf_pesquisa = re.sub(r'\D', '', cpf_agendamento)
        registros = df_cadastros[df_cadastros["CPF"].astype(str).str.replace(r'\D', '', regex=True) == cpf_pesquisa]
        if not registros.empty:
            linha = registros.iloc[0]
            if pd.notna(linha.get("Data")) and pd.notna(linha.get("Horario")) and str(linha.get("Data")).strip():
                st.success(f"Você já possui um agendamento:\n\nData: {linha['Data']} ({linha.get('Dia semana', '')})\nHorário: {linha['Horario']}\n\nSe precisar trocar, entre em contato conosco via WhatsApp.")
            else:
                # Não tem agendamento ainda, permite escolher
                # --- Planilha de horários
                HORARIOS_SHEET_ID = SHEET_ID
                ABA_HORARIOS = "Página2"
                sh_horarios = gc.open_by_key(HORARIOS_SHEET_ID)
                worksheet_horarios = sh_horarios.worksheet(ABA_HORARIOS)
                df_horarios = pd.DataFrame(worksheet_horarios.get_all_records())
                disponiveis = df_horarios[df_horarios["Disponivel"].str.upper() == "SIM"]
                disponiveis["Opção"] = (
                    disponiveis["Data"] + " (" + disponiveis["Dia Semana"] + ") - " + disponiveis["Horario"]
                )
                if not disponiveis.empty:
                    horario_escolhido = st.selectbox(
                        "Horários disponíveis para selecionar:",
                        disponiveis["Opção"].tolist()
                    )
                    confirmar = st.button("Confirmar horário")
                    if confirmar:
                        m = re.match(r"(\d{1,2}/\d{1,2}/\d{2,4}) \((.*?)\) - (.+)", horario_escolhido)
                        if m:
                            data_selecionada = m.group(1)
                            dia_semana = m.group(2)
                            horario = m.group(3)
                            idx = registros.index[0]
                            worksheet.update_cell(idx+2, df_cadastros.columns.get_loc("Data")+1, data_selecionada)
                            worksheet.update_cell(idx+2, df_cadastros.columns.get_loc("Horario")+1, horario)
                            worksheet.update_cell(idx+2, df_cadastros.columns.get_loc("Dia semana")+1, dia_semana)
                            st.success(
                                f"Agendamento realizado!\n\nData: {data_selecionada} ({dia_semana})\nHorário: {horario}"
                            )
                        else:
                            st.error("Formato do horário inválido, tente novamente.")
                else:
                    st.warning("Nenhum horário disponível para agendamento no momento.")
        else:
            st.error("Cadastro não encontrado para o CPF informado. Se for seu primeiro cadastro, volte e selecione 'Novo Cadastro'.")
    elif buscar:
        st.warning("Digite um CPF válido (11 dígitos, apenas números).")

# =============== VISUALIZAÇÃO ADMIN (simples, opcional) ===============
st.markdown("---")
if SHEET_OK and st.checkbox("Mostrar todos cadastros"):
    sh = gc.open_by_key(SHEET_ID)
    worksheet = sh.worksheet("Página1")
    df = pd.DataFrame(worksheet.get_all_records())
    st.dataframe(df, use_container_width=True)
