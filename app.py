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
            'Volume OPT JKN', 'Volume OPT Non JKN', 'Volume IPT JKN', 'Volume IPT Non JKN',
            'Volume IGD JKN', 'Volume IGD Non JKN', 'Volume IGD to IPT JKN', 'Volume IGD to IPT Non JKN'
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
    # --- SIDEBAR FILTER ---
    st.sidebar.header("🕹️ Panel Kontrol")
    all_cabang = list(df['Cabang'].unique())
    selected_cabang = st.sidebar.multiselect("Pilih Cabang:", all_cabang, default=all_cabang)
    
    month_order = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 
                   'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
    available_months = [m for m in month_order if m in df['Bulan'].unique()]
    selected_months = st.sidebar.multiselect("Pilih Periode Bulan:", available_months, default=available_months)
    
    filtered_df = df[(df['Cabang'].isin(selected_cabang)) & (df['Bulan'].isin(selected_months))].copy()
    filtered_df['Bulan'] = pd.Categorical(filtered_df['Bulan'], categories=selected_months, ordered=True)
    filtered_df = filtered_df.sort_values(['Cabang', 'Bulan'])

    # --- PERHITUNGAN METRIK ---
    filtered_df['Total OPT'] = filtered_df['Volume OPT JKN'] + filtered_df['Volume OPT Non JKN']
    filtered_df['Total IPT'] = filtered_df['Volume IPT JKN'] + filtered_df['Volume IPT Non JKN']
    filtered_df['Total IGD'] = filtered_df['Volume IGD JKN'] + filtered_df['Volume IGD Non JKN']
    filtered_df['Total IGD to IPT'] = filtered_df['Volume IGD to IPT JKN'] + filtered_df['Volume IGD to IPT Non JKN']
    filtered_df['CR IGD to IPT'] = np.where(filtered_df['Total IGD'] > 0, (filtered_df['Total IGD to IPT'] / filtered_df['Total IGD']) * 100, 0)
    
    for col in ['Actual Revenue (Total)', 'Total OPT', 'Total IPT', 'Total IGD', 'Total IGD to IPT']:
        filtered_df[f'{col}_Growth'] = filtered_df.groupby('Cabang')[col].pct_change() * 100

    st.title("📊 Dashboard Performa Helsa-BR 2025")
    
    colors = {
        'Jatirahayu': {'base': '#AEC6CF', 'light': '#D1E1E6', 'dark': '#779ECB'},
        'Cikampek':   {'base': '#FFB7B2', 'light': '#FFD1CF', 'dark': '#E08E88'},
        'Citeureup':  {'base': '#B2F2BB', 'light': '#D5F9DA', 'dark': '#88C090'},
        'Ciputat':    {'base': '#CFC1FF', 'light': '#E1D9FF', 'dark': '#A694FF'}
    }

    # FUNGSI UNIVERSAL STACKED BAR
    def create_stacked_chart(df_data, title, col_top, col_bottom, col_total, col_growth_name, y_label, is_revenue=False, target_col=None):
        with st.container(border=True):
            st.subheader(title)
            fig = go.Figure()
            
            for i, cabang in enumerate(selected_cabang):
                branch_df = df_data[df_data['Cabang'] == cabang].copy()
                if branch_df.empty: continue
                
                def fmt_txt(val, cat):
                    if val == 0: return ""
                    val_str = f"{val/1e9:.2f}M" if is_revenue else f"{int(val):,}"
                    return f"<b>{val_str}</b><br>({cat})"

                # Bar Segments
                fig.add_trace(go.Bar(x=branch_df['Bulan'], y=branch_df[col_bottom], name=cabang, legendgroup=cabang, offsetgroup=cabang, marker_color=colors.get(cabang)['light'], customdata=branch_df[col_total], text=branch_df[col_bottom].apply(lambda x: fmt_txt(x, "Opt" if is_revenue else "Non JKN")), textposition='inside', insidetextanchor='middle', textangle=0, textfont=dict(size=9, color='#444444'), hovertemplate=f"<b>{cabang}</b><br>Total: %{{customdata:,.0f}}<extra></extra>"))
                fig.add_trace(go.Bar(x=branch_df['Bulan'], y=branch_df[col_top], name=cabang, legendgroup=cabang, showlegend=False, base=branch_df[col_bottom], offsetgroup=cabang, marker_color=colors.get(cabang)['dark'], customdata=branch_df[col_total], text=branch_df[col_top].apply(lambda x: fmt_txt(x, "Ipt" if is_revenue else "JKN")), textposition='inside', insidetextanchor='middle', textangle=0, textfont=dict(color='white', size=9), hovertemplate=f"<b>{cabang}</b><br>Total: %{{customdata:,.0f}}<extra></extra>"))
                
                # --- LOGIKA LABEL ATAS (FONT SIZE 14) ---
                growth_vals = branch_df[col_growth_name]
                display_labels = []
                for idx, g_val in enumerate(growth_vals):
                    symbol = "▲" if g_val >= 0 else "▼"
                    g_color = "#059669" if g_val >= 0 else "#dc2626"
                    g_txt = f"<span style='color:{g_color}'><b>{symbol} {abs(g_val):.1f}%</b></span>"
                    
                    if target_col and target_col in branch_df:
                        actual = branch_df[col_total].iloc[idx]
                        target = branch_df[target_col].iloc[idx]
                        ach = (actual / target * 100) if target > 0 else 0
                        ach_color = "#059669" if ach >= 100 else "#dc2626"
                        # HANYA TAMPILKAN PERSENTASE TANPA "Ach:"
                        ach_txt = f"<span style='color:{ach_color}'><b>{ach:.1f}%</b></span>"
                        display_labels.append(f"{ach_txt}<br>{g_txt}")
                    else:
                        display_labels.append(g_txt)

                fig.add_trace(go.Bar(x=branch_df['Bulan'], y=branch_df[col_total], offsetgroup=cabang, showlegend=False, text=display_labels, textposition='outside', textfont=dict(size=14), marker_color='rgba(0,0,0,0)', hoverinfo='skip', cliponaxis=False))

            # Autoscale 1.35x
            max_v = df_data[col_total].max() if not df_data.empty else 0
            y_limit = max_v * 1.35 if max_v > 0 else 100
            yaxis_config = dict(title=y_label, range=[0, y_limit])
            if is_revenue:
                ticks = np.arange(0, y_limit + 1e9, 1e9)
                fig.update_yaxes(tickvals=ticks, ticktext=[f"{int(v/1e9)}M" for v in ticks])

            fig.update_layout(barmode='group', height=520, margin=dict(t=120, b=10), yaxis=yaxis_config, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True)
            
            # --- SUMMARY FOOTER (CABANG + GRUP) ---
            df_ok = df_data[df_data[col_total] > 0]
            if not df_ok.empty:
                avg_branch = df_ok.groupby('Cabang', observed=True)[col_total].mean()
                sum_branch = df_ok.groupby('Cabang', observed=True)[col_total].sum()
                group_avg = df_ok[col_total].mean()
                group_total = df_ok[col_total].sum()

                def disp_v(val): return f"Rp {val/1e9:.2f} M" if is_revenue else f"{int(val):,} Pasien"

                # Row 1: Rata-rata
                st.markdown(f"**Rata-rata {y_label} per Bulan ({', '.join(selected_months)}):**")
                cols = st.columns(len(selected_cabang) + 1)
                for idx, cb in enumerate(selected_cabang):
                    with cols[idx]:
                        st.markdown(f"<span style='color:{colors.get(cb)['dark']};'>● <b>{cb}</b></span>", unsafe_allow_html=True)
                        st.write(disp_v(avg_branch.get(cb, 0)))
                with cols[-1]:
                    st.markdown("### 🏆 Grup Avg")
                    st.markdown(f"**{disp_v(group_avg)}**")

                # Row 2: Total
                st.markdown(f"**Total {y_label} Terpilih:**")
                cols2 = st.columns(len(selected_cabang) + 1)
                for idx, cb in enumerate(selected_cabang):
                    with cols2[idx]:
                        st.markdown(f"<span style='color:{colors.get(cb)['dark']};'>● <b>{cb}</b></span>", unsafe_allow_html=True)
                        val = sum_branch.get(cb, 0)
                        suffix = f" <br><small>({(val/group_total*100):.1f}% Kontribusi)</small>" if is_revenue and group_total > 0 else ""
                        st.markdown(f"{disp_v(val)}{suffix}", unsafe_allow_html=True)
                with cols2[-1]:
                    st.markdown("### 🏛️ Grup Total")
                    st.markdown(f"**{disp_v(group_total)}**")

    # --- EKSEKUSI ---
    create_stacked_chart(filtered_df, "📈 Realisasi Revenue (Stacked Opt vs Ipt)", 'Actual Revenue (Ipt)', 'Actual Revenue (Opt)', 'Actual Revenue (Total)', 'Actual Revenue (Total)_Growth', "Revenue", is_revenue=True, target_col='Target Revenue')
    create_stacked_chart(filtered_df, "👥 Volume Outpatient (OPT)", 'Volume OPT JKN', 'Volume OPT Non JKN', 'Total OPT', 'Total OPT_Growth', "Volume OPT")
    create_stacked_chart(filtered_df, "🏥 Volume Inpatient (Ranap)", 'Volume IPT JKN', 'Volume IPT Non JKN', 'Total IPT', 'Total IPT_Growth', "Volume IPT")
    create_stacked_chart(filtered_df, "🚑 Volume IGD", 'Volume IGD JKN', 'Volume IGD Non JKN', 'Total IGD', 'Total IGD_Growth', "Volume IGD")
    create_stacked_chart(filtered_df, "🎯 Volume Konversi IGD ke Rawat Inap (Ranap)", 'Volume IGD to IPT JKN', 'Volume IGD to IPT Non JKN', 'Total IGD to IPT', 'Total IGD to IPT_Growth', "Volume Konversi")

    with st.container(border=True):
        st.subheader("📊 Tren Conversion Rate (CR) IGD ke Ranap")
        fig_cr = go.Figure()
        for cb in selected_cabang:
            branch_df = filtered_df[filtered_df['Cabang'] == cb]
            if not branch_df.empty:
                fig_cr.add_trace(go.Scatter(x=branch_df['Bulan'], y=branch_df['CR IGD to IPT'], name=cb, mode='lines+markers+text', text=branch_df['CR IGD to IPT'].apply(lambda x: f"<b>{x:.1f}%</b>" if x > 0 else ""), textposition="top center", line=dict(color=colors.get(cb)['dark'], width=3), hovertemplate=f"<b>{cb}</b><br>CR: %{{y:.2f}}%<extra></extra>"))
        fig_cr.update_layout(height=400, yaxis_title="Persentase (%)", yaxis=dict(range=[0, 115]), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_cr, use_container_width=True)

    with st.expander("🔍 Lihat Detail Data Mentah"):
        st.dataframe(filtered_df)
else:
    st.warning("Data tidak tersedia atau filter cabang/bulan kosong.")
