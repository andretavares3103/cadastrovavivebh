import streamlit as st
import pandas as pd
import sqlite3
import os
import uuid
import hashlib
from datetime import datetime

UPLOADS_DIR = "uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)
DB_PATH = "cadastros.db"

# ----------- AUTENTICAÇÃO SEGURA -----------
def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

ADMIN_USER = "admin"
ADMIN_HASH = hash_senha("vvv")  # Troque pela sua senha forte!

def autenticar(usuario, senha):
    return usuario == ADMIN_USER and hash_senha(senha) == ADMIN_HASH

# ----------- BANCO DE DADOS -----------
def conectar():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def criar_tabela():
    with conectar() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS profissionais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT, cpf TEXT, rg TEXT, celular TEXT, email TEXT, data_nascimento TEXT,
            cep TEXT, rua TEXT, numero TEXT, bairro TEXT, cidade TEXT, estado TEXT,
            arquivos TEXT, data_cadastro TEXT
        )""")

def inserir_profissional(dados, links_arquivos):
    with conectar() as conn:
        conn.execute("""
        INSERT INTO profissionais
        (nome, cpf, rg, celular, email, data_nascimento, cep, rua, numero, bairro, cidade, estado, arquivos, data_cadastro)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (*dados, ";".join(links_arquivos), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

def listar_profissionais():
    with conectar() as conn:
        return pd.read_sql("SELECT * FROM profissionais", conn)

criar_tabela()

# ----------- LAYOUT -----------
st.set_page_config("Cadastro de Profissional", layout="wide")
tabs = st.tabs(["📋 Cadastro de Profissional", "🔑 Admin (Visualizar Cadastros)"])

# ========== TELA 1: Cadastro ==========
with tabs[0]:
    st.header("Cadastro de Profissional")
    with st.form("form_cadastro"):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome *")
            cpf = st.text_input("CPF *", max_chars=14)
            rg = st.text_input("RG")
            celular = st.text_input("Celular *", max_chars=15)
            email = st.text_input("E-mail *")
            data_nascimento = st.date_input("Data de nascimento *")
        with col2:
            cep = st.text_input("CEP")
            rua = st.text_input("Rua")
            numero = st.text_input("Número")
            bairro = st.text_input("Bairro")
            cidade = st.text_input("Cidade")
            estado = st.text_input("Estado")
        arquivos = st.file_uploader("Upload de documentos (PDF/JPG)", accept_multiple_files=True)
        enviado = st.form_submit_button("Finalizar Cadastro")
    if enviado:
        obrigatorios = [nome, cpf, celular, email, data_nascimento]
        if any([not campo for campo in obrigatorios]):
            st.error("Preencha todos os campos obrigatórios.")
        else:
            links_arquivos = []
            if arquivos:
                for arq in arquivos:
                    arq_name = f"{uuid.uuid4()}_{arq.name}"
                    arq_path = os.path.join(UPLOADS_DIR, arq_name)
                    with open(arq_path, "wb") as f:
                        f.write(arq.read())
                    links_arquivos.append(arq_path)
            dados = [nome, cpf, rg, celular, email, str(data_nascimento), cep, rua, numero, bairro, cidade, estado]
            inserir_profissional(dados, links_arquivos)
            st.success("Cadastro realizado com sucesso!")

# ========== TELA 2: Admin (com autenticação segura, busca e filtro) ==========
with tabs[1]:
    st.header("Administração de Cadastros")
    if "admin_autenticado" not in st.session_state:
        st.session_state.admin_autenticado = False

    if not st.session_state.admin_autenticado:
        with st.form("form_login"):
            usuario = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            login = st.form_submit_button("Entrar")
        if login:
            if autenticar(usuario, senha):
                st.session_state.admin_autenticado = True
                st.success("Login realizado com sucesso!")
            else:
                st.error("Usuário ou senha incorretos.")
        st.stop()

    # Se chegou aqui, está autenticado
    st.success(f"Bem-vindo, {ADMIN_USER}!")

    df = listar_profissionais()
    if df.empty:
        st.info("Nenhum cadastro realizado ainda.")
        st.stop()

    # --------- FILTROS (por nome, período) ----------
    colf1, colf2 = st.columns([2, 3])

    with colf1:
        busca_nome = st.text_input("Buscar por nome").strip().lower()
    with colf2:
        st.write("Filtrar por data de cadastro:")
        min_date = df["data_cadastro"].min()
        max_date = df["data_cadastro"].max()
        if pd.isnull(min_date): min_date = datetime.today().strftime("%Y-%m-%d")
        if pd.isnull(max_date): max_date = datetime.today().strftime("%Y-%m-%d")
        data_inicio, data_fim = st.date_input(
            "Período:",
            [pd.to_datetime(min_date).date(), pd.to_datetime(max_date).date()]
        )

    df_filtro = df.copy()
    if busca_nome:
        df_filtro = df_filtro[df_filtro["nome"].str.lower().str.contains(busca_nome)]
    # Filtra pelo período
    df_filtro = df_filtro[
        (pd.to_datetime(df_filtro["data_cadastro"]) >= pd.to_datetime(data_inicio)) &
        (pd.to_datetime(df_filtro["data_cadastro"]) <= pd.to_datetime(data_fim))
    ]
    st.markdown(f"**Total encontrado:** {len(df_filtro)} cadastro(s)")

    # -------- TABELA E DOWNLOADS -----------
    st.dataframe(df_filtro.drop(columns=["id"]), hide_index=True, use_container_width=True)

    st.subheader("Download de Documentos (anexos)")
    for idx, row in df_filtro.iterrows():
        if row["arquivos"]:
            for arq_path in row["arquivos"].split(";"):
                arq_path = arq_path.strip()
                if arq_path and os.path.exists(arq_path):
                    with open(arq_path, "rb") as f:
                        st.download_button(
                            f"Baixar: {os.path.basename(arq_path)} (Profissional: {row['nome']})",
                            data=f.read(),
                            file_name=os.path.basename(arq_path),
                            key=f"{arq_path}_{idx}"
                        )
    # -------- EXPORTAR FILTRO ----------
    st.subheader("Exportar Cadastros Filtrados")
    csv = df_filtro.to_csv(index=False).encode("utf-8")
    st.download_button("Exportar para CSV", data=csv, file_name="cadastros_filtrados.csv")
    excel = df_filtro.to_excel(index=False, engine='openpyxl')
    st.download_button("Exportar para Excel", data=excel, file_name="cadastros_filtrados.xlsx")

