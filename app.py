import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import calendar

# --- 1. KONFIGURASI DATA ---
SHEET_ID = '18Djb0QiE8uMgt_nXljFCZaMKHwii1pMzAtH96zGc_cI'
SHEET_NAME = 'app_data'
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}'

st.set_page_config(page_title="Helsa-BR Performance Dashboard 2025", layout="wide")

MONTH_MAP = {
    'Januari': 1, 'Februari': 2, 'Maret': 3, 'April': 4, 'Mei': 5, 'Juni': 6,
    'Juli': 7, 'Agustus': 8, 'September': 9, 'Oktober': 10, 'November': 11, 'Desember': 12
}

@st.cache_data(ttl=300)
def load_data():
    try:
        raw_df = pd.read_csv(URL)
        raw_df.columns = raw_df.columns.str.strip()
        numeric_cols = [
            'Target Revenue', 'Actual Revenue (Total)', 'Actual Revenue (Opt)', 'Actual Revenue (Ipt)',
            'Volume OPT JKN', 'Volume OPT Non JKN', 'Volume IPT JKN', 'Volume IPT Non JKN',
            'Volume IGD JKN', 'Volume IGD Non JKN', 'Volume IGD to IPT JKN', 'Volume IGD to IPT Non JKN',
            'Pintu Poli'
        ]
        for col in numeric_cols:
            if col in raw_df.columns:
                # PERBAIKAN REGEX: Memperbolehkan titik desimal agar 20.0 tidak menjadi 200
                raw_df[col] = raw_df[col].astype(str).str.replace(r'[^\d.]', '', regex=True)
                raw_df[col] = pd.to_numeric(raw_df[col], errors='coerce').fillna(0)
            elif col == 'Pintu Poli':
                raw_df[col] = 0
        return raw_df
    except Exception as e:
        st.error(f"Gagal memuat data: {e}")
        return pd.DataFrame()

# Fungsi hitung hari kerja (Senin-Jumat) dan Sabtu dalam sebulan (Tahun 2025)
def count_days(year, month_name):
    month_idx = MONTH_MAP.get(month_name, 1)
    matrix = calendar.monthcalendar(year, month_idx)
    mon_fri, saturdays = 0, 0
    for week in matrix:
        for d in range(0, 5): # Senin - Jumat
            if week[d] != 0: mon_fri += 1
        if week[5] != 0: saturdays += 1 # Sabtu
    return mon_fri, saturdays

df = load_data()

if not df.empty:
    # --- SIDEBAR FILTER ---
    st.sidebar.header("🕹️ Panel Kontrol")
    all_cabang = list(df['Cabang'].unique())
    selected_cabang = st.sidebar.multiselect("Pilih Cabang:", all_cabang, default=all_cabang)
    
    month_order = list(MONTH_MAP.keys())
    available_months = [m for m in month_order if m in df['Bulan'].unique()]
    selected_months = st.sidebar.multiselect("Pilih Periode Bulan:", available_months, default=available_months)
    
    filtered_df = df[(df['Cabang'].isin(selected_cabang)) & (df['Bulan'].isin(selected_months))].copy()
    filtered_df['Bulan'] = pd.Categorical(filtered_df['Bulan'], categories=selected_months, ordered=True)
    filtered_df = filtered_df.sort_values(['Cabang', 'Bulan'])

    # --- PERHITUNGAN METRIK & KAPASITAS ---
    filtered_df['Total OPT'] = filtered_df['Volume OPT JKN'] + filtered_df['Volume OPT Non JKN']
    filtered_df['Total IPT'] = filtered_df['Volume IPT JKN'] + filtered_df['Volume IPT Non JKN']
    filtered_df['Total IGD'] = filtered_df['Volume IGD JKN'] + filtered_df['Volume IGD Non JKN']
    filtered_df['Total IGD to IPT'] = filtered_df['Volume IGD to IPT JKN'] + filtered_df['Volume IGD to IPT Non JKN']
    filtered_df['CR IGD to IPT'] = np.where(filtered_df['Total IGD'] > 0, (filtered_df['Total IGD to IPT'] / filtered_df['Total IGD']) * 100, 0)
    
    # Kapasitas Rajal menggunakan kalender 2025
    capacity_data = []
    for _, row in filtered_df.iterrows():
        mf, sat = count_days(2025, row['Bulan']) # TAHUN DISESUAIKAN KE 2025
        pintu = row['Pintu Poli']
        # Perhitungan Poin 7: (MF * Pintu * 12 * 5) + (SAT * Pintu * 4 * 5)
        monthly_cap = (mf * (pintu * 12 * 5)) + (sat * (pintu * 4 * 5))
        capacity_data.append(monthly_cap)
    
    filtered_df['Kapasitas Maks'] = capacity_data
    filtered_df['Utilisasi Poli'] = np.where(filtered_df['Kapasitas Maks'] > 0, (filtered_df['Total OPT'] / filtered_df['Kapasitas Maks']) * 100, 0)

    for col in ['Actual Revenue (Total)', 'Total OPT', 'Total IPT', 'Total IGD', 'Total IGD to IPT']:
        filtered_df[f'{col}_Growth'] = filtered_df.groupby('Cabang', observed=True)[col].pct_change() * 100

    st.title("📊 Dashboard Performa Helsa-BR 2025")
    
    colors = {
        'Jatirahayu': {'base': '#AEC6CF', 'light': '#D1E1E6', 'dark': '#779ECB'},
        'Cikampek':   {'base': '#FFB7B2', 'light': '#FFD1CF', 'dark': '#E08E88'},
        'Citeureup':  {'base': '#B2F2BB', 'light': '#D5F9DA', 'dark': '#88C090'},
        'Ciputat':    {'base': '#CFC1FF', 'light': '#E1D9FF', 'dark': '#A694FF'}
    }

    def create_stacked_chart(df_data, title, col_top, col_bottom, col_total, col_growth_name, y_label, is_revenue=False, target_col=None):
        with st.container(border=True):
            st.subheader(title)
            fig = go.Figure()
            for cb in selected_cabang:
                branch_df = df_data[df_data['Cabang'] == cb].copy()
                if branch_df.empty: continue
                
                def fmt_txt(val, cat):
                    if val == 0: return ""
                    val_str = f"{val/1e9:.2f}M" if is_revenue else f"{int(val):,}"
                    return f"<b>{val_str}</b><br>({cat})"

                fig.add_trace(go.Bar(x=branch_df['Bulan'], y=branch_df[col_bottom], name=cb, legendgroup=cb, offsetgroup=cb, marker_color=colors.get(cb)['light'], text=branch_df[col_bottom].apply(lambda x: fmt_txt(x, "Opt" if is_revenue else "Non JKN")), textposition='inside', textangle=0, textfont=dict(size=9, color='#444444')))
                fig.add_trace(go.Bar(x=branch_df['Bulan'], y=branch_df[col_top], name=cb, legendgroup=cb, showlegend=False, base=branch_df[col_bottom], offsetgroup=cb, marker_color=colors.get(cb)['dark'], text=branch_df[col_top].apply(lambda x: fmt_txt(x, "Ipt" if is_revenue else "JKN")), textposition='inside', textangle=0, textfont=dict(color='white', size=9)))
                
                display_labels = []
                for idx, g_val in enumerate(branch_df[col_growth_name]):
                    symbol = "▲" if g_val >= 0 else "▼"
                    g_color = "#059669" if g_val >= 0 else "#dc2626"
                    g_txt = f"<span style='color:{g_color}'><b>{symbol} {abs(g_val):.1f}%</b></span>"
                    if target_col and target_col in branch_df:
                        ach = (branch_df[col_total].iloc[idx] / branch_df[target_col].iloc[idx] * 1
