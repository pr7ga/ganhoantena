import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import re
import csv

st.set_page_config(page_title="Ganho da Antena sob Teste", layout="centered")
st.title("📡 Cálculo do Ganho")
st.markdown("Baseado nos coeficientes de transmissão medidos entre duas antenas iguais, com ganho conhecido (antenas padrão) e a antena sob teste.")

# --- Helpers ---
def safe_float(s):
    """Tenta extrair um float de uma string, lidando com +, vírgulas, unidades anexadas, etc."""
    if s is None:
        return None
    s = str(s).strip()
    if s == "":
        return None
    s = s.replace('+', '')
    s = s.replace('\xa0', '')
    s = s.replace(' ', '')
    s = s.replace(',', '.')  # vírgula decimal -> ponto
    # tenta conversão direta
    try:
        return float(s)
    except:
        # tenta extrair via regex um número (ex: "1.23e9Hz" -> 1.23e9)
        m = re.search(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', s)
        if m:
            try:
                return float(m.group(0))
            except:
                return None
        return None

def detect_delimiter(sample_text):
    """Tenta detectar delimitador usando csv.Sniffer; fallback para , ; \t ou whitespace"""
    try:
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample_text[:4096])
        delim = dialect.delimiter
        return delim
    except Exception:
        if ',' in sample_text:
            return ','
        if ';' in sample_text:
            return ';'
        if '\t' in sample_text:
            return '\t'
        return None

def parse_csv_text(text):
    """Extrai pares (freq, amplitude) de um conteúdo CSV/semelhante a CSV."""
    lines = [ln for ln in text.splitlines() if ln.strip() != ""]
    if not lines:
        return [], []

    sample = "\n".join(lines[:20])
    delim = detect_delimiter(sample)

    # Se detectamos um delimitador, procuramos a primeira linha que contenha um número na coluna 0
    if delim:
        # procura a primeira linha que pareça conter dados (coluna 0 numérica)
        start = None
        for i, ln in enumerate(lines[:50]):  # limita busca
            tokens = [t.strip() for t in ln.split(delim)]
            if len(tokens) >= 2 and safe_float(tokens[0]) is not None:
                start = i
                break
        if start is None:
            start = 0

        # tenta ler com pandas a partir dessa linha
        chunk = "\n".join(lines[start:])
        try:
            df_try = pd.read_csv(io.StringIO(chunk), sep=delim, header=None, engine='python', skipinitialspace=True)
        except Exception:
            # fallback manual
            df_try = None

        if df_try is not None:
            # heurística: coluna 0 é frequência; amplitude é a coluna entre 1..4 que tem mais valores numéricos plausíveis
            freqs = []
            amps = []
            # identifica melhor coluna de amplitude
            cand_cols = []
            ncols = df_try.shape[1]
            for col in range(1, min(ncols, 6)):
                vals = df_try.iloc[:, col].astype(str).apply(lambda x: safe_float(x) is not None)
                cand_cols.append((col, vals.mean()))
            if cand_cols:
                amp_col = sorted(cand_cols, key=lambda x: x[1], reverse=True)[0][0]
            else:
                amp_col = 1 if ncols > 1 else 0

            for _, row in df_try.iterrows():
                f = safe_float(row.iloc[0])
                a = safe_float(row.iloc[amp_col]) if amp_col < len(row) else None
                if (f is not None) and (a is not None):
                    freqs.append(f)
                    amps.append(a)
            return freqs, amps

    # Se não detectou delimiter / ou parsing falhou: tenta parsing por whitespace/colunas fixas
    freqs = []
    amps = []
    for ln in lines:
        parts = re.split(r'\s+', ln.strip())
        if len(parts) >= 2:
            f = safe_float(parts[0])
            a = safe_float(parts[1])
            if f is not None and a is not None:
                freqs.append(f)
                amps.append(a)
                continue
        # tentativa alternativa: split por vírgula
        parts = [p.strip() for p in ln.split(',')]
        if len(parts) >= 2:
            f = safe_float(parts[0])
            a = safe_float(parts[1])
            if f is not None and a is not None:
                freqs.append(f)
                amps.append(a)
                continue
    return freqs, amps

# --- Função unificada e robusta para CSV ou RESULT ---
def carregar_dados(uploaded_file):
    """
    Lê .csv ou .result com tentativas de repair:
    - tenta vários encodings
    - detecta delimitador para CSV
    - extrai apenas linhas que contenham números
    Retorna DataFrame com colunas: Freq_MHz, Amplitude_dB
    """
    nome_arquivo = uploaded_file.name.lower()
    # lê bytes e tenta decodificar com vários encodings
    uploaded_file.seek(0)
    raw = uploaded_file.read()
    encodings_to_try = ["utf-8-sig", "utf-8", "utf-16", "latin1", "cp1252"]
    text = None
    for enc in encodings_to_try:
        try:
            text = raw.decode(enc)
            break
        except Exception:
            continue
    if text is None:
        raise UnicodeDecodeError("Não foi possível decodificar o arquivo com encodings comuns (utf-8/utf-16/latin1).")

    # Remove linhas de comentário que comecem com # ou ! (heurística)
    # Não removemos tudo — parseadores abaixo ignoram.
    # Branch por extensão
    freqs = []
    amps = []

    if nome_arquivo.endswith(".result"):
        # .result: formato com 7 colunas fixas (freq, unused, amplitude, azim, pol, elev, timestamp)
        # vamos iterar linhas, pegar col0 e col2 quando possível
        for ln in text.splitlines():
            ln = ln.strip()
            if ln == "":
                continue
            parts = re.split(r'\s+', ln)
            if len(parts) >= 7:
                f = safe_float(parts[0])
                a = safe_float(parts[2])
                if f is not None and a is not None:
                    freqs.append(f)
                    amps.append(a)
            else:
                # se houver linhas com outro formato, tentamos extrair dois primeiros numeros
                nums = re.findall(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', ln.replace(',', '.'))
                if len(nums) >= 2:
                    f = safe_float(nums[0])
                    a = safe_float(nums[1])
                    if f is not None and a is not None:
                        freqs.append(f)
                        amps.append(a)

    else:
        # assume csv-like
        freqs, amps = parse_csv_text(text)

    # validação
    if len(freqs) == 0:
        raise ValueError("Não foram encontrados pares frequência/amplitude no arquivo. Verifique o formato do arquivo ou envie um exemplo.")

    # cria DataFrame, converte para MHz e ordena
    df = pd.DataFrame({"Freq_Hz": freqs, "Amplitude_dB": amps})
    df = df.dropna().copy()

    # Aqui: se existir a variável global freq_em_mhz e ela for True, NÃO dividir por 1e6
    # Isso atende a opção do usuário para arquivos .result que já estão em MHz
    if 'freq_em_mhz' in globals() and freq_em_mhz and nome_arquivo.endswith(".result"):
        df["Freq_MHz"] = df["Freq_Hz"].astype(float)
    else:
        df["Freq_MHz"] = df["Freq_Hz"].astype(float) / 1e6

    df = df[["Freq_MHz", "Amplitude_dB"]]
    df = df.sort_values("Freq_MHz").reset_index(drop=True)
    return df

# --- Layout / Inputs (mantidos) ---
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

# --------------------
# NOVA OPÇÃO (apenas adicionada): checkbox para indicar que arquivos .result já têm frequência em MHz
# --------------------
freq_em_mhz = st.checkbox("Arquivos .result já estão em MHz (não dividir por 1e6)")

uploaded_aut_ref = st.file_uploader("📁 Arquivo (.csv ou .result) com S21 entre padrão e antena sob teste", type=["csv", "result"])
uploaded_ref_ref = st.file_uploader("📁 Arquivo (.csv ou .result) com S21 entre duas antenas padrão", type=["csv", "result"])

if uploaded_aut_ref and uploaded_ref_ref:
    try:
        df_aut_ref = carregar_dados(uploaded_aut_ref)
        df_ref_ref = carregar_dados(uploaded_ref_ref)

        # small preview to help debugging
        st.subheader("Preview (AUT vs REF) — primeiras 5 linhas")
        colA, colB = st.columns(2)
        with colA:
            st.write("AUT (primeiras 5 linhas)")
            st.dataframe(df_aut_ref.head())
        with colB:
            st.write("REF (primeiras 5 linhas)")
            st.dataframe(df_ref_ref.head())

        # Interpolação para a mesma base de frequências
        freqs_common = df_aut_ref["Freq_MHz"].values
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

        # (restante do app: equação, gráficos, downloads — mantenha o que já tinha)
        st.markdown(
            f"<h2 style='text-align: center; color: green;'>📈 Ganho da {aut_nome} em {fc_input:.1f} MHz: <strong>{gain_aut_fc:.2f} dBi</strong></h2>",
            unsafe_allow_html=True
        )

        # Gráfico dos S21
        fig1, ax1 = plt.subplots()
        ax1.plot(df_aut_ref["Freq_MHz"], df_aut_ref["Amplitude_dB"], label="S21 AUT/REF", color='blue')
        ax1.plot(df_ref_ref["Freq_MHz"], df_ref_ref["Amplitude_dB"], label="S21 REF/REF", color='green')
        ax1.axvline(fc_input, color='red', linestyle='--', label=f"Centro {fc_input} MHz")
        ax1.set_xlabel("Frequência (MHz)")
        ax1.set_ylabel("S21 (dB)")
        ax1.legend(fontsize=9)
        ax1.grid(True)
        st.pyplot(fig1)

        # Gráfico do ganho
        fig2, ax2 = plt.subplots()
        ax2.plot(freqs_common, gain_aut_freq, label=f"Ganho @ {fc_input:.1f} MHz", color='purple')
        ax2.axvline(fc_input, color='red', linestyle='--')
        ax2.set_xlabel("Frequência (MHz)")
        ax2.set_ylabel("Ganho (dBi)")
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
