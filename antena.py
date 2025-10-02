import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import StringIO

st.title("Cálculo de Ganho de Antenas")

# Entrada do ganho da antena de referência
gain_ref = st.number_input("Ganho da antena de referência (dBi)", value=6.24)

# Frequência central
fc_input = st.number_input("Frequência central (MHz)", value=900.0)

# Upload dos arquivos
uploaded_file_aut_ref = st.file_uploader("Carregue o arquivo AUT-REF (.csv ou .result)", type=["csv", "result"])
uploaded_file_ref_ref = st.file_uploader("Carregue o arquivo REF-REF (.csv ou .result)", type=["csv", "result"])

# Checkbox para sinalizar unidade da frequência nos arquivos
freq_em_mhz = st.checkbox("Os dados de frequência já estão em MHz?")

def carregar_dados(uploaded_file):
    if uploaded_file is None:
        return None

    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
        if "Freq" in df.columns and "Amplitude" in df.columns:
            df = df.rename(columns={"Freq": "Freq_Hz", "Amplitude": "Amplitude_dB"})
        else:
            st.error("CSV deve ter colunas 'Freq' e 'Amplitude'")
            return None

    elif uploaded_file.name.endswith(".result"):
        lines = uploaded_file.getvalue().decode("latin1").splitlines()
        freq = []
        amp = []
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 3:
                try:
                    f = float(parts[0])
                    a = float(parts[2])
                    freq.append(f)
                    amp.append(a)
                except ValueError:
                    continue
        df = pd.DataFrame({"Freq_Hz": freq, "Amplitude_dB": amp})
    else:
        st.error("Formato não suportado")
        return None

    # Ajuste de unidade
    if freq_em_mhz:
        df["Freq_MHz"] = df["Freq_Hz"].astype(float)  # já está em MHz
    else:
        df["Freq_MHz"] = df["Freq_Hz"].astype(float) / 1e6  # estava em Hz

    return df

if uploaded_file_aut_ref and uploaded_file_ref_ref:
    df_aut_ref = carregar_dados(uploaded_file_aut_ref)
    df_ref_ref = carregar_dados(uploaded_file_ref_ref)

    if df_aut_ref is not None and df_ref_ref is not None:
        # Interpolação para frequência central
        s21_aut_ref_fc = np.interp(fc_input, df_aut_ref["Freq_MHz"], df_aut_ref["Amplitude_dB"])
        s21_ref_ref_fc = np.interp(fc_input, df_ref_ref["Freq_MHz"], df_ref_ref["Amplitude_dB"])

        ganho_fc = gain_ref + (s21_aut_ref_fc - s21_ref_ref_fc)

        st.subheader("Resultados")
        st.write(f"Ganho na frequência central ({fc_input:.2f} MHz): **{ganho_fc:.2f} dBi**")

        # Plot comparativo
        plt.figure(figsize=(10, 5))
        plt.plot(df_aut_ref["Freq_MHz"], df_aut_ref["Amplitude_dB"], label="AUT-REF")
        plt.plot(df_ref_ref["Freq_MHz"], df_ref_ref["Amplitude_dB"], label="REF-REF")
        plt.axvline(fc_input, color="red", linestyle="--", label=f"fc = {fc_input:.2f} MHz")
        plt.xlabel("Frequência (MHz)")
        plt.ylabel("S21 (dB)")
        plt.title("Medições S21")
        plt.legend()
        st.pyplot(plt)

        # Tabela comparativa
        st.subheader("Pré-visualização dos dados")
        st.write("AUT-REF")
        st.dataframe(df_aut_ref.head())
        st.write("REF-REF")
        st.dataframe(df_ref_ref.head())
