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
            'Target Revenue', 'Actual Revenue (Total)', 'Actual Revenue (Opt)', 'Actual Revenue (Ipt)',
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

    # Perhitungan Metrik Tambahan
    filtered_df['Total OPT'] = filtered_df['Volume OPT JKN'] + filtered_df['Volume OPT Non JKN']
    filtered_df['Total IPT'] = filtered_df['Volume IPT JKN'] + filtered_df['Volume IPT Non JKN']
    filtered_df['Total IGD'] = filtered_df['Volume IGD JKN'] + filtered_df['Volume IGD Non JKN']
    
    # Perhitungan Growth
    for col in ['Actual Revenue (Total)', 'Total OPT', 'Total IPT', 'Total IGD']:
        filtered_df[f'{col}_Growth'] = filtered_df.groupby('Cabang')[col].pct_change() * 100

    st.title("📊 Dashboard Performa Helsa-BR 2025")
    
    colors = {
        'Jatirahayu': {'base': '#AEC6CF', 'light': '#D1E1E6', 'dark': '#779ECB'},
        'Cikampek':   {'base': '#FFB7B2', 'light': '#FFD1CF', 'dark': '#E08E88'},
        'Citeureup':  {'base': '#B2F2BB', 'light': '#D5F9DA', 'dark': '#88C090'},
        'Ciputat':    {'base': '#CFC1FF', 'light': '#E1D9FF', 'dark': '#A694FF'}
    }

    # FUNGSI UNTUK MEMBUAT STACKED CHART (Volume & Revenue)
    def create_stacked_chart(df_data, title, col_top, col_bottom, col_total, col_growth_name, y_label, is_revenue=False):
        with st.container(border=True):
            st.subheader(title)
            fig = go.Figure()
            
            for i, cabang in enumerate(selected_cabang):
                branch_df = df_data[df_data['Cabang'] == cabang].copy()
                
                # Format Label Fungsi
                def fmt(val, suffix):
                    if val == 0: return ""
                    num = f"{val/1e9:.2f}M" if is_revenue else f"{int(val):,}"
                    return f"<b>{num}</b><br>({suffix})"

                # Trace 1: Bottom Segment (Non-JKN atau Opt)
                fig.add_trace(go.Bar(
                    x=branch_df['Bulan'], y=branch_df[col_bottom], name=cabang, legendgroup=cabang,
                    offsetgroup=cabang, marker_color=colors.get(cabang)['light'],
                    customdata=branch_df[col_total],
                    text=branch_df[col_bottom].apply(lambda x: fmt(x, "Opt" if is_revenue else "Non JKN")),
                    textposition='inside', insidetextanchor='middle', textangle=0,
                    textfont=dict(size=9, color='#444444'),
                    hovertemplate=f"<b>{cabang}</b><br>Total: %{{customdata:,.0f}}<extra></extra>"
                ))
                
                # Trace 2: Top Segment (JKN atau Ipt)
                fig.add_trace(go.Bar(
                    x=branch_df['Bulan'], y=branch_df[col_top], name=cabang, legendgroup=cabang, showlegend=False,
                    base=branch_df[col_bottom], offsetgroup=cabang, marker_color=colors.get(cabang)['dark'],
                    customdata=branch_df[col_total],
                    text=branch_df[col_top].apply(lambda x: fmt(x, "Ipt" if is_revenue else "JKN")),
                    textposition='inside', insidetextanchor='middle', textangle=0,
                    textfont=dict(color='white', size=9),
                    hovertemplate=f"<b>{cabang}</b><br>Total: %{{customdata:,.0f}}<extra></extra>"
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

            fig.update_layout(barmode='group', height=480, margin=dict(t=80, b=10),
                              yaxis_title=y_label,
                              yaxis=dict(range=[0, df_data[col_total].max() * 1.55]),
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
                        val = avg_val[cb]
                        display_val = f"Rp {val/1e9:.2f} M" if is_revenue else f"{int(val):,} Pasien"
                        st.markdown(f"<span style='color:{colors.get(cb)['base']};'>● <b>{cb}</b></span>", unsafe_allow_html=True)
                        st.write(display_val)

    # --- EKSEKUSI DASHBOARD ---

    # 1. Grafik Revenue (Stacked Opt vs Ipt)
    create_stacked_chart(filtered_df, "📈 Realisasi Revenue (Stacked Opt vs Ipt)", 
                         'Actual Revenue (Ipt)', 'Actual Revenue (Opt)', 'Actual Revenue (Total)', 
                         'Actual Revenue (Total)_Growth', "Revenue (IDR)", is_revenue=True)

    # 2. Grafik Volume OPT
    create_stacked_chart(filtered_df, "👥 Volume Outpatient (OPT)", 
                         'Volume OPT JKN', 'Volume OPT Non JKN', 'Total OPT', 
                         'Total OPT_Growth', "Volume OPT")

    # 3. Grafik Volume IPT (Ranap)
    create_stacked_chart(filtered_df, "🏥 Volume Inpatient (Ranap)", 
                         'Volume IPT JKN', 'Volume IPT Non JKN', 'Total IPT', 
                         'Total IPT_Growth', "Volume IPT")

    # 4. Grafik Volume IGD
    create_stacked_chart(filtered_df, "🚑 Volume IGD", 
                         'Volume IGD JKN', 'Volume IGD Non JKN', 'Total IGD', 
                         'Total IGD_Growth', "Volume IGD")

    with st.expander("🔍 Lihat Detail Data Mentah"):
        st.dataframe(filtered_df)
else:
    st.warning("Data tidak tersedia atau filter cabang kosong.")
