import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- 1. KONFIGURASI ---
SHEET_ID = '18Djb0QiE8uMgt_nXljFCZaMKHwii1pMzAtH96zGc_cI'
SHEET_NAME = 'app_data'
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}'

st.set_page_config(page_title="Helsa-BR Live Dashboard", layout="wide")

# --- 2. FUNGSI LOAD & CLEAN DATA ---
@st.cache_data(ttl=300)
def load_data():
    try:
        raw_df = pd.read_csv(URL)
        raw_df.columns = raw_df.columns.str.strip()
        
        numeric_cols = [
            'Target Revenue', 'Actual Revenue (Total)', 'Actual Revenue (Opt)', 
            'Actual Revenue (Ipt)', 'Volume OPT JKN', 'Volume OPT Non JKN',
            'Volume IPT JKN', 'Volume IPT Non JKN'
        ]
        
        for col in numeric_cols:
            if col in raw_df.columns:
                raw_df[col] = raw_df[col].astype(str).str.replace(r'[^\d]', '', regex=True)
                raw_df[col] = pd.to_numeric(raw_df[col], errors='coerce').fillna(0)
        
        return raw_df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

df = load_data()

# --- 3. LOGIKA DASHBOARD ---
if not df.empty:
    st.sidebar.header("🕹️ Filter Panel")
    all_cabang = df['Cabang'].unique()
    selected_cabang = st.sidebar.multiselect("Pilih Cabang:", all_cabang, default=all_cabang)
    
    month_order = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 
                   'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
    
    filtered_df = df[df['Cabang'].isin(selected_cabang)].copy()
    filtered_df['Bulan'] = pd.Categorical(filtered_df['Bulan'], categories=month_order, ordered=True)
    filtered_df = filtered_df.sort_values(['Cabang', 'Bulan'])

    # Perhitungan Total & Growth
    filtered_df['Total Volume OPT'] = filtered_df['Volume OPT JKN'] + filtered_df['Volume OPT Non JKN']
    filtered_df['Rev Growth'] = filtered_df.groupby('Cabang')['Actual Revenue (Total)'].pct_change() * 100
    filtered_df['Vol Growth'] = filtered_df.groupby('Cabang')['Total Volume OPT'].pct_change() * 100

    st.title("📊 Dashboard Performa Helsa-BR")
    
    # Mapping Warna (4 Warna Utama dengan variasi Terang/Gelap)
    colors = {
        'Jatirahayu': {'base': '#3b82f6', 'light': '#93c5fd', 'dark': '#1d4ed8'},
        'Cikampek':   {'base': '#8b5cf6', 'light': '#c4b5fd', 'dark': '#6d28d9'},
        'Citeureup':  {'base': '#6366f1', 'light': '#a5b4fc', 'dark': '#4338ca'},
        'Ciputat':    {'base': '#10b981', 'light': '#6ee7b7', 'dark': '#047857'}
    }

    # ==========================================
    # BAGIAN 1: REVENUE (Grouped Bar - Total Only)
    # ==========================================
    with st.container(border=True):
        st.subheader("📈 Realisasi Revenue & Pertumbuhan per Cabang")
        fig_rev = go.Figure()
        for i, cabang in enumerate(selected_cabang):
            branch_df = filtered_df[filtered_df['Cabang'] == cabang].copy()
            nominal_labels = branch_df['Actual Revenue (Total)'].apply(lambda x: f"<b>{x/1e9:.2f}M</b>" if x > 0 else "")
            growth_labels = [f"<b>{'▲' if v >= 0 else '▼'} {abs(v):.1f}%</b>" if pd.notnull(v) else "" for v in branch_df['Rev Growth']]
            growth_colors = ["#059669" if v >= 0 else "#dc2626" if pd.notnull(v) else "rgba(0,0,0,0)" for v in branch_df['Rev Growth']]
            
            fig_rev.add_trace(go.Bar(
                x=branch_df['Bulan'], y=branch_df['Actual Revenue (Total)'], name=cabang,
                offsetgroup=cabang, marker_color=colors.get(cabang)['base'],
                text=nominal_labels, textposition='inside', insidetextanchor='middle', textfont=dict(color='white')
            ))
            fig_rev.add_trace(go.Bar(
                x=branch_df['Bulan'], y=branch_df['Actual Revenue (Total)'], offsetgroup=cabang,
                text=growth_labels, textposition='outside', textfont=dict(color=growth_colors, size=11),
                marker_color='rgba(0,0,0,0)', showlegend=False, hoverinfo='skip'
            ))

        fig_rev.update_layout(barmode='group', height=450, margin=dict(t=50, b=10),
                              yaxis=dict(range=[0, filtered_df['Actual Revenue (Total)'].max() * 1.35]),
                              legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_rev, use_container_width=True)

        # Footer Rata-rata Revenue
        st.markdown("**Rata-rata Revenue (Data Terisi):**")
        df_rev_ok = filtered_df[filtered_df['Actual Revenue (Total)'] > 0]
        avg_rev = df_rev_ok.groupby('Cabang')['Actual Revenue (Total)'].mean()
        cols_rev = st.columns(len(selected_cabang))
        for idx, cb in enumerate(selected_cabang):
            if cb in avg_rev:
                with cols_rev[idx]:
                    st.markdown(f"<span style='color:{colors.get(cb)['base']}; font-weight:bold;'>● {cb}</span>", unsafe_allow_html=True)
                    st.write(f"Rp {avg_rev[cb]/1e9:.2f} Miliar")

    st.write("")

    # ==========================================
    # BAGIAN 2: VOLUME OPT (Stacked Bar - JKN vs Non-JKN)
    # ==========================================
    with st.container(border=True):
        st.subheader("👥 Realisasi Volume OPT (Stacked JKN vs Non-JKN)")
        fig_vol = go.Figure()
        
        for i, cabang in enumerate(selected_cabang):
            branch_df = filtered_df[filtered_df['Cabang'] == cabang].copy()
            
            # Label Growth untuk posisi paling atas
            growth_labels = [f"<b>{'▲' if v >= 0 else '▼'} {abs(v):.1f}%</b>" if pd.notnull(v) else "" for v in branch_df['Vol Growth']]
            growth_colors = ["#059669" if v >= 0 else "#dc2626" if pd.notnull(v) else "rgba(0,0,0,0)" for v in branch_df['Vol Growth']]
            
            # Trace 1: Volume OPT Non JKN (Dasar Bar - Warna Terang)
            fig_vol.add_trace(go.Bar(
                x=branch_df['Bulan'], y=branch_df['Volume OPT Non JKN'], 
                name=cabang, legendgroup=cabang, showlegend=True,
                offsetgroup=cabang, marker_color=colors.get(cabang)['light'],
                text=branch_df['Volume OPT Non JKN'].apply(lambda x: f"{int(x):,}" if x > 0 else ""),
                textposition='inside', insidetextanchor='middle', textfont=dict(size=10),
                hovertemplate=f"<b>{cabang} (Non JKN)</b>: %{{y:,}} Pasien<extra></extra>"
            ))
            
            # Trace 2: Volume OPT JKN (Menumpuk di Atas - Warna Gelap)
            fig_vol.add_trace(go.Bar(
                x=branch_df['Bulan'], y=branch_df['Volume OPT JKN'], 
                name=cabang, legendgroup=cabang, showlegend=False,
                base=branch_df['Volume OPT Non JKN'], # Teknik manual stacking
                offsetgroup=cabang, marker_color=colors.get(cabang)['dark'],
                text=branch_df['Volume OPT JKN'].apply(lambda x: f"{int(x):,}" if x > 0 else ""),
                textposition='inside', insidetextanchor='middle', textfont=dict(color='white', size=10),
                hovertemplate=f"<b>{cabang} (JKN)</b>: %{{y:,}} Pasien<br>Total: %{{base + y:,}} Pasien<extra></extra>"
            ))

            # Trace 3: Label Growth (Paling Atas)
            fig_vol.add_trace(go.Bar(
                x=branch_df['Bulan'], y=branch_df['Total Volume OPT'], 
                offsetgroup=cabang, showlegend=False,
                text=growth_labels, textposition='outside', textfont=dict(color=growth_colors, size=11),
                marker_color='rgba(0,0,0,0)', hoverinfo='skip'
            ))

        fig_vol.update_layout(barmode='group', height=450, margin=dict(t=50, b=10),
                              yaxis_title="Jumlah Pasien",
                              yaxis=dict(range=[0, filtered_df['Total Volume OPT'].max() * 1.35]),
                              legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_vol, use_container_width=True)

        # Footer Rata-rata Volume
        st.markdown("**Rata-rata Volume OPT (Total):**")
        df_vol_ok = filtered_df[filtered_df['Total Volume OPT'] > 0]
        avg_vol = df_vol_ok.groupby('Cabang')['Total Volume OPT'].mean()
        cols_vol = st.columns(len(selected_cabang))
        for idx, cb in enumerate(selected_cabang):
            if cb in avg_vol:
                with cols_vol[idx]:
                    st.markdown(f"<span style='color:{colors.get(cb)['base']}; font-weight:bold;'>● {cb}</span>", unsafe_allow_html=True)
                    st.write(f"{int(avg_vol[cb]):,} Pasien")

    with st.expander("🔍 Lihat Detail Data Mentah"):
        st.dataframe(filtered_df)
else:
    st.warning("Menunggu data dari Google Sheets...")
