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
    all_cabang_list = list(df['Cabang'].unique())
    selected_cabang = st.sidebar.multiselect("Pilih Cabang:", all_cabang_list, default=all_cabang_list)
    
    month_order = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 
                   'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
    
    filtered_df = df[df['Cabang'].isin(selected_cabang)].copy()
    filtered_df['Bulan'] = pd.Categorical(filtered_df['Bulan'], categories=month_order, ordered=True)
    filtered_df = filtered_df.sort_values(['Cabang', 'Bulan'])

    # Perhitungan Metrik
    filtered_df['Total OPT'] = filtered_df['Volume OPT JKN'] + filtered_df['Volume OPT Non JKN']
    filtered_df['Total IPT'] = filtered_df['Volume IPT JKN'] + filtered_df['Volume IPT Non JKN']
    filtered_df['Total IGD'] = filtered_df['Volume IGD JKN'] + filtered_df['Volume IGD Non JKN']
    
    # Growth Calculation
    for col in ['Actual Revenue (Total)', 'Total OPT', 'Total IPT', 'Total IGD']:
        filtered_df[f'{col}_Growth'] = filtered_df.groupby('Cabang')[col].pct_change() * 100

    st.title("📊 Dashboard Performa Helsa-BR 2025")
    
    # Warna Pale Kontras
    colors = {
        'Jatirahayu': {'base': '#AEC6CF', 'light': '#D1E1E6', 'dark': '#779ECB'},
        'Cikampek':   {'base': '#FFB7B2', 'light': '#FFD1CF', 'dark': '#E08E88'},
        'Citeureup':  {'base': '#B2F2BB', 'light': '#D5F9DA', 'dark': '#88C090'},
        'Ciputat':    {'base': '#CFC1FF', 'light': '#E1D9FF', 'dark': '#A694FF'}
    }

    # FUNGSI UNTUK MEMBUAT STACKED CHART (OPT, IPT, IGD)
    def create_stacked_chart(df_data, title, col_jkn, col_nonjkn, col_total, col_growth_name, y_label):
        with st.container(border=True):
            st.subheader(title)
            fig = go.Figure()
            num_branches = len(selected_cabang)
            
            for i, cabang in enumerate(selected_cabang):
                branch_df = df_data[df_data['Cabang'] == cabang].copy()
                
                # Trace 1: Non JKN (Warna Terang)
                fig.add_trace(go.Bar(
                    x=branch_df['Bulan'], y=branch_df[col_nonjkn], name=cabang, legendgroup=cabang,
                    offsetgroup=cabang, marker_color=colors.get(cabang)['light'],
                    customdata=branch_df[col_total],
                    text=branch_df[col_nonjkn].apply(lambda x: f"{int(x):,}" if x > 0 else ""),
                    textposition='inside', insidetextanchor='middle', textfont=dict(size=10, color='#444444'),
                    hovertemplate=f"<b>{cabang} (Non JKN)</b>: %{{y:,}} Pasien<br>Total: %{{customdata:,}} Pasien<extra></extra>"
                ))
                # Trace 2: JKN (Warna Gelap)
                fig.add_trace(go.Bar(
                    x=branch_df['Bulan'], y=branch_df[col_jkn], name=cabang, legendgroup=cabang, showlegend=False,
                    base=branch_df[col_nonjkn], offsetgroup=cabang, marker_color=colors.get(cabang)['dark'],
                    customdata=branch_df[col_total],
                    text=branch_df[col_jkn].apply(lambda x: f"{int(x):,}" if x > 0 else ""),
                    textposition='inside', insidetextanchor='middle', textfont=dict(color='white', size=10),
                    # FIX: y = JKN saja, customdata = Total
                    hovertemplate=f"<b>{cabang} (JKN)</b>: %{{y:,}} Pasien<br>Total: %{{customdata:,}} Pasien<extra></extra>"
                ))
                
                # Tambahkan Label Growth via Annotation (Bebas gangguan hover)
                for idx, row in branch_df.iterrows():
                    growth_val = row[col_growth_name]
                    if pd.notnull(growth_val):
                        symbol = "▲" if growth_val >= 0 else "▼"
                        g_color = "#059669" if growth_val >= 0 else "#dc2626"
                        # Hitung pergeseran X manual agar tepat di atas bar yang berkelompok
                        x_shift = (i - (num_branches - 1) / 2) * (1 / (num_branches + 1))
                        fig.add_annotation(
                            x=row['Bulan'], y=row[col_total],
                            text=f"<b>{symbol} {abs(growth_val):.1f}%</b>",
                            showarrow=False, yshift=12, xshift=x_shift,
                            font=dict(color=g_color, size=10),
                            xref="x", yref="y", xanchor="center"
                        )

            fig.update_layout(barmode='group', height=400, margin=dict(t=60, b=10),
                              yaxis_title="Jumlah Pasien",
                              yaxis=dict(range=[0, df_data[col_total].max() * 1.35]),
                              legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True)
            
            # Rata-rata Footer
            avg_val = df_data[df_data[col_total] > 0].groupby('Cabang')[col_total].mean()
            cols = st.columns(len(selected_cabang))
            for idx, cb in enumerate(selected_cabang):
                if cb in avg_val:
                    with cols[idx]:
                        st.markdown(f"<span style='color:{colors.get(cb)['base']};'>● <b>{cb}</b></span>", unsafe_allow_html=True)
                        st.write(f"{int(avg_val[cb]):,} Pasien (Avg)")

    # --- EKSEKUSI BAGIAN ---

    # 1. Revenue
    with st.container(border=True):
        st.subheader("📈 Realisasi Revenue & Pertumbuhan")
        fig_rev = go.Figure()
        for i, cabang in enumerate(selected_cabang):
            branch_df = filtered_df[filtered_df['Cabang'] == cabang].copy()
            rev_labels = branch_df['Actual Revenue (Total)'].apply(lambda x: f"<b>{x/1e9:.2f}M</b>" if x > 0 else "")
            
            fig_rev.add_trace(go.Bar(
                x=branch_df['Bulan'], y=branch_df['Actual Revenue (Total)'], name=cabang,
                offsetgroup=cabang, marker_color=colors.get(cabang)['base'],
                text=rev_labels, textposition='inside', insidetextanchor='middle', textfont=dict(color='#444444'),
                hovertemplate=f"<b>{cabang}</b>: Rp %{{y:,.0f}}<extra></extra>"
            ))
            # Growth Annotation for Revenue
            for idx, row in branch_df.iterrows():
                growth_val = row['Actual Revenue (Total)_Growth']
                if pd.notnull(growth_val):
                    g_color = "#059669" if growth_val >= 0 else "#dc2626"
                    fig_rev.add_annotation(
                        x=row['Bulan'], y=row['Actual Revenue (Total)'],
                        text=f"<b>{'▲' if growth_val >= 0 else '▼'} {abs(growth_val):.1f}%</b>",
                        showarrow=False, yshift=12, font=dict(color=g_color, size=10)
                    )
        fig_rev.update_layout(barmode='group', height=400, margin=dict(t=60, b=10),
                              yaxis=dict(range=[0, filtered_df['Actual Revenue (Total)'].max() * 1.35]))
        st.plotly_chart(fig_rev, use_container_width=True)

    # 2. Volume OPT, Ranap, & IGD
    create_stacked_chart(filtered_df, "👥 Volume Outpatient (OPT)", 'Volume OPT JKN', 'Volume OPT Non JKN', 'Total OPT', 'Total OPT_Growth', "Volume OPT")
    create_stacked_chart(filtered_df, "🏥 Volume Inpatient (Ranap)", 'Volume IPT JKN', 'Volume IPT Non JKN', 'Total IPT', 'Total IPT_Growth', "Volume IPT")
    create_stacked_chart(filtered_df, "🚑 Volume IGD", 'Volume IGD JKN', 'Volume IGD Non JKN', 'Total IGD', 'Total IGD_Growth', "Volume IGD")

    with st.expander("🔍 Lihat Detail Data Mentah"):
        st.dataframe(filtered_df)
else:
    st.warning("Menunggu data dari Google Sheets...")
