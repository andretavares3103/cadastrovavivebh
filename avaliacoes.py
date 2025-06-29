import streamlit as st
import pandas as pd
import urllib.parse

st.set_page_config(page_title="Portal de Atendimentos Vavivê BH", layout="wide")

# Senha fixa
SENHA_CORRETA = "vvv"

# Estados globais
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
if "arquivo_cartoes" not in st.session_state:
    st.session_state["arquivo_cartoes"] = None
if "os_visiveis" not in st.session_state:
    st.session_state["os_visiveis"] = []

def formatar_hora(h):
    try:
        if pd.isnull(h) or h == "":
            return ""
        h_str = str(h).strip()
        if ":" in h_str and len(h_str) == 8:
            return h_str[:5]
        if ":" in h_str and len(h_str) == 5:
            return h_str
        return pd.to_datetime(h_str).strftime("%H:%M")
    except:
        return str(h)

def listar_atendimentos(arquivo_excel):
    df = pd.read_excel(arquivo_excel, sheet_name="Clientes")
    df["Data 1"] = pd.to_datetime(df["Data 1"], errors="coerce")
    dias_pt = {
        "Monday": "segunda-feira", "Tuesday": "terça-feira", "Wednesday": "quarta-feira",
        "Thursday": "quinta-feira", "Friday": "sexta-feira", "Saturday": "sábado", "Sunday": "domingo"
    }
    df["Dia da Semana"] = df["Data 1"].dt.day_name().map(dias_pt)
    df["Data 1 Formatada"] = df["Data 1"].dt.strftime("%d/%m/%Y")
    df["Horas de serviço"] = df["Horas de serviço"].apply(formatar_hora)
    df["Hora de entrada"] = df["Hora de entrada"].apply(formatar_hora)
    df = df[df["OS"].notnull()]
    df = df.sort_values("Data 1")
    opcoes = [
        (
            f'OS {row.OS} | {row["Data 1 Formatada"]} | {row["Serviço"]} | {row["Bairro"]} | {row["Cliente"]}',
            int(row.OS)
        )
        for _, row in df.iterrows()
    ]
    return opcoes, df

def gerar_cartoes_global(df, os_visiveis):
    cards = []
    if df is None or not os_visiveis:
        return "<div style='color:orange;'>Nenhum atendimento selecionado.</div>"
    df = df[df["OS"].astype(int).isin(os_visiveis)]
    for _, row in df.iterrows():
        servico = row.get("Serviço", "")
        bairro = row.get("Bairro", "")
        data = row.get("Data 1 Formatada", "")
        dia_semana = row.get("Dia da Semana", "")
        horas_servico = row.get("Horas de serviço", "")
        hora_entrada = row.get("Hora de entrada", "")
        referencia = row.get("Ponto de Referencia", "")
        os = row.get("OS", "")
        mensagem = (
            f"Aceito a OS{os} do atendimento de {servico} no bairro {bairro}, "
            f"para o dia {dia_semana}, {data}. "
            f"Horário de entrada: {hora_entrada}"
        )
        mensagem_url = urllib.parse.quote(mensagem)
        celular = "31995265364"
        whatsapp_url = f"https://wa.me/55{celular}?text={mensagem_url}"

        card_html = f"""
        <div style="
            background: #fff;
            border: 1.5px solid #eee;
            border-radius: 18px;
            padding: 24px 22px 16px 22px;
            margin: 18px;
            min-width: 300px;
            max-width: 380px;
            color: #00008B;
            font-family: Arial, sans-serif;
        ">
            <div style="font-size:1.35em; font-weight:bold; color:#00008B; margin-bottom:2px;">
                {servico}
            </div>
            <div style="font-size:1.10em; color:#00008B; margin-bottom:8px;">
                <b style="color:#00008B;">Bairro:</b> <span style="color:#00008B;">{bairro}</span>
            </div>
            <div style="font-size:1em; color:#00008B;">
                <b style="color:#00008B;">Data:</b> <span style="color:#00008B;">{data} ({dia_semana})</span><br>
                <b style="color:#00008B;">Duração do atendimento:</b> <span style="color:#00008B;">{horas_servico}</span><br>
                <b style="color:#00008B;">Hora de entrada:</b> <span style="color:#00008B;">{hora_entrada}</span><br>
                <b style="color:#00008B;">Ponto de Referência:</b> <span style="color:#00008B;">{referencia if referencia and referencia != 'nan' else '-'}</span>
            </div>
            <a href="{whatsapp_url}" target="_blank">
                <button style="margin-top:18px;padding:10px 24px;background:#25D366;color:#fff;border:none;border-radius:8px;font-size:1.07em; font-weight:700;cursor:pointer; width:100%;">
                    Aceitar Atendimento no WhatsApp
                </button>
            </a>
        </div>
        """
        cards.append(card_html)
    if not cards:
        return "<div style='color:orange;'>Nenhum atendimento selecionado.</div>"
    grid_html = f"""
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 24px;">
        {''.join(cards)}
    </div>
    """
    return grid_html

st.markdown("""
<div style="display: flex; align-items: center; width: 25%; background: #406040; padding: 24px 0 24px 0;">
    <img src="https://i.imgur.com/gIhC0fC.png" height="78" style="margin-left: 40px; margin-right: 40px;">
    <span style="font-size: 2rem; font-weight: 800; color: #18d96b; font-family: Arial, sans-serif; letter-spacing: 1px;">
        VAVIVÊ BH
    </span>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style="color:#333; font-size:1.12rem; margin-top:20px; margin-bottom:10px;">
    Consulte abaixo os atendimentos disponíveis!
</div>
""", unsafe_allow_html=True)

if not st.session_state["autenticado"]:
    senha = st.text_input("Digite a senha de administrador", type="password")
    if st.button("Entrar"):
        if senha == SENHA_CORRETA:
            st.session_state["autenticado"] = True
            st.success("Acesso liberado!")
        else:
            st.error("Senha incorreta!")
else:
    uploaded_file = st.file_uploader(
        "Faça upload do arquivo Excel com a aba 'Clientes'",
        type=["xlsx"]
    )
    if uploaded_file:
        st.session_state["arquivo_cartoes"] = uploaded_file
        opcoes, df = listar_atendimentos(uploaded_file)
        os_selecionados = st.multiselect(
            "Selecione os atendimentos para gerar cartão WhatsApp:",
            options=[op[1] for op in opcoes],
            format_func=lambda x: next(label for label, os_num in opcoes if os_num == x),
        )
        st.session_state["os_visiveis"] = os_selecionados
        if st.button("Exibir atendimentos selecionados"):
            if not os_selecionados:
                st.warning("Selecione pelo menos um atendimento!")
            else:
                st.markdown(
                    gerar_cartoes_global(df, os_selecionados),
                    unsafe_allow_html=True
                )
