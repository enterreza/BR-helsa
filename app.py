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
                # Membersihkan karakter non-angka
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
    
    # Pre-processing Data
    month_order = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 
                   'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
    
    filtered_df = df[df['Cabang'].isin(selected_cabang)].copy()
    filtered_df['Bulan'] = pd.Categorical(filtered_df['Bulan'], categories=month_order, ordered=True)
    filtered_df = filtered_df.sort_values(['Cabang', 'Bulan'])

    # Hitung Growth MoM
    filtered_df['Growth'] = filtered_df.groupby('Cabang')['Actual Revenue (Total)'].pct_change() * 100

    # --- HEADER ---
    st.title("📊 Dashboard Pertumbuhan & Realisasi Helsa-BR")
    
    # --- 4. VISUALISASI CHART ---
    with st.container(border=True):
        st.subheader("📈 Realisasi Revenue & Pertumbuhan per Cabang")
        
        fig = go.Figure()
        colors = {
            'Jatirahayu': '#3b82f6', 'Cikampek': '#8b5cf6', 
            'Citeureup': '#6366f1', 'Ciputat': '#10b981'
        }

        for i, cabang in enumerate(selected_cabang):
            branch_df = filtered_df[filtered_df['Cabang'] == cabang].copy()
            
            # Label Nominal (Inside) - Miliar
            nominal_labels = branch_df['Actual Revenue (Total)'].apply(
                lambda x: f"<b>{x/1e9:.2f}M</b>" if x > 0 else ""
            )
            
            # Label Growth (Outside)
            growth_labels = []
            growth_colors = []
            for val in branch_df['Growth']:
                if pd.isna(val):
                    growth_labels.append("")
                    growth_colors.append("rgba(0,0,0,0)")
                else:
                    symbol = "▲" if val >= 0 else "▼"
                    color = "#059669" if val >= 0 else "#dc2626"
                    growth_labels.append(f"<b>{symbol} {abs(val):.1f}%</b>")
                    growth_colors.append(color)
            
            # Trace Bar Utama (Nominal)
            fig.add_trace(go.Bar(
                x=branch_df['Bulan'],
                y=branch_df['Actual Revenue (Total)'],
                name=cabang,
                offsetgroup=cabang,
                marker_color=colors.get(cabang, '#94a3b8'),
                text=nominal_labels,
                textposition='inside',
                insidetextanchor='middle',
                textfont=dict(color='white', size=11),
                hovertemplate=f"<b>{cabang}</b><br>Actual: Rp %{{y:,.0f}}<extra></extra>"
            ))

            # Trace Bar Transparan (Growth)
            fig.add_trace(go.Bar(
                x=branch_df['Bulan'],
                y=branch_df['Actual Revenue (Total)'],
                offsetgroup=cabang, 
                text=growth_labels,
                textposition='outside',
                textfont=dict(color=growth_colors, size=11),
                marker_color='rgba(0,0,0,0)',
                showlegend=False,
                hoverinfo='skip'
            ))

        fig.update_layout(
            barmode='group', 
            height=500,
            margin=dict(t=50, b=10),
            xaxis_title="",
            yaxis_title="Total Revenue (IDR)",
            yaxis=dict(range=[0, filtered_df['Actual Revenue (Total)'].max() * 1.35]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified"
        )
        
        st.plotly_chart(fig, use_container_width=True)

        # --- FOOTER: RATA-RATA REVENUE (DINAMIS) ---
        st.markdown("---")
        st.markdown("**Rata-rata Revenue per Bulan (Berdasarkan Data Terisi):**")
        
        # LOGIKA PEMBAGI: Hanya menghitung baris yang memiliki nilai > 0
        df_terisi = filtered_df[filtered_df['Actual Revenue (Total)'] > 0]
        avg_revenue = df_terisi.groupby('Cabang')['Actual Revenue (Total)'].mean()
        
        cols = st.columns(len(selected_cabang))
        for idx, cb in enumerate(selected_cabang):
            if cb in avg_revenue:
                val = avg_revenue[cb]
                # Hitung jumlah bulan terisi untuk info tambahan
                count_bulan = len(df_terisi[df_terisi['Cabang'] == cb])
                with cols[idx]:
                    st.markdown(f"<span style='color:{colors.get(cb, '#888888')}; font-weight:bold;'>● {cb}</span>", unsafe_allow_html=True)
                    st.write(f"Rp {val/1e9:.2f} Miliar")
                    st.caption(f"(Rata-rata {count_bulan} bulan)")

    # --- TABEL DETAIL ---
    with st.expander("🔍 Lihat Detail Data Mentah"):
        st.dataframe(filtered_df)
else:
    st.warning("Menunggu data dari Google Sheets...")
