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
        # Membersihkan spasi pada nama kolom untuk mencegah KeyError
        raw_df.columns = raw_df.columns.str.strip()
        
        numeric_cols = [
            'Target Revenue', 'Actual Revenue (Total)', 'Actual Revenue (Opt)', 'Actual Revenue (Ipt)',
            'Volume OPT JKN', 'Volume OPT Non JKN',
            'Volume IPT JKN', 'Volume IPT Non JKN',
            'Volume IGD JKN', 'Volume IGD Non JKN',
            'Volume IGD to Ipt JKN', 'Volume IGD to Ipt Non JKN'
        ]
        
        for col in numeric_cols:
            if col in raw_df.columns:
                raw_df[col] = raw_df[col].astype(str).str.replace(r'[^\d]', '', regex=True)
                raw_df[col] = pd.to_numeric(raw_df[col], errors='coerce').fillna(0)
            else:
                # Membuat kolom kosong jika tidak ditemukan di Sheet
                raw_df[col] = 0
        
        return raw_df
    except Exception as e:
        st.error(f"Error Loading Data: {e}")
        return pd.DataFrame()

df = load_data()

if not df.empty:
    st.sidebar.header("🕹️ Filter Panel")
    all_cabang = list(df['Cabang'].unique()) if 'Cabang' in df.columns else []
    selected_cabang = st.sidebar.multiselect("Pilih Cabang:", all_cabang, default=all_cabang)
    
    month_order = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 
                   'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
    
    filtered_df = df[df['Cabang'].isin(selected_cabang)].copy()
    filtered_df['Bulan'] = pd.Categorical(filtered_df['Bulan'], categories=month_order, ordered=True)
    filtered_df = filtered_df.sort_values(['Cabang', 'Bulan'])

    # --- PERHITUNGAN METRIK ---
    filtered_df['Total OPT'] = filtered_df['Volume OPT JKN'] + filtered_df['Volume OPT Non JKN']
    filtered_df['Total IPT'] = filtered_df['Volume IPT JKN'] + filtered_df['Volume IPT Non JKN']
    filtered_df['Total IGD'] = filtered_df['Volume IGD JKN'] + filtered_df['Volume IGD Non JKN']
    filtered_df['Total IGD to Ipt'] = filtered_df['Volume IGD to Ipt JKN'] + filtered_df['Volume IGD to Ipt Non JKN']
    
    # Conversion Rate (CR)
    filtered_df['CR IGD to Ipt'] = np.where(
        filtered_df['Total IGD'] > 0, 
        (filtered_df['Total IGD to Ipt'] / filtered_df['Total IGD']) * 100, 
        0
    )
    
    # Growth Calculation
    for col in ['Actual Revenue (Total)', 'Total OPT', 'Total IPT', 'Total IGD', 'Total IGD to Ipt']:
        filtered_df[f'{col}_Growth'] = filtered_df.groupby('Cabang')[col].pct_change() * 100

    st.title("📊 Dashboard Performa Helsa-BR 2025")
    
    colors = {
        'Jatirahayu': {'base': '#AEC6CF', 'light': '#D1E1E6', 'dark': '#779ECB'},
        'Cikampek':   {'base': '#FFB7B2', 'light': '#FFD1CF', 'dark': '#E08E88'},
        'Citeureup':  {'base': '#B2F2BB', 'light': '#D5F9DA', 'dark': '#88C090'},
        'Ciputat':    {'base': '#CFC1FF', 'light': '#E1D9FF', 'dark': '#A694FF'}
    }

    def create_stacked_chart(df_data, title, col_top, col_bottom, col_total, col_growth_name, y_label, is_revenue=False, line_col=None):
        with st.container(border=True):
            st.subheader(title)
            fig = go.Figure()
            
            for i, cabang in enumerate(selected_cabang):
                branch_df = df_data[df_data['Cabang'] == cabang].copy()
                
                # Trace 1: Bottom (Non-JKN / Opt)
                fig.add_trace(go.Bar(
                    x=branch_df['Bulan'], y=branch_df[col_bottom], name=cabang, legendgroup=cabang,
                    offsetgroup=cabang, marker_color=colors.get(cabang)['light'],
                    customdata=branch_df[col_total],
                    text=branch_df[col_bottom].apply(lambda x: f"<b>{x/1e9:.2f}M</b><br>(Opt)" if is_revenue and x > 0 else (f"<b>{int(x):,}</b><br>(Non JKN)" if x > 0 else "")),
                    textposition='inside', insidetextanchor='middle', textangle=0, textfont=dict(size=9, color='#444444'),
                    hovertemplate=f"<b>{cabang}</b><br>Total: %{{customdata:,.0f}}<extra></extra>"
                ))
                
                # Trace 2: Top (JKN / Ipt)
                fig.add_trace(go.Bar(
                    x=branch_df['Bulan'], y=branch_df[col_top], name=cabang, legendgroup=cabang, showlegend=False,
                    base=branch_df[col_bottom], offsetgroup=cabang, marker_color=colors.get(cabang)['dark'],
                    customdata=branch_df[col_total],
                    text=branch_df[col_top].apply(lambda x: f"<b>{x/1e9:.2f}M</b><br>(Ipt)" if is_revenue and x > 0 else (f"<b>{int(x):,}</b><br>(JKN)" if x > 0 else "")),
                    textposition='inside', insidetextanchor='middle', textangle=0, textfont=dict(color='white', size=9),
                    hovertemplate=f"<b>{cabang}</b><br>Total: %{{customdata:,.0f}}<extra></extra>"
                ))
                
                # Growth Label
                growth_vals = branch_df[col_growth_name]
                g_labels = [f"<b>{'▲' if v >= 0 else '▼'} {abs(v):.1f}%</b>" if pd.notnull(v) else "" for v in growth_vals]
                g_colors = ["#059669" if v >= 0 else "#dc2626" if pd.notnull(v) else "rgba(0,0,0,0)" for v in growth_vals]
                
                fig.add_trace(go.Bar(
                    x=branch_df['Bulan'], y=branch_df[col_total], offsetgroup=cabang, showlegend=False,
                    text=g_labels, textposition='outside', textfont=dict(color=g_colors, size=11),
                    marker_color='rgba(0,0,0,0)', hoverinfo='skip'
                ))

                # Line Chart for CR
                if line_col and line_col in branch_df:
                    fig.add_trace(go.Scatter(
                        x=branch_df['Bulan'], y=branch_df[line_col], name=f"CR {cabang}",
                        mode='lines+markers', line=dict(color=colors.get(cabang)['dark'], width=2),
                        yaxis="y2", hovertemplate=f"<b>CR {cabang}</b>: %{{y:.1f}}%<extra></extra>"
                    ))

            layout_args = dict(
                barmode='group', height=500, margin=dict(t=80, b=10),
                yaxis=dict(title=y_label, range=[0, df_data[col_total].max() * 1.55 if df_data[col_total].max() > 0 else 100]),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            if line_col:
                layout_args['yaxis2'] = dict(title="Conversion Rate (%)", overlaying="y", side="right", range=[0, 110], showgrid=False)
            
            fig.update_layout(**layout_args)
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
    create_stacked_chart(filtered_df, "📈 Realisasi Revenue (Opt vs Ipt)", 'Actual Revenue (Ipt)', 'Actual Revenue (Opt)', 'Actual Revenue (Total)', 'Actual Revenue (Total)_Growth', "Revenue (IDR)", is_revenue=True)
    create_stacked_chart(filtered_df, "👥 Volume Outpatient (OPT)", 'Volume OPT JKN', 'Volume OPT Non JKN', 'Total OPT', 'Total OPT_Growth', "Volume OPT")
    create_stacked_chart(filtered_df, "🏥 Volume Inpatient (Ranap)", 'Volume IPT JKN', 'Volume IPT Non JKN', 'Total IPT', 'Total IPT_Growth', "Volume IPT")
    create_stacked_chart(filtered_df, "🚑 Volume IGD", 'Volume IGD JKN', 'Volume IGD Non JKN', 'Total IGD', 'Total IGD_Growth', "Volume IGD")
    
    # Konversi IGD ke Ipt
    create_stacked_chart(filtered_df, "🎯 Konversi IGD ke Rawat Inap (Ipt)", 'Volume IGD to Ipt JKN', 'Volume IGD to Ipt Non JKN', 'Total IGD to Ipt', 'Total IGD to Ipt_Growth', "Volume IGD to Ipt", line_col='CR IGD to Ipt')

    # --- TABEL DATA MENTAH ---
    with st.expander("🔍 Lihat Detail Data Mentah"):
        st.dataframe(filtered_df)
else:
    st.warning("Data tidak tersedia. Mohon cek file Google Sheet Anda.")
