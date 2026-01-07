import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- 1. KONFIGURASI ---
SHEET_ID = '18Djb0QiE8uMgt_nXljFCZaMKHwii1pMzAtH96zGc_cI'
SHEET_NAME = 'app_data'
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}'

st.set_page_config(page_title="Helsa-BR Performance Dashboard", layout="wide")

# --- 2. FUNGSI LOAD & CLEAN DATA ---
@st.cache_data(ttl=300)
def load_data():
    try:
        raw_df = pd.read_csv(URL)
        raw_df.columns = raw_df.columns.str.strip()
        
        # Kolom numerik yang harus dibersihkan
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
df = load_data()

# --- 4. LOGIKA DASHBOARD ---
if not df.empty:
    # Sidebar Filter
    st.sidebar.header("🕹️ Filter Panel")
    all_cabang = df['Cabang'].unique()
    selected_cabang = st.sidebar.multiselect("Pilih Cabang:", all_cabang, default=all_cabang)
    
    # Filter Data
    filtered_df = df[df['Cabang'].isin(selected_cabang)].copy()

    # Judul
    st.title("📊 Dashboard Pertumbuhan & Realisasi Helsa-BR")
    
    # --- CHART PERTUMBUHAN & NOMINAL ---
    st.subheader("📈 Realisasi Revenue (Nominal) & Pertumbuhan MoM")
    
    # Urutan bulan agar kronologis
    month_order = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 
                   'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
    filtered_df['Bulan'] = pd.Categorical(filtered_df['Bulan'], categories=month_order, ordered=True)
    filtered_df = filtered_df.sort_values(['Cabang', 'Bulan'])

    # Hitung Growth MoM
    filtered_df['Growth'] = filtered_df.groupby('Cabang')['Actual Revenue (Total)'].pct_change() * 100

    fig = go.Figure()
    
    # Warna per Cabang
    colors = {
        'Jatirahayu': '#3b82f6', # Biru
        'Cikampek':   '#8b5cf6', # Ungu
        'Citeureup':  '#6366f1', # Indigo
        'Ciputat':    '#10b981'  # Hijau
    }

    for i, cabang in enumerate(selected_cabang):
        branch_df = filtered_df[filtered_df['Cabang'] == cabang].copy()
        
        # 1. Siapkan Label Nominal (e.g., 4.8B atau 4.8M)
        # Di sini kita bagi 1.000.000.000 untuk format Miliar (M)
        nominal_labels = branch_df['Actual Revenue (Total)'].apply(lambda x: f"<b>{x/1e9:.2f}M</b>")
        
        # 2. Trace: Actual Revenue (Total)
        fig.add_trace(go.Bar(
            x=branch_df['Bulan'],
            y=branch_df['Actual Revenue (Total)'],
            name=cabang,
            marker_color=colors.get(cabang, '#94a3b8'),
            # Cantumkan nominal revenue di dalam bar
            text=nominal_labels,
            textposition='inside', # Meletakkan angka nominal di dalam batang
            insidetextanchor='middle',
            textfont=dict(color='white', size=12),
            hovertemplate=f"<b>{cabang}</b><br>Actual: Rp %{{y:,.0f}}<extra></extra>"
        ))

        # 3. Tambahkan Label Growth (▲/▼) di atas bar menggunakan Anotasi
        for idx, row in branch_df.iterrows():
            if pd.notnull(row['Growth']):
                color = "#059669" if row['Growth'] >= 0 else "#dc2626"
                symbol = "▲" if row['Growth'] >= 0 else "▼"
                
                # Menghitung posisi X yang tepat untuk masing-masing bar dalam grup
                # (Plotly secara internal membagi grup berdasarkan jumlah cabang)
                fig.add_annotation(
                    x=row['Bulan'],
                    y=row['Actual Revenue (Total)'],
                    text=f"<b>{symbol} {abs(row['Growth']):.1f}%</b>",
                    showarrow=False,
                    yshift=15, # Jarak di atas batang
                    xshift=(i - (len(selected_cabang)-1)/2) * 20, # Menggeser label agar tepat di atas bar cabangnya
                    font=dict(color=color, size=11),
                    xanchor='center'
                )

    # Pengaturan Layout
    fig.update_layout(
        barmode='group', 
        height=650, 
        margin=dict(t=100, b=50),
        xaxis_title="Periode Bulan",
        yaxis_title="Total Revenue (IDR)",
        # Memberikan margin atas agar label pertumbuhan tidak terpotong
        yaxis=dict(range=[0, filtered_df['Actual Revenue (Total)'].max() * 1.3]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified"
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # --- TABEL DETAIL ---
    with st.expander("🔍 Lihat Detail Data Mentah"):
        st.dataframe(filtered_df)
else:
    st.warning("Menunggu data dari Google Sheets...")
