import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import calendar

# --- 1. KONFIGURASI DATA ---
SHEET_ID = '18Djb0QiE8uMgt_nXljFCZaMKHwii1pMzAtH96zGc_cI'
SHEET_NAME = 'app_data'
URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}'

st.set_page_config(page_title="Helsa-BR Performance Dashboard 2025", layout="wide")

MONTH_MAP = {
    'Januari': 1, 'Februari': 2, 'Maret': 3, 'April': 4, 'Mei': 5, 'Juni': 6,
    'Juli': 7, 'Agustus': 8, 'September': 9, 'Oktober': 10, 'November': 11, 'Desember': 12
}

@st.cache_data(ttl=300)
def load_data():
    try:
        raw_df = pd.read_csv(URL)
        raw_df.columns = raw_df.columns.str.strip()
        numeric_cols = [
            'Target Revenue', 'Actual Revenue (Total)', 'Actual Revenue (Opt)', 'Actual Revenue (Ipt)',
            'Volume OPT JKN', 'Volume OPT Non JKN', 'Volume IPT JKN', 'Volume IPT Non JKN',
            'Volume IGD JKN', 'Volume IGD Non JKN', 'Volume IGD to IPT JKN', 'Volume IGD to IPT Non JKN',
            'Pintu Poli'
        ]
        for col in numeric_cols:
            if col in raw_df.columns:
                raw_df[col] = raw_df[col].astype(str).str.replace(r'[^\d.]', '', regex=True)
                raw_df[col] = pd.to_numeric(raw_df[col], errors='coerce').fillna(0)
            elif col == 'Pintu Poli':
                raw_df[col] = 0
        return raw_df
    except Exception as e:
        st.error(f"Gagal memuat data: {e}")
        return pd.DataFrame()

def count_days(year, month_name):
    month_idx = MONTH_MAP.get(month_name, 1)
    matrix = calendar.monthcalendar(year, month_idx)
    mon_fri, saturdays = 0, 0
    for week in matrix:
        for d in range(0, 5): 
            if week[d] != 0: mon_fri += 1
        if week[5] != 0: saturdays += 1
    return mon_fri, saturdays

df = load_data()

if not df.empty:
    st.sidebar.header("🕹️ Panel Kontrol")
    all_cabang = list(df['Cabang'].unique())
    selected_cabang = st.sidebar.multiselect("Pilih Cabang:", all_cabang, default=all_cabang)
    
    month_order = list(MONTH_MAP.keys())
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
    
    capacity_data = []
    for _, row in filtered_df.iterrows():
        mf, sat = count_days(2025, row['Bulan'])
        pintu = row['Pintu Poli']
        monthly_cap = (mf * (pintu * 12 * 5)) + (sat * (pintu * 4 * 5))
        capacity_data.append(monthly_cap)
    
    filtered_df['Kapasitas Maks'] = capacity_data
    filtered_df['Utilisasi Poli'] = np.where(filtered_df['Kapasitas Maks'] > 0, (filtered_df['Total OPT'] / filtered_df['Kapasitas Maks']) * 100, 0)

    for col in ['Actual Revenue (Total)', 'Total OPT', 'Total IPT', 'Total IGD', 'Total IGD to IPT']:
        filtered_df[f'{col}_Growth'] = filtered_df.groupby('Cabang', observed=True)[col].pct_change() * 100

    st.title("📊 Dashboard Performa Helsa-BR 2025")
    
    colors = {
        'Jatirahayu': {'base': '#AEC6CF', 'light': '#D1E1E6', 'dark': '#779ECB'},
        'Cikampek':   {'base': '#FFB7B2', 'light': '#FFD1CF', 'dark': '#E08E88'},
        'Citeureup':  {'base': '#B2F2BB', 'light': '#D5F9DA', 'dark': '#88C090'},
        'Ciputat':    {'base': '#CFC1FF', 'light': '#E1D9FF', 'dark': '#A694FF'}
    }

    def create_stacked_chart(df_data, title, col_top, col_bottom, col_total, col_growth_name, y_label, is_revenue=False, target_col=None):
        with st.container(border=True):
            st.subheader(title)
            fig = go.Figure()
            for cb in selected_cabang:
                branch_df = df_data[df_data['Cabang'] == cb].copy()
                if branch_df.empty: continue
                
                # Format string untuk hover total
                branch_df['total_fmt'] = branch_df[col_total].apply(lambda x: f"Rp {x/1e9:.2f} M" if is_revenue else f"{int(x):,} Pasien")
                
                # Customdata: [Total Raw, Growth, Achievement, Total Formatted]
                ach_series = (branch_df[col_total] / branch_df[target_col] * 100).fillna(0) if target_col else np.zeros(len(branch_df))
                h_customdata = np.stack([branch_df[col_total], branch_df[col_growth_name].fillna(0), ach_series, branch_df['total_fmt']], axis=-1)

                h_template = f"<b>{cb}</b><br>Total: %{{customdata[3]}}<br>"
                if target_col: h_template += "Ach: %{customdata[2]:.1f}%<br>"
                h_template += "Growth: %{customdata[1]:.1f}%<extra></extra>"

                def fmt_txt(val, cat):
                    if val == 0: return ""
                    val_str = f"{val/1e9:.2f}M" if is_revenue else f"{int(val):,}"
                    return f"<b>{val_str}</b><br>({cat})"

                fig.add_trace(go.Bar(x=branch_df['Bulan'], y=branch_df[col_bottom], name=cb, legendgroup=cb, offsetgroup=cb, marker_color=colors.get(cb)['light'], customdata=h_customdata, text=branch_df[col_bottom].apply(lambda x: fmt_txt(x, "Opt" if is_revenue else "Non JKN")), textposition='inside', textangle=0, hovertemplate=h_template))
                fig.add_trace(go.Bar(x=branch_df['Bulan'], y=branch_df[col_top], name=cb, legendgroup=cb, showlegend=False, base=branch_df[col_bottom], offsetgroup=cb, marker_color=colors.get(cb)['dark'], customdata=h_customdata, text=branch_df[col_top].apply(lambda x: fmt_txt(x, "Ipt" if is_revenue else "JKN")), textposition='inside', textangle=0, hovertemplate=h_template))
                
                display_labels = []
                for idx in range(len(branch_df)):
                    g_val = branch_df[col_growth_name].iloc[idx]
                    g_txt = f"<span style='color:{('#059669' if g_val >= 0 else '#dc2626')}'><b>{('▲' if g_val >= 0 else '▼')} {abs(g_val):.1f}%</b></span>"
                    if target_col:
                        ach = ach_series.iloc[idx]
                        ach_txt = f"<span style='color:{('#059669' if ach >= 100 else '#dc2626')}'><b>{ach:.1f}%</b></span>"
                        display_labels.append(f"{ach_txt}<br>{g_txt}")
                    else: display_labels.append(g_txt)

                fig.add_trace(go.Bar(x=branch_df['Bulan'], y=branch_df[col_total], offsetgroup=cb, showlegend=False, text=display_labels, textposition='outside', textfont=dict(size=14), marker_color='rgba(0,0,0,0)', hoverinfo='skip', cliponaxis=False))

            max_v = df_data[col_total].max() if not df_data.empty else 0
            y_limit = max_v * 1.25 if max_v > 0 else 100
            yaxis_config = dict(title=y_label, range=[0, y_limit])
            if is_revenue:
                ticks = np.arange(0, y_limit + 1e9, 1e9)
                fig.update_yaxes(tickvals=ticks, ticktext=[f"{int(v/1e9)}M" for v in ticks])
            fig.update_layout(barmode='group', height=520, margin=dict(t=120, b=10), yaxis=yaxis_config, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True)
            
            # --- SUMMARY FOOTER (GRUP AVG & TOTAL) ---
            df_ok = df_data[df_data[col_total] > 0]
            if not df_ok.empty:
                avg_branch = df_ok.groupby('Cabang', observed=True)[col_total].mean()
                sum_branch = df_ok.groupby('Cabang', observed=True)[col_total].sum()
                monthly_group_totals = df_ok.groupby('Bulan', observed=True)[col_total].sum()
                group_avg = monthly_group_totals.mean() 
                group_total = sum_branch.sum()

                def disp_v(val): return f"Rp {val/1e9:.2f} M" if is_revenue else f"{int(val):,} Pasien"

                st.markdown(f"**Rata-rata {y_label} per Bulan:**")
                cols = st.columns(len(selected_cabang) + 1)
                for idx, cb in enumerate(selected_cabang):
                    with cols[idx]:
                        st.markdown(f"<span style='color:{colors.get(cb)['dark']};'>● <b>{cb}</b></span>", unsafe_allow_html=True)
                        st.write(disp_v(avg_branch.get(cb, 0)))
                cols[-1].markdown(f"### 🏆 Grup Avg\n**{disp_v(group_avg)}**")

                st.markdown(f"**Total {y_label} Keseluruhan:**")
                cols2 = st.columns(len(selected_cabang) + 1)
                for idx, cb in enumerate(selected_cabang):
                    with cols2[idx]:
                        st.markdown(f"<span style='color:{colors.get(cb)['dark']};'>● <b>{cb}</b></span>", unsafe_allow_html=True)
                        val = sum_branch.get(cb, 0)
                        suffix = f" <br><small>({(val/group_total*100):.1f}% Kontr.)</small>" if is_revenue and group_total > 0 else ""
                        st.markdown(f"{disp_v(val)}{suffix}", unsafe_allow_html=True)
                cols2[-1].markdown(f"### 🏛️ Grup Total\n**{disp_v(group_total)}**")

    # --- EKSEKUSI GRAFIK ---
    create_stacked_chart(filtered_df, "📈 Realisasi Revenue (Opt vs Ipt)", 'Actual Revenue (Ipt)', 'Actual Revenue (Opt)', 'Actual Revenue (Total)', 'Actual Revenue (Total)_Growth', "Revenue", is_revenue=True, target_col='Target Revenue')
    create_stacked_chart(filtered_df, "👥 Volume Outpatient (OPT)", 'Volume OPT JKN', 'Volume OPT Non JKN', 'Total OPT', 'Total OPT_Growth', "Volume OPT")
    
    # --- ANALISIS KAPASITAS RAJAL ---
    with st.container(border=True):
        st.subheader("⚙️ Analisis Kapasitas Produksi Rawat Jalan (2025)")
        fig_cap = go.Figure()
        for cb in selected_cabang:
            branch_df = filtered_df[filtered_df['Cabang'] == cb]
            if branch_df.empty: continue
            
            # Bar: Kapasitas Maks. Per Bulan
            fig_cap.add_trace(go.Bar(x=branch_df['Bulan'], y=branch_df['Kapasitas Maks'], name=f"Kapasitas Maks. ({cb})", offsetgroup=cb, marker_color=colors.get(cb)['light'], text=branch_df['Kapasitas Maks'].apply(lambda x: f"<b>{int(x):,}</b>"), textposition='inside', textangle=0, hovertemplate=f"<b>{cb}</b><br>Kapasitas Maks: %{{y:,.0f}}<extra></extra>"))
            
            # Line: Volume Rajal Aktual (Nilai dimunculkan)
            fig_cap.add_trace(go.Scatter(x=branch_df['Bulan'], y=branch_df['Total OPT'], name=f"Volume Rajal ({cb})", mode='markers+lines+text', offsetgroup=cb, text=branch_df['Total OPT'].apply(lambda x: f"<b>{int(x):,}</b>"), textposition="top center", line=dict(color=colors.get(cb)['dark'], width=3), hovertemplate=f"<b>{cb}</b><br>Volume Rajal: %{{y:,.0f}}<extra></extra>"))

            # Label Atas: Utilisasi (%)
            fig_cap.add_trace(go.Bar(x=branch_df['Bulan'], y=branch_df['Kapasitas Maks'], offsetgroup=cb, showlegend=False, text=branch_df['Utilisasi Poli'].apply(lambda x: f"<b>{x:.1f}%</b>"), textposition='outside', textfont=dict(size=14), marker_color='rgba(0,0,0,0)', hoverinfo='skip', cliponaxis=False))
        
        y_max = filtered_df['Kapasitas Maks'].max() if not filtered_df.empty else 100
        fig_cap.update_layout(barmode='group', height=520, margin=dict(t=100, b=10), yaxis=dict(title="Jumlah Pasien", range=[0, y_max * 1.25]), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_cap, use_container_width=True)

    create_stacked_chart(filtered_df, "🏥 Volume Inpatient (Ranap)", 'Volume IPT JKN', 'Volume IPT Non JKN', 'Total IPT', 'Total IPT_Growth', "Volume IPT")
    create_stacked_chart(filtered_df, "🚑 Volume IGD", 'Volume IGD JKN', 'Volume IGD Non JKN', 'Total IGD', 'Total IGD_Growth', "Volume IGD")
    create_stacked_chart(filtered_df, "🎯 Volume Konversi IGD ke Rawat Inap (Ranap)", 'Volume IGD to IPT JKN', 'Volume IGD to IPT Non JKN', 'Total IGD to IPT', 'Total IGD to IPT_Growth', "Volume Konversi")

    with st.container(border=True):
        st.subheader("📊 Tren Conversion Rate (CR) IGD ke Ranap")
        fig_cr = go.Figure()
        for cb in selected_cabang:
            branch_df = filtered_df[filtered_df['Cabang'] == cb]
            if not branch_df.empty:
                fig_cr.add_trace(go.Scatter(x=branch_df['Bulan'], y=branch_df['CR IGD to IPT'], name=cb, mode='lines+markers+text', text=branch_df['CR IGD to IPT'].apply(lambda x: f"<b>{x:.1f}%</b>" if x > 0 else ""), textposition="top center", line=dict(color=colors.get(cb)['dark'], width=3)))
        fig_cr.update_layout(height=400, yaxis_title="Persentase (%)", yaxis=dict(range=[0, 115]), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_cr, use_container_width=True)
else:
    st.warning("Data tidak tersedia.")
