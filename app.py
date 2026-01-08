import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# --- 1. KONFIGURASI DATA ---
SHEET_ID = '18Djb0QiE8uMgt_nXljFCZaMKHwii1pMzAtH96zGc_cI'
SHEET_NAME = 'app_data'
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}'

st.set_page_config(page_title="Helsa-BR Performance Dashboard", layout="wide")

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
    all_cabang = list(df['Cabang'].unique())
    selected_cabang = st.sidebar.multiselect("Pilih Cabang:", all_cabang, default=all_cabang)
    
    month_order = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 
                   'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
    filtered_df = df[df['Cabang'].isin(selected_cabang)].copy()
    filtered_df['Bulan'] = pd.Categorical(filtered_df['Bulan'], categories=month_order, ordered=True)
    filtered_df = filtered_df.sort_values(['Cabang', 'Bulan'])

    # Kalkulasi Total per Kategori
    filtered_df['Total OPT'] = filtered_df['Volume OPT JKN'] + filtered_df['Volume OPT Non JKN']
    filtered_df['Total IPT'] = filtered_df['Volume IPT JKN'] + filtered_df['Volume IPT Non JKN']
    filtered_df['Total IGD'] = filtered_df['Volume IGD JKN'] + filtered_df['Volume IGD Non JKN']
    
    # Kalkulasi Growth
    for cat in ['Actual Revenue (Total)', 'Total OPT', 'Total IPT', 'Total IGD']:
        filtered_df[f'{cat}_Growth'] = filtered_df.groupby('Cabang')[cat].pct_change() * 100

    st.title("📊 Dashboard Performa Helsa-BR")
    
    colors = {
        'Jatirahayu': {'light': '#AEC6CF', 'dark': '#779ECB'},
        'Cikampek':   {'light': '#FFB7B2', 'dark': '#E08E88'},
        'Citeureup':  {'light': '#B2F2BB', 'dark': '#88C090'},
        'Ciputat':    {'light': '#CFC1FF', 'dark': '#A694FF'}
    }

    def create_dashboard_chart(df_plot, title, col_jkn, col_nonjkn, col_total, growth_col):
        with st.container(border=True):
            st.subheader(title)
            fig = go.Figure()
            
            for i, cabang in enumerate(selected_cabang):
                branch_df = df_plot[df_plot['Cabang'] == cabang].copy()
                
                # Trace 1: Non-JKN (Bawah)
                fig.add_trace(go.Bar(
                    x=branch_df['Bulan'], y=branch_df[col_nonjkn], name=cabang, legendgroup=cabang,
                    offsetgroup=i, marker_color=colors.get(cabang)['light'],
                    text=branch_df[col_nonjkn].apply(lambda x: f"{int(x):,}" if x > 0 else ""),
                    textposition='inside', insidetextanchor='middle',
                    customdata=branch_df[col_total],
                    hovertemplate=f"<b>{cabang} (Non JKN)</b>: %{{y:,}} Pasien<br>Total: %{{customdata:,}} Pasien<extra></extra>"
                ))
                
                # Trace 2: JKN (Atas) + Label Pertumbuhan
                growth_labels = [f"<b>{'▲' if v >= 0 else '▼'} {abs(v):.1f}%</b>" if pd.notnull(v) else "" 
                                 for v in branch_df[growth_col]]
                
                fig.add_trace(go.Bar(
                    x=branch_df['Bulan'], y=branch_df[col_jkn], name=cabang, legendgroup=cabang, showlegend=False,
                    base=branch_df[col_nonjkn], offsetgroup=i, marker_color=colors.get(cabang)['dark'],
                    text=growth_labels, textposition='outside', # Label growth diletakkan di luar bar teratas
                    customdata=np.stack((branch_df[col_jkn], branch_df[col_total]), axis=-1),
                    # SOLUSI: Ambil JKN murni dari customdata[0] agar tidak terbaca Total
                    hovertemplate=f"<b>{cabang} (JKN)</b>: %{{customdata[0]:,}} Pasien<br>Total: %{{customdata[1]:,}} Pasien<extra></extra>"
                ))

            fig.update_layout(barmode='group', height=450, margin=dict(t=50, b=10),
                              yaxis=dict(range=[0, df_plot[col_total].max() * 1.4]),
                              legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True)

    # --- 1. Revenue Chart ---
    with st.container(border=True):
        st.subheader("📈 Realisasi Revenue & Pertumbuhan")
        fig_rev = go.Figure()
        for i, cabang in enumerate(selected_cabang):
            branch_df = filtered_df[filtered_df['Cabang'] == cabang]
            growth_rev = [f"<b>{'▲' if v >= 0 else '▼'} {abs(v):.1f}%</b>" if pd.notnull(v) else "" 
                          for v in branch_df['Actual Revenue (Total)_Growth']]
            fig_rev.add_trace(go.Bar(
                x=branch_df['Bulan'], y=branch_df['Actual Revenue (Total)'], name=cabang,
                offsetgroup=i, marker_color=colors.get(cabang)['dark'],
                text=growth_rev, textposition='outside',
                hovertemplate=f"<b>{cabang}</b>: Rp %{{y:,.0f}}<extra></extra>"
            ))
        fig_rev.update_layout(barmode='group', height=400, yaxis=dict(range=[0, filtered_df['Actual Revenue (Total)'].max() * 1.3]))
        st.plotly_chart(fig_rev, use_container_width=True)

    # --- 2. Volume Charts ---
    create_dashboard_chart(filtered_df, "👥 Volume Outpatient (OPT)", 'Volume OPT JKN', 'Volume OPT Non JKN', 'Total OPT', 'Total OPT_Growth')
    create_dashboard_chart(filtered_df, "🏥 Volume Inpatient (Ranap)", 'Volume IPT JKN', 'Volume IPT Non JKN', 'Total IPT', 'Total IPT_Growth')
    create_dashboard_chart(filtered_df, "🚑 Volume IGD", 'Volume IGD JKN', 'Volume IGD Non JKN', 'Total IGD', 'Total IGD_Growth')

else:
    st.warning("Menunggu data...")
