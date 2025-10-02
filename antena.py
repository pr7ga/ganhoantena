import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

st.title("📡 Cálculo de Ganho de Antenas")

# ------------------------------
# Função para carregar e tratar dados (.csv ou .result)
# ------------------------------
def carregar_dados(uploaded_file):
    nome_arquivo = uploaded_file.name.lower()

    def tentar_ler(encoding, sep=None, names=None, skiprows=None):
        uploaded_file.seek(0)  # reset ponteiro
        return pd.read_csv(uploaded_file, encoding=encoding, sep=sep, names=names, skiprows=skiprows)

    try:
        if nome_arquivo.endswith(".csv"):
            colunas = ["Freq_Hz", "S21_dB", "Unused"]
            df = tentar_ler("utf-8-sig", sep=",", names=colunas, skiprows=3)
            df["Freq_Hz"] = df["Freq_Hz"].astype(str).str.replace('+', '', regex=False).str.strip().astype(float)
            df["S21_dB"] = df["S21_dB"].astype(str).str.replace('+', '', regex=False).str.strip().astype(float)
            df["Freq_MHz"] = df["Freq_Hz"] / 1e6
            df = df[["Freq_MHz", "S21_dB"]].rename(columns={"S21_dB": "Amplitude_dB"})

        elif nome_arquivo.endswith(".result"):
            colunas = ["Freq_Hz", "Unused", "Amplitude_dB", "Azim", "Pol", "Elev", "Timestamp"]
            try:
                df = tentar_ler("utf-8-sig", sep="\s+", names=colunas)
            except Exception:
                try:
                    df = tentar_ler("latin1", sep="\s+", names=colunas)
                except Exception:
                    df = tentar_ler("utf-16", sep="\s+", names=colunas)

            df = df[["Freq_Hz", "Amplitude_dB"]].copy()
            df["Freq_MHz"] = df["Freq_Hz"] / 1e6
            df = df[["Freq_MHz", "Amplitude_dB"]]

        else:
            raise ValueError("Formato de arquivo não suportado. Use .csv ou .result")

    except Exception as e:
        st.error(f"Erro ao processar o arquivo {uploaded_file.name}: {e}")
        return None

    return df


# ------------------------------
# Upload dos arquivos
# ------------------------------
uploaded_aut_ref = st.file_uploader("📁 Arquivo (.csv ou .result) - S21 entre AUT e referência", type=["csv", "result"])
uploaded_ref_ref = st.file_uploader("📁 Arquivo (.csv ou .result) - S21 entre duas referências", type=["csv", "result"])

ganho_ref = st.number_input("📌 Ganho conhecido da antena de referência (dBi)", value=2.15)

# ------------------------------
# Processamento e cálculo do ganho
# ------------------------------
if uploaded_aut_ref and uploaded_ref_ref:
    df_aut_ref = carregar_dados(uploaded_aut_ref)
    df_ref_ref = carregar_dados(uploaded_ref_ref)

    if df_aut_ref is not None and df_ref_ref is not None:
        # Garantir alinhamento por frequência
        df = pd.merge(df_aut_ref, df_ref_ref, on="Freq_MHz", suffixes=("_AUT_REF", "_REF_REF"))

        # Cálculo do ganho da AUT
        df["Ganho_AUT_dBi"] = (df["Amplitude_dB_AUT_REF"] - df["Amplitude_dB_REF_REF"]) + ganho_ref

        # ------------------------------
        # Gráfico
        # ------------------------------
        fig, ax = plt.subplots(figsize=(8,5))
        ax.plot(df["Freq_MHz"], df["Ganho_AUT_dBi"], color="blue", lw=2)

        ax.set_xlabel("Frequência (MHz)")
        ax.set_ylabel("Ganho da AUT (dBi)")
        ax.set_title("📊 Ganho da Antena sob Teste")

        # Grade e legenda
        ax.grid(True, which="both", ls="--", lw=0.7)
        legend_elements = [Line2D([0], [0], color="blue", lw=2, label="Ganho AUT (calculado)")]
        ax.legend(handles=legend_elements, loc="best")

        st.pyplot(fig)

        # ------------------------------
        # Exibir tabela
        # ------------------------------
        st.subheader("📋 Resultados Numéricos")
        st.dataframe(df[["Freq_MHz", "Ganho_AUT_dBi"]])

        # ------------------------------
        # Opção de download
        # ------------------------------
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Baixar resultados em CSV", data=csv, file_name="ganho_aut.csv", mime="text/csv")
