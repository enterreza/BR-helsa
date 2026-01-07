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
        
        # Kolom yang harus dikonversi ke angka
        numeric_cols = [
            'Target Revenue', 'Actual Revenue (Total)', 'Actual Revenue (Opt)', 
            'Actual Revenue (Ipt)', 'Volume OPT JKN', 'Volume OPT Non JKN',
            'Volume IPT JKN', 'Volume IPT Non JKN'
        ]
        
        for col in numeric_cols:
            if col in raw_df.columns:
                # Membersihkan karakter non-angka (Rp, titik, koma)
                raw_df[col] = raw_df[col].astype(str).str.replace(r'[^\d]', '', regex=True)
                raw_df[col] = pd.to_numeric(raw_df[col], errors='coerce').fillna(0)
        
        return raw_df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# --- 3. EKSEKUSI LOAD DATA ---
# Pastikan variabel 'df' didefinisikan di sini agar tidak NameError
df = load_data()

# --- 4. LOGIKA DASHBOARD ---
if not df.empty:
    # Sidebar Filter
    st.sidebar.header("🕹️ Filter Panel")
    all_cabang = df['Cabang'].unique()
    selected_cabang = st.sidebar.multiselect("Pilih Cabang:", all_cabang, default=all_cabang)
    
    # Filter Data
    filtered_df = df[df['Cabang'].isin(selected_cabang)]

    # Judul
    st.title("📊 Dashboard Pertumbuhan & Realisasi Helsa-BR")
    
    # --- CHART PERTUMBUHAN (Sesuai Permintaan) ---
    st.subheader("📈 Pertumbuhan Revenue per Cabang 2025")
    
    # Pastikan urutan bulan benar
    month_order = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 
                   'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
    filtered_df['Bulan'] = pd.Categorical(filtered_df['Bulan'], categories=month_order, ordered=True)
    filtered_df = filtered_df.sort_values(['Cabang', 'Bulan'])

    # Hitung Growth MoM
    filtered_df['Growth'] = filtered_df.groupby('Cabang')['Actual Revenue (Total)'].pct_change() * 100

    fig = go.Figure()
    colors = {'Jatirahayu': '#3b82f6', 'Cikampek': '#8b5cf6', 'Citeureup': '#6366f1', 'Ciputat': '#10b981'}

    for cabang in selected_cabang:
        branch_df = filtered_df[filtered_df['Cabang'] == cabang]
        
        # Bar Chart
        fig.add_trace(go.Bar(
            x=branch_df['Bulan'],
            y=branch_df['Actual Revenue (Total)'],
            name=cabang,
            marker_color=colors.get(cabang),
            text=branch_df['Actual Revenue (Total)'].apply(lambda x: f"{x/1e6:.1f}M"),
            textposition='auto',
        ))

        # Tambahkan Label Growth ▲/▼
        for i, row in branch_df.iterrows():
            if pd.notnull(row['Growth']):
                color = "green" if row['Growth'] >= 0 else "red"
                symbol = "▲" if row['Growth'] >= 0 else "▼"
                fig.add_annotation(
                    x=row['Bulan'], y=row['Actual Revenue (Total)'],
                    text=f"{symbol} {row['Growth']:.1f}%",
                    showarrow=False, yshift=25,
                    font=dict(color=color, size=11), xanchor='center'
                )

    fig.update_layout(barmode='group', height=500, margin=dict(t=50))
    st.plotly_chart(fig, use_container_width=True)

    # --- TABEL DETAIL ---
    with st.expander("🔍 Lihat Detail Data Mentah"):
        st.dataframe(filtered_df)
else:
    st.warning("Menunggu data dari Google Sheets...")
