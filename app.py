import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# --- 1. KONFIGURASI DATA ---
SHEET_ID = '18Djb0QiE8uMgt_nXljFCZaMKHwii1pMzAtH96zGc_cI'
SHEET_NAME = 'app_data'
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}'

st.set_page_config(page_title="Helsa-BR Live Dashboard", layout="wide")

@st.cache_data(ttl=300)
def load_data():
    try:
        raw_df = pd.read_csv(URL)
        raw_df.columns = raw_df.columns.str.strip()
        numeric_cols = [
            'Target Revenue', 'Actual Revenue (Total)', 
            'Volume OPT JKN', 'Volume OPT Non JKN',
            'Volume IPT JKN', 'Volume IPT Non JKN',
            'Volume IGD JKN', 'Volume IGD Non JKN'
        ]
        for col in numeric_cols:
            if col in raw_df.columns:
                raw_df[col] = raw_df[col].astype(str).str.replace(r'[^\d]', '', regex=True)
                raw_df[col] = pd.to_numeric(raw_df[col], errors='coerce').fillna(0)
        return raw_df
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame()

df = load_data()

if not df.empty:
    st.sidebar.header("🕹️ Filter Panel")
    all_cabang = df['Cabang'].unique()
    selected_cabang = st.sidebar.multiselect("Pilih Cabang:", all_cabang, default=all_cabang)
    
    month_order = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 
                   'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
    filtered_df = df[df['Cabang'].isin(selected_cabang)].copy()
    filtered_df['Bulan'] = pd.Categorical(filtered_df['Bulan'], categories=month_order, ordered=True)
    filtered_df = filtered_df.sort_values(['Cabang', 'Bulan'])

    # Kalkulasi Total & Growth
    filtered_df['Total OPT'] = filtered_df['Volume OPT JKN'] + filtered_df['Volume OPT Non JKN']
    filtered_df['Total IPT'] = filtered_df['Volume IPT JKN'] + filtered_df['Volume IPT Non JKN']
    filtered_df['Total IGD'] = filtered_df['Volume IGD JKN'] + filtered_df['Volume IGD Non JKN']
    
    for cat in ['Actual Revenue (Total)', 'Total OPT', 'Total IPT', 'Total IGD']:
        filtered_df[f'{cat}_Growth'] = filtered_df.groupby('Cabang')[cat].pct_change() * 100

    st.title("📊 Dashboard Performa Helsa-BR")
    
    colors = {
        'Jatirahayu': {'base': '#AEC6CF', 'light': '#D1E1E6', 'dark': '#779ECB'},
        'Cikampek':   {'base': '#FFB7B2', 'light': '#FFD1CF', 'dark': '#E08E88'},
        'Citeureup':  {'base': '#B2F2BB', 'light': '#D5F9DA', 'dark': '#88C090'},
        'Ciputat':    {'base': '#CFC1FF', 'light': '#E1D9FF', 'dark': '#A694FF'}
    }

    # FUNGSI STACKED CHART DENGAN HOVER FIX
    def create_stacked_chart(df_data, title, col_jkn, col_nonjkn, col_total, col_growth, y_label):
        with st.container(border=True):
            st.subheader(title)
            fig = go.Figure()
            for i, cabang in enumerate(selected_cabang):
                branch_df = df_data[df_data['Cabang'] == cabang].copy()
                
                # NUCLEAR OPTION: Gunakan customdata untuk semua angka hover
                # Index 0: Nilai Segmen (JKN/Non), Index 1: Nilai Total
                cd_nonjkn = np.stack([branch_df[col_nonjkn], branch_df[col_total]], axis=-1)
                cd_jkn = np.stack([branch_df[col_jkn], branch_df[col_total]], axis=-1)

                # Trace 1: Non JKN (Light)
                fig.add_trace(go.Bar(
                    x=branch_df['Bulan'], y=branch_df[col_nonjkn], name=cabang, legendgroup=cabang,
                    offsetgroup=cabang, marker_color=colors.get(cabang)['light'],
                    customdata=cd_nonjkn,
                    text=branch_df[col_nonjkn].apply(lambda x: f"{int(x):,}" if x > 0 else ""),
                    textposition='inside', insidetextanchor='middle', textfont=dict(size=10, color='#444444'),
                    hovertemplate=f"<b>{cabang} (Non JKN)</b>: %{{customdata[0]:,}} Pasien<br>Total: %{{customdata[1]:,}} Pasien<extra></extra>"
                ))
                
                # Trace 2: JKN (Dark)
                fig.add_trace(go.Bar(
                    x=branch_df['Bulan'], y=branch_df[col_jkn], name=cabang, legendgroup=cabang, showlegend=False,
                    base=branch_df[col_nonjkn], offsetgroup=cabang, marker_color=colors.get(cabang)['dark'],
                    customdata=cd_jkn,
                    text=branch_df[col_jkn].apply(lambda x: f"{int(x):,}" if x > 0 else ""),
                    textposition='inside', insidetextanchor='middle', textfont=dict(color='white', size=10),
                    # FIX: Memanggil data segmen murni dari customdata[0]
                    hovertemplate=f"<b>{cabang} (JKN)</b>: %{{customdata[0]:,}} Pasien<br>Total: %{{customdata[1]:,}} Pasien<extra></extra>"
                ))
                
                # Trace 3: Growth Label (Transparent)
                g_vals = branch_df[col_growth + '_Growth'] if col_growth + '_Growth' in branch_df else branch_df[col_growth]
                g_labels = [f"<b>{'▲' if v >= 0 else '▼'} {abs(v):.1f}%</b>" if pd.notnull(v) else "" for v in g_vals]
                g_colors = ["#059669" if v >= 0 else "#dc2626" if pd.notnull(v) else "rgba(0,0,0,0)" for v in g_vals]
                fig.add_trace(go.Bar(
                    x=branch_df['Bulan'], y=branch_df[col_total], offsetgroup=cabang, showlegend=False,
                    text=g_labels, textposition='outside', textfont=dict(color=g_colors, size=11),
                    marker_color='rgba(0,0,0,0)', hoverinfo='none' # 'none' agar tidak menutupi hover bar bawah
                ))

            fig.update_layout(barmode='group', height=400, margin=dict(t=50, b=10),
                              yaxis=dict(range=[0, df_data[col_total].max() * 1.4]),
                              legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True)

    # --- EKSEKUSI ---
    # Revenue (Total Only)
    with st.container(border=True):
        st.subheader("📈 Realisasi Revenue & Pertumbuhan")
        fig_rev = go.Figure()
        for i, cabang in enumerate(selected_cabang):
            branch_df = filtered_df[filtered_df['Cabang'] == cabang].copy()
            rev_labels = branch_df['Actual Revenue (Total)'].apply(lambda x: f"<b>{x/1e9:.2f}M</b>" if x > 0 else "")
            g_labels = [f"<b>{'▲' if v >= 0 else '▼'} {abs(v):.1f}%</b>" if pd.notnull(v) else "" for v in branch_df['Actual Revenue (Total)_Growth']]
            g_colors = ["#059669" if v >= 0 else "#dc2626" if pd.notnull(v) else "rgba(0,0,0,0)" for v in branch_df['Actual Revenue (Total)_Growth']]
            fig_rev.add_trace(go.Bar(
                x=branch_df['Bulan'], y=branch_df['Actual Revenue (Total)'], name=cabang,
                offsetgroup=cabang, marker_color=colors.get(cabang)['base'],
                text=rev_labels, textposition='inside', insidetextanchor='middle', textfont=dict(color='#444444'),
                hovertemplate=f"<b>{cabang}</b>: Rp %{{y:,.0f}}<extra></extra>"
            ))
            fig_rev.add_trace(go.Bar(
                x=branch_df['Bulan'], y=branch_df['Actual Revenue (Total)'], offsetgroup=cabang,
                text=g_labels, textposition='outside', textfont=dict(color=g_colors, size=11),
                marker_color='rgba(0,0,0,0)', showlegend=False, hoverinfo='none'
            ))
        fig_rev.update_layout(barmode='group', height=400, margin=dict(t=50, b=10),
                              yaxis=dict(range=[0, filtered_df['Actual Revenue (Total)'].max() * 1.4]))
        st.plotly_chart(fig_rev, use_container_width=True)

    # Volume OPT, Ranap, IGD
    create_stacked_chart(filtered_df, "👥 Volume Outpatient (OPT)", 'Volume OPT JKN', 'Volume OPT Non JKN', 'Total OPT', 'Total OPT', "Volume OPT")
    create_stacked_chart(filtered_df, "🏥 Volume Inpatient (Ranap)", 'Volume IPT JKN', 'Volume IPT Non JKN', 'Total IPT', 'Total IPT', "Volume IPT")
    create_stacked_chart(filtered_df, "🚑 Volume IGD", 'Volume IGD JKN', 'Volume IGD Non JKN', 'Total IGD', 'Total IGD', "Volume IGD")

else:
    st.warning("Menunggu data dari Google Sheets...")
