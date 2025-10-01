import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Ganho da Antena sob Teste", layout="centered")
st.title("📡 Cálculo do Ganho")
st.markdown("Baseado nos coeficientes de transmissão medidos entre duas antenas iguais, com ganho conhecido (antenas padrão) e a antena sob teste.")

# Agrupamento dos campos de entrada
col1, col2, col3, col4 = st.columns([1.5, 1.7, 1.7, 1.5])

with col1:
    st.markdown("<div style='height: 32px;'>📝 Nome da Antena sob Teste</div>", unsafe_allow_html=True)
    aut_nome = st.text_input("", value="Antena sob Teste")

with col2:
    st.markdown("<div style='height: 32px;'>🔧 Freq. central (MHz)</div>", unsafe_allow_html=True)
    fc_input = st.number_input("", min_value=0.0, value=1420.0, step=0.1, format="%.1f")

with col3:
    st.markdown("<div style='height: 32px;'>📈 Ganho das antenas padrão (dBi)</div>", unsafe_allow_html=True)
    gain_ref_input = st.number_input("", value=8.0, step=0.1)

with col4:
    st.markdown("<div style='height: 32px;'>🌐 Idioma</div>", unsafe_allow_html=True)
    idioma = st.selectbox("", ["Português", "English"])


# 🔹 Função unificada para CSV ou RESULT
def carregar_dados(uploaded_file):
    nome_arquivo = uploaded_file.name.lower()
    
    if nome_arquivo.endswith(".csv"):
        # Arquivo CSV do VNA
        df = pd.read_csv(uploaded_file, skiprows=3, names=["Freq_Hz", "S21_dB", "Unused"])
        df["Freq_Hz"] = df["Freq_Hz"].astype(str).str.replace('+', '', regex=False).str.strip()
        df["S21_dB"] = df["S21_dB"].astype(str).str.replace('+', '', regex=False).str.strip()
        df["Freq_Hz"] = df["Freq_Hz"].astype(float)
        df["S21_dB"] = df["S21_dB"].astype(float)
        df["Freq_MHz"] = df["Freq_Hz"] / 1e6
        df = df[["Freq_MHz", "S21_dB"]]
        df = df.rename(columns={"S21_dB": "Amplitude_dB"})
    
    elif nome_arquivo.endswith(".result"):
        # Arquivo .result (7 colunas fixas)
        df = pd.read_csv(
            uploaded_file,
            delim_whitespace=True,
            header=None,
            names=["Freq_Hz", "Unused", "Amplitude_dB", "Azim", "Pol", "Elev", "Timestamp"]
        )
        df = df[["Freq_Hz", "Amplitude_dB"]].copy()
        df["Freq_MHz"] = df["Freq_Hz"] / 1e6
        df = df[["Freq_MHz", "Amplitude_dB"]]
    
    else:
        raise ValueError("Formato de arquivo não suportado. Use .csv ou .result")
    
    return df


# Upload dos arquivos (aceita CSV e RESULT)
uploaded_aut_ref = st.file_uploader("📁 Arquivo (.csv ou .result) com S21 entre padrão e antena sob teste", type=["csv", "result"])
uploaded_ref_ref = st.file_uploader("📁 Arquivo (.csv ou .result) com S21 entre duas antenas padrão", type=["csv", "result"])

if uploaded_aut_ref and uploaded_ref_ref:
    try:
        # Carregar arquivos
        df_aut_ref = carregar_dados(uploaded_aut_ref)
        df_ref_ref = carregar_dados(uploaded_ref_ref)

        # Interpolação para a mesma base de frequências
        freqs_common = df_aut_ref["Freq_MHz"]
        s21_aut_ref_interp = np.interp(freqs_common, df_aut_ref["Freq_MHz"], df_aut_ref["Amplitude_dB"])
        s21_ref_ref_interp = np.interp(freqs_common, df_ref_ref["Freq_MHz"], df_ref_ref["Amplitude_dB"])

        # Cálculo do ganho da antena sob teste ao longo da faixa
        gain_aut_freq = gain_ref_input + (s21_aut_ref_interp - s21_ref_ref_interp)
        df_gain = pd.DataFrame({
            "Frequência (MHz)": freqs_common,
            "Ganho da Antena sob Teste (dBi)": gain_aut_freq
        })

        # Ganho na frequência central
        s21_aut_ref_fc = np.interp(fc_input, df_aut_ref["Freq_MHz"], df_aut_ref["Amplitude_dB"])
        s21_ref_ref_fc = np.interp(fc_input, df_ref_ref["Freq_MHz"], df_ref_ref["Amplitude_dB"])
        gain_aut_fc = gain_ref_input + (s21_aut_ref_fc - s21_ref_ref_fc)

        st.markdown("<hr>", unsafe_allow_html=True)

        # Equação explicativa
        if idioma == "Português":
            st.markdown(
                r"""
                **Equação do cálculo do ganho:**  
                $$
                G_{\text{AUT}} = G_{\text{Padrão}} + (S_{21}^{\text{AUT}} - S_{21}^{\text{Padrão}})
                $$
                """
            )
        else:
            st.markdown(
                r"""
                **Gain calculation equation:**  
                $$
                G_{\text{AUT}} = G_{\text{Standard}} + (S_{21}^{\text{AUT}} - S_{21}^{\text{Standard}})
                $$
                """
            )
        
        # Resultado com destaque
        st.markdown(
            f"<h2 style='text-align: center; color: green;'>📈 Ganho da {aut_nome} em {fc_input:.1f} MHz: <strong>{gain_aut_fc:.2f} dBi</strong></h2>",
            unsafe_allow_html=True
        )

        # Labels e textos dinâmicos por idioma
        if idioma == "Português":
            legenda1 = f"S21 Padrão/Testada (Ganho = {gain_aut_fc:.2f} dBi)"
            legenda2 = "S21 Padrão/Padrão"
            freq_label = "Frequência (MHz)"
            s21_label = "S21 (dB)"
            titulo_s21 = f"Coeficiente de Transmissão S21 ({aut_nome})"
            linha_fc_label = f"Frequência Central: {fc_input} MHz"

            ganho_label = f"Ganho da {aut_nome} (em {fc_input:.1f} MHz = {gain_aut_fc:.2f} dBi)"
            titulo_ganho = f"Ganho da {aut_nome} em função da frequência"
            eixo_y = "Ganho (dBi)"
            eixo_x = "Frequência (MHz)"
            linha_fc_ganho = f"{fc_input} MHz"
        else:
            legenda1 = f"S21 Standard/Test (Gain = {gain_aut_fc:.2f} dBi)"
            legenda2 = "S21 Standard/Standard"
            freq_label = "Frequency (MHz)"
            s21_label = "S21 (dB)"
            titulo_s21 = f"S21 Transmission Coefficient ({aut_nome})"
            linha_fc_label = f"Center Frequency: {fc_input} MHz"

            ganho_label = f"Gain of {aut_nome} (at {fc_input:.1f} MHz = {gain_aut_fc:.2f} dBi)"
            titulo_ganho = f"Gain of {aut_nome} vs Frequency"
            eixo_y = "Gain (dBi)"
            eixo_x = "Frequency (MHz)"
            linha_fc_ganho = f"{fc_input} MHz"

        # Gráfico dos S21
        st.subheader("Visualização dos S21")
        fig1, ax1 = plt.subplots()
        ax1.plot(df_aut_ref["Freq_MHz"], df_aut_ref["Amplitude_dB"], label=legenda1, color='blue')
        ax1.plot(df_ref_ref["Freq_MHz"], df_ref_ref["Amplitude_dB"], label=legenda2, color='green')
        ax1.axvline(fc_input, color='red', linestyle='--', label=linha_fc_label)
        ax1.set_xlabel(freq_label)
        ax1.set_ylabel(s21_label)
        ax1.set_title(titulo_s21)
        ax1.legend(fontsize=9)
        ax1.grid(True)
        st.pyplot(fig1)

        # Gráfico do ganho da antena sob teste
        st.subheader(f"📊 {titulo_ganho}")
        fig2, ax2 = plt.subplots()
        ax2.plot(freqs_common, gain_aut_freq, label=ganho_label, color='purple')
        ax2.axvline(fc_input, color='red', linestyle='--', label=linha_fc_ganho)
        ax2.set_xlabel(eixo_x)
        ax2.set_ylabel(eixo_y)
        ax2.set_title(titulo_ganho)
        ax2.legend(fontsize=9)
        ax2.grid(True)
        st.pyplot(fig2)

        # Exportação dos dados
        csv_output = df_gain.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Baixar CSV com Ganho por Frequência",
            data=csv_output,
            file_name="ganho_antena_sob_teste.csv",
            mime="text/csv"
        )

    except Exception as e:
        st.error(f"Ocorreu um erro ao processar os arquivos: {e}")
