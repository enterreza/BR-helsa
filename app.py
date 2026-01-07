import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURASI DATA SOURCE ---
SHEET_ID = '18Djb0QiE8uMgt_nXljFCZaMKHwii1pMzAtH96zGc_cI'
SHEET_NAME = 'app_data'
# URL khusus untuk menarik sheet berdasarkan nama
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}'

st.set_page_config(page_title="Helsa-BR Live Dashboard", layout="wide")

@st.cache_data(ttl=300) # Data refresh setiap 5 menit
def load_data():
    try:
        df = pd.read_csv(URL)
        
        # Pembersihan Nama Kolom (menghapus spasi berlebih atau karakter aneh)
        df.columns = df.columns.str.strip()
        
        # Konversi kolom angka (menangani format ribuan jika ada)
        numeric_cols = [
            'Target Revenue', 'Actual Revenue (Total)', 'Actual Revenue (Opt)', 
            'Actual Revenue (Ipt)', 'Volume OPT JKN', 'Volume OPT Non JKN',
            'Volume IPT JKN', 'Volume IPT Non JKN'
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        return df
    except Exception as e:
        st.error(f"Gagal memuat sheet '{SHEET_NAME}': {e}")
        return pd.DataFrame()

# Load Data
df = load_data()

if not df.empty:
    # --- SIDEBAR ---
    st.sidebar.header("🕹️ Control Panel")
    
    # Filter Cabang
    all_cabang = df['Cabang'].unique()
    selected_cabang = st.sidebar.multiselect("Pilih Cabang:", all_cabang, default=all_cabang)
    
    # Filter Bulan
    all_bulan = df['Bulan'].unique()
    selected_bulan = st.sidebar.multiselect("Pilih Bulan:", all_bulan, default=all_bulan)

    # Filter Data berdasarkan pilihan user
    filtered_df = df[(df['Cabang'].isin(selected_cabang)) & (df['Bulan'].isin(selected_bulan))]

    # --- HEADER ---
    st.title("📊 Helsa-BR Performance Dashboard")
    st.info(f"📍 Menampilkan data dari sheet: **{SHEET_NAME}**")

    # --- ROW 1: METRIK UTAMA ---
    col1, col2, col3, col4 = st.columns(4)
    
    total_rev = filtered_df['Actual Revenue (Total)'].sum()
    total_tar = filtered_df['Target Revenue'].sum()
    ach = (total_rev / total_tar * 100) if total_tar > 0 else 0
    
    col1.metric("Actual Revenue", f"Rp {total_rev:,.0f}")
    col2.metric("Target Revenue", f"Rp {total_tar:,.0f}")
    col3.metric("% Achievement", f"{ach:.1f}%", delta=f"{ach-100:.1f}%")
    col4.metric("Total Pasien (Opt+Ipt)", f"{filtered_df[['Volume OPT JKN', 'Volume OPT Non JKN', 'Volume IPT JKN', 'Volume IPT Non JKN']].sum().sum():,.0f}")

    st.divider()

    # --- ROW 2: CHART TIMELINE ---
    st.subheader("📈 Tren Realisasi vs Target Bulanan")
    
    # Pastikan urutan bulan sesuai kalender (Jan-Des)
    month_order = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 
                   'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
    
    timeline_df = filtered_df.groupby('Bulan')[['Actual Revenue (Total)', 'Target Revenue']].sum().reset_index()
    timeline_df['Bulan'] = pd.Categorical(timeline_df['Bulan'], categories=month_order, ordered=True)
    timeline_df = timeline_df.sort_values('Bulan')

    fig_timeline = go.Figure()
    fig_timeline.add_trace(go.Bar(x=timeline_df['Bulan'], y=timeline_df['Actual Revenue (Total)'], name='Actual', marker_color='#10b981'))
    fig_timeline.add_trace(go.Scatter(x=timeline_df['Bulan'], y=timeline_df['Target Revenue'], name='Target', line=dict(color='#ef4444', width=3)))
    
    fig_timeline.update_layout(height=400, margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig_timeline, use_container_width=True)

    # --- ROW 3: VOLUME & PROPORSI ---
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("🏢 Revenue per Cabang")
        fig_pie = px.pie(filtered_df, values='Actual Revenue (Total)', names='Cabang', hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with c2:
        st.subheader("👥 Volume Pasien JKN vs Non-JKN")
        # Menjumlahkan total JKN vs Non-JKN
        jkn_total = filtered_df[['Volume OPT JKN', 'Volume IPT JKN']].sum().sum()
        non_jkn_total = filtered_df[['Volume OPT Non JKN', 'Volume IPT Non JKN']].sum().sum()
        
        fig_vol = px.bar(
            x=['JKN', 'Non-JKN'], 
            y=[jkn_total, non_jkn_total],
            labels={'x': 'Kategori Pasien', 'y': 'Jumlah Pasien'},
            color=['JKN', 'Non-JKN'],
            color_discrete_sequence=['#3b82f6', '#f59e0b']
        )
        st.plotly_chart(fig_vol, use_container_width=True)

    # --- DATA TABLE ---
    with st.expander("🔍 Lihat Detail Data Mentah"):
        st.dataframe(filtered_df, use_container_width=True)

else:
    st.warning("Data tidak ditemukan atau sheet kosong.")
