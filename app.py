import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import calendar

# --- 1. KONFIGURASI DATA ---
SHEET_ID = '18Djb0QiE8uMgt_nXljFCZaMKHwii1pMzAtH96zGc_cI'
SHEET_NAME = 'app_data'
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}'

st.set_page_config(page_title="Helsa-BR Performance Dashboard", layout="wide")

# Mapping bulan Indonesia ke angka
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
            'Pintu Poli' # Data jumlah pintu poli per cabang
        ]
        for col in numeric_cols:
            if col in raw_df.columns:
                raw_df[col] = raw_df[col].astype(str).str.replace(r'[^\d]', '', regex=True)
                raw_df[col] = pd.to_numeric(raw_df[col], errors='coerce').fillna(0)
        return raw_df
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame()

# Fungsi hitung hari kerja (Senin-Jumat) dan Sabtu dalam sebulan
def count_days(year, month_name):
    month_idx = MONTH_MAP.get(month_name, 1)
    matrix = calendar.monthcalendar(year, month_idx)
    mon_fri = 0
    saturdays = 0
    for week in matrix:
        # Senin - Jumat (Index 0-4)
        for d in range(0, 5):
            if week[d] != 0: mon_fri += 1
        # Sabtu (Index 5)
        if week[5] != 0: saturdays += 1
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

    # --- PERHITUNGAN METRIK ---
    filtered_df['Total OPT'] = filtered_df['Volume OPT JKN'] + filtered_df['Volume OPT Non JKN']
    filtered_df['Total IPT'] = filtered_df['Volume IPT JKN'] + filtered_df['Volume IPT Non JKN']
    filtered_df['Total IGD'] = filtered_df['Volume IGD JKN'] + filtered_df['Volume IGD Non JKN']
    filtered_df['Total IGD to IPT'] = filtered_df['Volume IGD to IPT JKN'] + filtered_df['Volume IGD to IPT Non JKN']
    filtered_df['CR IGD to IPT'] = np.where(filtered_df['Total IGD'] > 0, (filtered_df['Total IGD to IPT'] / filtered_df['Total IGD']) * 100, 0)
    
    # PERHITUNGAN KAPASITAS (Tahun 2025)
    capacity_data = []
    for idx, row in filtered_df.iterrows():
        mf, sat = count_days(2025, row['Bulan'])
        pintu = row['Pintu Poli']
        # Poin 5: Max Cap Daily (Mon-Fri) = Pintu * 12 jam * 5 pts
        cap_mf = pintu * 12 * 5
        # Poin 6: Max Cap Daily (Sat) = Pintu * 4 jam * 5 pts
        cap_sat = pintu * 4 * 5
        # Poin 7: Max Cap Monthly
        monthly_cap = (mf * cap_mf) + (sat * cap_sat)
        capacity_data.append(monthly_cap)
    
    filtered_df['Kapasitas Maks'] = capacity_data
    # Poin 8 & Utilisasi: Volume OPT / Kapasitas
    filtered_df['Utilisasi Poli'] = np.where(filtered_df['Kapasitas Maks'] > 0, (filtered_df['Total OPT'] / filtered_df['Kapasitas Maks']) * 100, 0)

    for col in ['Actual Revenue (Total)', 'Total OPT', 'Total IPT', 'Total IGD', 'Total IGD to IPT']:
        filtered_df[f'{col}_Growth'] = filtered_df.groupby('Cabang')[col].pct_change() * 100

    st.title("📊 Dashboard Performa Helsa-BR 2025")
    
    colors = {
        'Jatirahayu': {'base': '#AEC6CF', 'light': '#D1E1E6', 'dark': '#779ECB'},
        'Cikampek':   {'base': '#FFB7B2', 'light': '#FFD1CF', 'dark': '#E08E88'},
        'Citeureup':  {'base': '#B2F2BB', 'light': '#D5F9DA', 'dark': '#88C090'},
        'Ciputat':    {'base': '#CFC1FF', 'light': '#E1D9FF', 'dark': '#A694FF'}
    }

    # FUNGSI UNIVERSAL STACKED BAR
    def create_stacked_chart(df_data, title, col_top, col_bottom, col_total, col_growth_name, y_label, is_revenue=False, target_col=None):
        with st.container(border=True):
            st.subheader(title)
            fig = go.Figure()
            for i, cabang in enumerate(selected_cabang):
                branch_df = df_data[df_data['Cabang'] == cabang].copy()
                if branch_df.empty: continue
                
                h_vals = branch_df[col_growth_name].fillna(0)
                a_vals = (branch_df[col_total] / branch_df[target_col] * 100).fillna(0) if target_col else np.zeros(len(branch_df))
                h_customdata = np.stack([branch_df[col_total], h_vals, a_vals], axis=-1)

                h_template = f"<b>{cabang}</b><br>Total: %{{customdata[0]:,}}<br>"
                if target_col: h_template += "Ach: %{customdata[2]:.1f}%<br>"
                h_template += "Growth: %{customdata[1]:.1f}%<extra></extra>"

                fig.add_trace(go.Bar(x=branch_df['Bulan'], y=branch_df[col_bottom], name=cabang, legendgroup=cabang, offsetgroup=cabang, marker_color=colors.get(cabang)['light'], customdata=h_customdata, textposition='inside', insidetextanchor='middle', textangle=0, hovertemplate=h_template))
                fig.add_trace(go.Bar(x=branch_df['Bulan'], y=branch_df[col_top], name=cabang, legendgroup=cabang, showlegend=False, base=branch_df[col_bottom], offsetgroup=cabang, marker_color=colors.get(cabang)['dark'], customdata=h_customdata, textposition='inside', insidetextanchor='middle', textangle=0, hovertemplate=h_template))
                
                labels = []
                for idx, g_val in enumerate(h_vals):
                    symbol = "▲" if g_val >= 0 else "▼"
                    g_txt = f"<span style='color:{('#059669' if g_val >= 0 else '#dc2626')}'><b>{symbol} {abs(g_val):.1f}%</b></span>"
                    if target_col:
                        ach = a_vals.iloc[idx]
                        ach_txt = f"<span style='color:{('#059669' if ach >= 100 else '#dc2626')}'><b>{ach:.1f}%</b></span>"
                        labels.append(f"{ach_txt}<br>{g_txt}")
                    else: labels.append(g_txt)
                fig.add_trace(go.Bar(x=branch_df['Bulan'], y=branch_df[col_total], offsetgroup=cabang, showlegend=False, text=labels, textposition='outside', textfont=dict(size=14), marker_color='rgba(0,0,0,0)', hoverinfo='skip', cliponaxis=False))

            max_v = df_data[col_total].max() if not df_data.empty else 0
            y_limit = max_v * 1.35 if max_v > 0 else 100
            yaxis_config = dict(title=y_label, range=[0, y_limit])
            if is_revenue:
                fig.update_yaxes(tickvals=np.arange(0, y_limit + 1e9, 1e9), ticktext=[f"{int(v/1e9)}M" for v in np.arange(0, y_limit + 1e9, 1e9)])
            fig.update_layout(barmode='group', height=520, margin=dict(t=120, b=10), yaxis=yaxis_config, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True)

    # --- EKSEKUSI GRAFIK UTAMA ---
    create_stacked_chart(filtered_df, "📈 Realisasi Revenue (Stacked Opt vs Ipt)", 'Actual Revenue (Ipt)', 'Actual Revenue (Opt)', 'Actual Revenue (Total)', 'Actual Revenue (Total)_Growth', "Revenue", is_revenue=True, target_col='Target Revenue')
    create_stacked_chart(filtered_df, "👥 Volume Outpatient (OPT)", 'Volume OPT JKN', 'Volume OPT Non JKN', 'Total OPT', 'Total OPT_Growth', "Volume OPT")
    
    # --- GRAFIK BARU: KAPASITAS PRODUKSI RAJAL ---
    with st.container(border=True):
        st.subheader("⚙️ Analisis Kapasitas Produksi Rawat Jalan")
        fig_cap = go.Figure()
        for cb in selected_cabang:
            branch_df = filtered_df[filtered_df['Cabang'] == cb]
            if branch_df.empty: continue
            
            # Bar: Kapasitas Maks
            fig_cap.add_trace(go.Bar(
                x=branch_df['Bulan'], y=branch_df['Kapasitas Maks'],
                name=f"Kapasitas {cb}", offsetgroup=cb,
                marker_color=colors.get(cb)['light'],
                text=branch_df['Utilisasi Poli'].apply(lambda x: f"<b>{x:.1f}%</b><br>Util"),
                textposition='inside', textfont=dict(size=10, color='#444444'),
                hovertemplate=f"<b>{cb} Kapasitas</b>: %{{y:,.0f}} Pasien<extra></extra>"
            ))
            # Line: Volume Aktual
            fig_cap.add_trace(go.Scatter(
                x=branch_df['Bulan'], y=branch_df['Total OPT'],
                name=f"Volume {cb}", mode='lines+markers+text',
                line=dict(color=colors.get(cb)['dark'], width=3),
                text=branch_df['Total OPT'].apply(lambda x: f"{int(x):,}"),
                textposition="top center",
                hovertemplate=f"<b>{cb} Volume</b>: %{{y:,.0f}} Pasien<extra></extra>"
            ))
        
        fig_cap.update_layout(
            barmode='group', height=500, margin=dict(t=80, b=10),
            yaxis=dict(title="Jumlah Pasien", range=[0, filtered_df['Kapasitas Maks'].max() * 1.3 if not filtered_df.empty else 1000]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_cap, use_container_width=True)

    create_stacked_chart(filtered_df, "🏥 Volume Inpatient (Ranap)", 'Volume IPT JKN', 'Volume IPT Non JKN', 'Total IPT', 'Total IPT_Growth', "Volume IPT")
    create_stacked_chart(filtered_df, "🚑 Volume IGD", 'Volume IGD JKN', 'Volume IGD Non JKN', 'Total IGD', 'Total IGD_Growth', "Volume IGD")
    create_stacked_chart(filtered_df, "🎯 Volume Konversi IGD ke Rawat Inap (Ranap)", 'Volume IGD to IPT JKN', 'Volume IGD to IPT Non JKN', 'Total IGD to IPT', 'Total IGD to IPT_Growth', "Volume Konversi")

    with st.expander("🔍 Lihat Detail Data Mentah"):
        st.dataframe(filtered_df)
else:
    st.warning("Data tidak tersedia.")
