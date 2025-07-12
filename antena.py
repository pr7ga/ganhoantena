import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import StringIO

st.set_page_config(page_title="Ganho da Antena sob Teste", layout="centered")
st.title("📡 Cálculo do Ganho da Antena sob Teste")
st.markdown("Baseado nos coeficientes de transmissão medidos entre antenas padrão e a antena sob teste.")

# Entrada do usuário
fc_input = st.number_input("🔧 Frequência central (MHz)", min_value=0.0, value=1420.0, step=0.1)
gain_ref_input = st.number_input("📈 Ganho da antena padrão (dBi)", value=8.0, step=0.1)

# Função para carregar e tratar os dados dos arquivos CSV
def carregar_csv_formatado(uploaded_file):
    df = pd.read_csv(uploaded_file, skiprows=3, names=["Freq_Hz", "S21_dB", "Unused"])
    df["Freq_Hz"] = df["Freq_Hz"].astype(str).str.replace('+', '', regex=False).str.strip()
    df["S21_dB"] = df["S21_dB"].astype(str).str.replace('+', '', regex=False).str.strip()
    df["Freq_Hz"] = df["Freq_Hz"].astype(float)
    df["S21_dB"] = df["S21_dB"].astype(float)
    df["Freq_MHz"] = df["Freq_Hz"] / 1e6
    return df[["Freq_MHz", "S21_dB"]]

# Upload dos arquivos
uploaded_aut_ref = st.file_uploader("📁 CSV com S21 entre padrão e antena sob teste", type="csv")
uploaded_ref_ref = st.file_uploader("📁 CSV com S21 entre duas antenas padrão", type="csv")

if uploaded_aut_ref and uploaded_ref_ref:
    try:
        # Carregar arquivos
        df_aut_ref = carregar_csv_formatado(uploaded_aut_ref)
        df_ref_ref = carregar_csv_formatado(uploaded_ref_ref)

        # Interpolação para a mesma base de frequências
        freqs_common = df_aut_ref["Freq_MHz"]
        s21_aut_ref_interp = np.interp(freqs_common, df_aut_ref["Freq_MHz"], df_aut_ref["S21_dB"])
        s21_ref_ref_interp = np.interp(freqs_common, df_ref_ref["Freq_MHz"], df_ref_ref["S21_dB"])

        # Cálculo do ganho da antena sob teste ao longo da faixa
        gain_aut_freq = gain_ref_input + (s21_aut_ref_interp - s21_ref_ref_interp)
        df_gain = pd.DataFrame({
            "Frequência (MHz)": freqs_common,
            "Ganho da Antena sob Teste (dBi)": gain_aut_freq
        })

        # Ganho na frequência central
        s21_aut_ref_fc = np.interp(fc_input, df_aut_ref["Freq_MHz"], df_aut_ref["S21_dB"])
        s21_ref_ref_fc = np.interp(fc_input, df_ref_ref["Freq_MHz"], df_ref_ref["S21_dB"])
        gain_aut_fc = gain_ref_input + (s21_aut_ref_fc - s21_ref_ref_fc)

        st.success(f"Ganho da antena sob teste em {fc_input:.1f} MHz: **{gain_aut_fc:.2f} dBi**")

        # Gráfico dos S21
        st.subheader("Visualização dos S21")
        fig1, ax1 = plt.subplots()
        ax1.plot(df_aut_ref["Freq_MHz"], df_aut_ref["S21_dB"], label="S21 Padrão/Testada", color='blue')
        ax1.plot(df_ref_ref["Freq_MHz"], df_ref_ref["S21_dB"], label="S21 Padrão/Padrão", color='green')
        ax1.axvline(fc_input, color='red', linestyle='--', label=f"Frequência Central: {fc_input} MHz")
        ax1.set_xlabel("Frequência (MHz)")
        ax1.set_ylabel("S21 (dB)")
        ax1.set_title("Coeficiente de Transmissão S21")
        ax1.legend()
        ax1.grid(True)
        st.pyplot(fig1)

        # Gráfico do ganho da antena sob teste
        st.subheader("📊 Ganho da Antena sob Teste vs Frequência")
        fig2, ax2 = plt.subplots()
        ax2.plot(freqs_common, gain_aut_freq, label="Ganho da AUT", color='purple')
        ax2.axvline(fc_input, color='red', linestyle='--', label=f"{fc_input} MHz")
        ax2.set_xlabel("Frequência (MHz)")
        ax2.set_ylabel("Ganho (dBi)")
        ax2.set_title("Ganho da Antena sob Teste")
        ax2.legend()
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
