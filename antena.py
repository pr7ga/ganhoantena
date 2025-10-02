import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.title("Cálculo de Ganho de Antena pelo Método da Substituição")

# Upload dos arquivos
file_aut_ref = st.file_uploader("Carregue o arquivo AUT-REF (.result ou .csv)", type=["result", "csv"])
file_ref_ref = st.file_uploader("Carregue o arquivo REF-REF (.result ou .csv)", type=["result", "csv"])

# Ganho da antena de referência
gain_ref_input = st.number_input("Ganho da antena de referência (dBi)", value=6.24)

# Frequência central
fc_input = st.number_input("Frequência central (MHz)", value=900.0)

def load_result_file(uploaded_file):
    """Carrega arquivos .result ou .csv de forma robusta"""
    if uploaded_file is None:
        return None
    
    # Detecta se tem cabeçalho
    try:
        df = pd.read_csv(uploaded_file, sep=None, engine="python")
        if df.shape[1] < 2:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, sep=None, engine="python", header=None)
    except Exception:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, sep=None, engine="python", header=None)

    # Renomear colunas dependendo do número detectado
    if df.shape[1] >= 7:
        df.columns = ["Freq_Hz", "Unused", "Amplitude_dB", "Azimuth", "Pol", "Elevation", "Timestamp"]
    elif df.shape[1] >= 2:
        df.columns = ["Freq_Hz", "Amplitude_dB"] + [f"extra{i}" for i in range(df.shape[1]-2)]
    else:
        raise ValueError("Arquivo com número insuficiente de colunas.")

    # Converter frequência para MHz
    if df["Freq_Hz"].max() > 1e6:
        df["Freq_MHz"] = df["Freq_Hz"] / 1e6
    else:
        df["Freq_MHz"] = df["Freq_Hz"]

    return df[["Freq_MHz", "Amplitude_dB"]]

if file_aut_ref and file_ref_ref:
    try:
        df_aut_ref = load_result_file(file_aut_ref)
        df_ref_ref = load_result_file(file_ref_ref)

        # Frequência comum interpolada (faixa sobreposta dos dois arquivos)
        freqs_common = np.linspace(
            max(df_aut_ref["Freq_MHz"].min(), df_ref_ref["Freq_MHz"].min()),
            min(df_aut_ref["Freq_MHz"].max(), df_ref_ref["Freq_MHz"].max()),
            1000
        )

        # Interpolação dos S21
        s21_aut_ref_interp = np.interp(freqs_common, df_aut_ref["Freq_MHz"], df_aut_ref["Amplitude_dB"])
        s21_ref_ref_interp = np.interp(freqs_common, df_ref_ref["Freq_MHz"], df_ref_ref["Amplitude_dB"])

        # Cálculo do ganho ao longo da faixa
        gain_aut_freq = gain_ref_input + (s21_aut_ref_interp - s21_ref_ref_interp)

        df_gain = pd.DataFrame({
            "Frequência (MHz)": freqs_common,
            "Ganho da Antena sob Teste (dBi)": gain_aut_freq
        })

        # Ganho interpolado na frequência central
        if (fc_input >= freqs_common.min()) and (fc_input <= freqs_common.max()):
            s21_aut_ref_fc = np.interp(fc_input, df_aut_ref["Freq_MHz"], df_aut_ref["Amplitude_dB"])
            s21_ref_ref_fc = np.interp(fc_input, df_ref_ref["Freq_MHz"], df_ref_ref["Amplitude_dB"])
            gain_aut_fc = gain_ref_input + (s21_aut_ref_fc - s21_ref_ref_fc)
        else:
            gain_aut_fc = None
            st.warning("⚠️ Frequência central fora da faixa dos dados medidos.")

        # Exibir tabela
        st.subheader("Tabela de Ganho Calculado")
        st.dataframe(df_gain)

        # Exibir ganho na frequência central
        if gain_aut_fc is not None:
            st.success(f"Ganho da antena sob teste em {fc_input:.2f} MHz = {gain_aut_fc:.2f} dBi")

        # Plot
        fig, ax = plt.subplots()
        ax.plot(df_gain["Frequência (MHz)"], df_gain["Ganho da Antena sob Teste (dBi)"], label="Ganho AUT")
        ax.axvline(fc_input, color="red", linestyle="--", label=f"{fc_input:.1f} MHz")
        ax.set_xlabel("Frequência (MHz)")
        ax.set_ylabel("Ganho (dBi)")
        ax.legend()
        ax.grid(True)
        st.pyplot(fig)

    except Exception as e:
        st.error(f"Ocorreu um erro ao processar os arquivos: {e}")
