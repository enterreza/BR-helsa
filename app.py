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
    
    for col in ['Actual Revenue (Total)', 'Total OPT', 'Total IPT', 'Total IGD']:
        filtered_df[f'{col}_Growth'] = filtered_df.groupby('Cabang')[col].pct_change() * 100

    st.title("📊 Dashboard Performa Helsa-BR 2025")
    
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
            
            for i, cabang in enumerate(selected_cabang):
                branch_df = df_data[df_data['Cabang'] == cabang].copy()
                
                # Trace 1: Non JKN (Warna Terang)
                fig.add_trace(go.Bar(
                    x=branch_df['Bulan'], y=branch_df[col_nonjkn], name=cabang, legendgroup=cabang,
                    offsetgroup=cabang, marker_color=colors.get(cabang)['light'],
                    customdata=branch_df[col_total],
                    text=branch_df[col_nonjkn].apply(lambda x: f"<b>{int(x):,} Non JKN</b>" if x > 0 else ""),
                    textposition='inside', insidetextanchor='middle', textfont=dict(size=10, color='#444444'),
                    hovertemplate=f"<b>{cabang}</b><br>Total: %{{customdata:,}} Pasien<extra></extra>"
                ))
                
                # Trace 2: JKN (Warna Gelap)
                fig.add_trace(go.Bar(
                    x=branch_df['Bulan'], y=branch_df[col_jkn], name=cabang, legendgroup=cabang, showlegend=False,
                    base=branch_df[col_nonjkn], offsetgroup=cabang, marker_color=colors.get(cabang)['dark'],
                    customdata=branch_df[col_total],
                    text=branch_df[col_jkn].apply(lambda x: f"<b>{int(x):,} JKN</b>" if x > 0 else ""),
                    textposition='inside', insidetextanchor='middle', textfont=dict(color='white', size=10),
                    hovertemplate=f"<b>{cabang}</b><br>Total: %{{customdata:,}} Pasien<extra></extra>"
                ))
                
                # Trace 3: Label Growth (Paling Atas)
                growth_vals = branch_df[col_growth_name]
                g_labels = [f"<b>{'▲' if v >= 0 else '▼'} {abs(v):.1f}%</b>" if pd.notnull(v) else "" for v in growth_vals]
                g_colors = ["#059669" if v >= 0 else "#dc2626" if pd.notnull(v) else "rgba(0,0,0,0)" for v in growth_vals]
                
                fig.add_trace(go.Bar(
                    x=branch_df['Bulan'], y=branch_df[col_total], offsetgroup=cabang, showlegend=False,
                    text=g_labels, textposition='outside', textfont=dict(color=g_colors, size=11),
                    marker_color='rgba(0,0,0,0)', hoverinfo='skip'
                ))

            fig.update_layout(barmode='group', height=450, margin=dict(t=80, b=10),
                              yaxis_title=y_label,
                              yaxis=dict(range=[0, df_data[col_total].max() * 1.5]),
                              legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True)
            
            # --- FOOTER RATA-RATA ---
            st.markdown(f"**Rata-rata {y_label} per Bulan:**")
            df_ok = df_data[df_data[col_total] > 0]
            avg_val = df_ok.groupby('Cabang')[col_total].mean()
            cols = st.columns(len(selected_cabang))
            for idx, cb in enumerate(selected_cabang):
                if cb in avg_val:
                    with cols[idx]:
                        st.markdown(f"<span style='color:{colors.get(cb)['base']};'>● <b>{cb}</b></span>", unsafe_allow_html=True)
                        st.write(f"{int(avg_val[cb]):,} Pasien")

    # --- EKSEKUSI ---
    # 1. Revenue
    with st.container(border=True):
        st.subheader("📈 Realisasi Revenue & Pertumbuhan")
        fig_rev = go.Figure()
        for i, cabang in enumerate(selected_cabang):
            branch_df = filtered_df[filtered_df['Cabang'] == cabang].copy()
            nominal_labels = branch_df['Actual Revenue (Total)'].apply(lambda x: f"<b>{x/1e9:.2f}M</b>" if x > 0 else "")
            
            # Trace Utama Revenue
            fig_rev.add_trace(go.Bar(
                x=branch_df['Bulan'], y=branch_df['Actual Revenue (Total)'], name=cabang,
                offsetgroup=cabang, marker_color=colors.get(cabang)['base'],
                text=nominal_labels, textposition='inside', insidetextanchor='middle', textfont=dict(color='#444444'),
                hovertemplate=f"<b>{cabang}</b>: Rp %{{y:,.0f}}<extra></extra>"
            ))
            
            # Trace Growth Revenue
            rev_growth = branch_df['Actual Revenue (Total)_Growth']
            g_labels = [f"<b>{'▲' if v >= 0 else '▼'} {abs(v):.1f}%</b>" if pd.notnull(v) else "" for v in rev_growth]
            g_colors = ["#059669" if v >= 0 else "#dc2626" if pd.notnull(v) else "rgba(0,0,0,0)" for v in rev_growth]
            
            fig_rev.add_trace(go.Bar(
                x=branch_df['Bulan'], y=branch_df['Actual Revenue (Total)'], offsetgroup=cabang, showlegend=False,
                text=g_labels, textposition='outside', textfont=dict(color=g_colors, size=11),
                marker_color='rgba(0,0,0,0)', hoverinfo='skip'
            ))

        fig_rev.update_layout(barmode='group', height=400, margin=dict(t=80, b=10),
                              yaxis=dict(range=[0, filtered_df['Actual Revenue (Total)'].max() * 1.5]))
        st.plotly_chart(fig_rev, use_container_width=True)
        
        # Rata-rata Revenue
        st.markdown("**Rata-rata Revenue per Bulan:**")
        df_rev_ok = filtered_df[filtered_df['Actual Revenue (Total)'] > 0]
        avg_rev = df_rev_ok.groupby('Cabang')['Actual Revenue (Total)'].mean()
        cols_rev = st.columns(len(selected_cabang))
        for idx, cb in enumerate(selected_cabang):
            if cb in avg_rev:
                with cols_rev[idx]:
                    st.markdown(f"<span style='color:{colors.get(cb)['base']};'>● <b>{cb}</b></span>", unsafe_allow_html=True)
                    st.write(f"Rp {avg_rev[cb]/1e9:.2f} M")

    # 2. Volume OPT, Ranap, & IGD
    create_stacked_chart(filtered_df, "👥 Volume Outpatient (OPT)", 'Volume OPT JKN', 'Volume OPT Non JKN', 'Total OPT', 'Total OPT_Growth', "Volume OPT")
    create_stacked_chart(filtered_df, "🏥 Volume Inpatient (Ranap)", 'Volume IPT JKN', 'Volume IPT Non JKN', 'Total IPT', 'Total IPT_Growth', "Volume IPT")
    create_stacked_chart(filtered_df, "🚑 Volume IGD", 'Volume IGD JKN', 'Volume IGD Non JKN', 'Total IGD', 'Total IGD_Growth', "Volume IGD")

    with st.expander("🔍 Lihat Detail Data Mentah"):
        st.dataframe(filtered_df)
else:
    st.warning("Menunggu data dari Google Sheets...")
