import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- 1. KONFIGURASI DATA ---
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

    # Total & Growth
    filtered_df['Total OPT'] = filtered_df['Volume OPT JKN'] + filtered_df['Volume OPT Non JKN']
    filtered_df['Total IPT'] = filtered_df['Volume IPT JKN'] + filtered_df['Volume IPT Non JKN']
    filtered_df['Total IGD'] = filtered_df['Volume IGD JKN'] + filtered_df['Volume IGD Non JKN']
    
    filtered_df['Rev Growth'] = filtered_df.groupby('Cabang')['Actual Revenue (Total)'].pct_change() * 100
    filtered_df['OPT Growth'] = filtered_df.groupby('Cabang')['Total OPT'].pct_change() * 100
    filtered_df['IPT Growth'] = filtered_df.groupby('Cabang')['Total IPT'].pct_change() * 100
    filtered_df['IGD Growth'] = filtered_df.groupby('Cabang')['Total IGD'].pct_change() * 100

    st.title("📊 Dashboard Performa Operasional Helsa-BR")
    
    colors = {
        'Jatirahayu': {'base': '#AEC6CF', 'light': '#D1E1E6', 'dark': '#779ECB'},
        'Cikampek':   {'base': '#FFB7B2', 'light': '#FFD1CF', 'dark': '#E08E88'},
        'Citeureup':  {'base': '#B2F2BB', 'light': '#D5F9DA', 'dark': '#88C090'},
        'Ciputat':    {'base': '#CFC1FF', 'light': '#E1D9FF', 'dark': '#A694FF'}
    }

    # FUNGSI UNTUK MEMBUAT STACKED CHART (OPT, IPT, IGD)
    def create_stacked_chart(df_data, title, col_jkn, col_nonjkn, col_total, col_growth, y_label):
        with st.container(border=True):
            st.subheader(title)
            fig = go.Figure()
            for i, cabang in enumerate(selected_cabang):
                branch_df = df_data[df_data['Cabang'] == cabang].copy()
                
                # Trace 1: Non JKN (Warna Terang)
                fig.add_trace(go.Bar(
                    x=branch_df['Bulan'], 
                    y=branch_df[col_nonjkn], # Nilai murni Non-JKN
                    name=cabang, legendgroup=cabang,
                    offsetgroup=cabang, marker_color=colors.get(cabang)['light'],
                    customdata=branch_df[col_total], # Mengirim data Total ke Hover
                    text=branch_df[col_nonjkn].apply(lambda x: f"{int(x):,}" if x > 0 else ""),
                    textposition='inside', insidetextanchor='middle', textfont=dict(size=10, color='#444444'),
                    hovertemplate=f"<b>{cabang} (Non JKN)</b>: %{{y:,}} Pasien<br>Total: %{{customdata:,}} Pasien<extra></extra>"
                ))
                
                # Trace 2: JKN (Warna Gelap)
                fig.add_trace(go.Bar(
                    x=branch_df['Bulan'], 
                    y=branch_df[col_jkn], # Nilai murni JKN
                    name=cabang, legendgroup=cabang, showlegend=False,
                    base=branch_df[col_nonjkn], # Menumpuk di atas Non-JKN
                    offsetgroup=cabang, marker_color=colors.get(cabang)['dark'],
                    customdata=branch_df[col_total], # Mengirim data Total ke Hover
                    text=branch_df[col_jkn].apply(lambda x: f"{int(x):,}" if x > 0 else ""),
                    textposition='inside', insidetextanchor='middle', textfont=dict(color='white', size=10),
                    # FIX: %{y} untuk nilai segmen, %{customdata} untuk nilai total
                    hovertemplate=f"<b>{cabang} (JKN)</b>: %{{y:,}} Pasien<br>Total: %{{customdata:,}} Pasien<extra></extra>"
                ))
                
                # Trace 3: Label Growth (Paling Atas)
                g_labels = [f"<b>{'▲' if v >= 0 else '▼'} {abs(v):.1f}%</b>" if pd.notnull(v) else "" for v in branch_df[col_growth]]
                g_colors = ["#059669" if v >= 0 else "#dc2626" if pd.notnull(v) else "rgba(0,0,0,0)" for v in branch_df[col_growth]]
                fig.add_trace(go.Bar(
                    x=branch_df['Bulan'], y=branch_df[col_total], offsetgroup=cabang, showlegend=False,
                    text=g_labels, textposition='outside', textfont=dict(color=g_colors, size=11),
                    marker_color='rgba(0,0,0,0)', 
                    hoverinfo='skip' # Menghindari gangguan hover dari bar transparan ini
                ))

            fig.update_layout(barmode='group', height=400, margin=dict(t=50, b=10),
                              yaxis_title=y_label,
                              yaxis=dict(range=[0, df_data[col_total].max() * 1.35]),
                              legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True)
            
            # Rata-rata Footer
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
            rev_labels = branch_df['Actual Revenue (Total)'].apply(lambda x: f"<b>{x/1e9:.2f}M</b>" if x > 0 else "")
            g_labels = [f"<b>{'▲' if v >= 0 else '▼'} {abs(v):.1f}%</b>" if pd.notnull(v) else "" for v in branch_df['Rev Growth']]
            g_colors = ["#059669" if v >= 0 else "#dc2626" if pd.notnull(v) else "rgba(0,0,0,0)" for v in branch_df['Rev Growth']]
            
            fig_rev.add_trace(go.Bar(
                x=branch_df['Bulan'], y=branch_df['Actual Revenue (Total)'], name=cabang,
                offsetgroup=cabang, marker_color=colors.get(cabang)['base'],
                text=rev_labels, textposition='inside', insidetextanchor='middle', textfont=dict(color='#444444')
            ))
            fig_rev.add_trace(go.Bar(
                x=branch_df['Bulan'], y=branch_df['Actual Revenue (Total)'], offsetgroup=cabang,
                text=g_labels, textposition='outside', textfont=dict(color=g_colors, size=11),
                marker_color='rgba(0,0,0,0)', showlegend=False, hoverinfo='skip'
            ))
        fig_rev.update_layout(barmode='group', height=400, margin=dict(t=50, b=10),
                              yaxis=dict(range=[0, filtered_df['Actual Revenue (Total)'].max() * 1.35]),
                              legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_rev, use_container_width=True)

    # 2. Volume OPT, Ranap (IPT), & IGD
    create_stacked_chart(filtered_df, "👥 Volume Outpatient (OPT)", 'Volume OPT JKN', 'Volume OPT Non JKN', 'Total OPT', 'OPT Growth', "Volume OPT")
    create_stacked_chart(filtered_df, "🏥 Volume Inpatient (Ranap)", 'Volume IPT JKN', 'Volume IPT Non JKN', 'Total IPT', 'IPT Growth', "Volume IPT")
    create_stacked_chart(filtered_df, "🚑 Volume IGD", 'Volume IGD JKN', 'Volume IGD Non JKN', 'Total IGD', 'IGD Growth', "Volume IGD")

    with st.expander("🔍 Lihat Detail Data Mentah"):
        st.dataframe(filtered_df)
else:
    st.warning("Menunggu data dari Google Sheets...")
