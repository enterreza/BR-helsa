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
        
        # Kolom numerik yang diproses
        numeric_cols = [
            'Target Revenue', 'Actual Revenue (Total)', 
            'Actual Revenue (Opt)', 'Actual Revenue (Ipt)'
        ]
        
        for col in numeric_cols:
            if col in raw_df.columns:
                # Membersihkan format uang/teks ke angka murni
                raw_df[col] = raw_df[col].astype(str).str.replace(r'[^\d]', '', regex=True)
                raw_df[col] = pd.to_numeric(raw_df[col], errors='coerce').fillna(0)
        
        return raw_df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

df = load_data()

# --- 3. LOGIKA DASHBOARD ---
if not df.empty:
    # Sidebar Filter
    st.sidebar.header("🕹️ Filter Panel")
    all_cabang = df['Cabang'].unique()
    selected_cabang = st.sidebar.multiselect("Pilih Cabang:", all_cabang, default=all_cabang)
    
    # Pre-processing Data (Urutan Bulan & Growth)
    month_order = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 
                   'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
    
    filtered_df = df[df['Cabang'].isin(selected_cabang)].copy()
    filtered_df['Bulan'] = pd.Categorical(filtered_df['Bulan'], categories=month_order, ordered=True)
    filtered_df = filtered_df.sort_values(['Cabang', 'Bulan'])
    
    # Hitung Growth berdasarkan TOTAL Revenue
    filtered_df['Growth'] = filtered_df.groupby('Cabang')['Actual Revenue (Total)'].pct_change() * 100

    st.title("📊 Dashboard Performa Helsa-BR")
    st.subheader("📈 Realisasi Revenue: Outpatient (Opt) vs Inpatient (Ipt)")

    # --- 4. VISUALISASI STACKED GROUPED BAR ---
    fig = go.Figure()

    # Warna khusus untuk pembeda Opt dan Ipt
    # Kita gunakan skema: Opt (Warna Terang), Ipt (Warna Gelap) dari hue yang sama per cabang
    color_map = {
        'Jatirahayu': {'opt': '#60a5fa', 'ipt': '#1e40af'}, # Biru
        'Cikampek': {'opt': '#a78bfa', 'ipt': '#5b21b6'},   # Ungu
        'Citeureup': {'opt': '#818cf8', 'ipt': '#3730a3'},  # Indigo
        'Ciputat': {'opt': '#34d399', 'ipt': '#065f46'}     # Hijau
    }

    for cabang in selected_cabang:
        branch_df = filtered_df[filtered_df['Cabang'] == cabang]
        
        # Trace untuk Outpatient (Opt)
        fig.add_trace(go.Bar(
            x=branch_df['Bulan'],
            y=branch_df['Actual Revenue (Opt)'],
            name=f"{cabang} (Opt)",
            stackgroup=cabang, # Ini yang membuat bar menumpuk (stacked) per cabang
            marker_color=color_map.get(cabang, {}).get('opt', '#94a3b8'),
            hovertemplate='%{x}<br>Opt: Rp %{y:,.0f}<extra></extra>'
        ))

        # Trace untuk Inpatient (Ipt)
        fig.add_trace(go.Bar(
            x=branch_df['Bulan'],
            y=branch_df['Actual Revenue (Ipt)'],
            name=f"{cabang} (Ipt)",
            stackgroup=cabang,
            marker_color=color_map.get(cabang, {}).get('ipt', '#475569'),
            hovertemplate='%{x}<br>Ipt: Rp %{y:,.0f}<extra></extra>'
        ))

        # Tambahkan Label Growth ▲/▼ di atas Total
        for i, row in branch_df.iterrows():
            if pd.notnull(row['Growth']):
                color = "#059669" if row['Growth'] >= 0 else "#dc2626"
                symbol = "▲" if row['Growth'] >= 0 else "▼"
                fig.add_annotation(
                    x=row['Bulan'], y=row['Actual Revenue (Total)'],
                    text=f"{symbol} {row['Growth']:.1f}%",
                    showarrow=False, yshift=15,
                    font=dict(color=color, size=10, bordercolor=color),
                    xanchor='center'
                )

    fig.update_layout(
        barmode='group', # Tetap grouped agar antar cabang bersebelahan
        height=600,
        xaxis_title="Periode Bulan",
        yaxis_title="Revenue (IDR)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified"
    )

    st.plotly_chart(fig, use_container_width=True)

    # --- 5. SUMMARY TABLE ---
    with st.expander("🔍 Detail Angka per Kategori"):
        display_df = filtered_df[['Bulan', 'Cabang', 'Actual Revenue (Opt)', 'Actual Revenue (Ipt)', 'Actual Revenue (Total)', 'Growth']]
        st.dataframe(display_df.style.format({
            'Actual Revenue (Opt)': '{:,.0f}',
            'Actual Revenue (Ipt)': '{:,.0f}',
            'Actual Revenue (Total)': '{:,.0f}',
            'Growth': '{:.2f}%'
        }), use_container_width=True)

else:
    st.warning("Data tidak tersedia atau sheet 'app_data' kosong.")
