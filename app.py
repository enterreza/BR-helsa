import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. Konfigurasi Halaman
st.set_page_config(page_title="Helsa-BR Performance Dashboard", layout="wide")

# 2. Simulasi/Pre-processing Data (Berdasarkan Gambar)
# Untuk implementasi asli, Anda bisa mengunggah CSV hasil konversi gambar tersebut
@st.cache_data
def get_data():
    # Contoh struktur data yang diekstrak dari gambar Anda
    data = {
        'Bulan': ['Januari', 'Januari', 'Februari', 'Februari', 'Maret', 'Maret'],
        'Cabang': ['JTR', 'CKP', 'JTR', 'CKP', 'JTR', 'CKP'],
        'Revenue': [4808448030, 3606930137, 4595869086, 3339207043, 4754418522, 3338485790],
        'Target': [4582359690, 3718951550, 4547766414, 3355596763, 4704099891, 3718951550],
        'EBITDA': [1358701122, 837308669, 1213814344, 658711010, 1154468261, 658621644],
        'BOR_JKN': [72.0, 67.0, 63.0, 66.0, 69.0, 63.0]
    }
    return pd.DataFrame(data)

df = get_data()

# 3. Sidebar - Filter
st.sidebar.header("Filter Dashboard")
selected_cabang = st.sidebar.multiselect("Pilih Cabang:", df['Cabang'].unique(), default=df['Cabang'].unique())

filtered_df = df[df['Cabang'].isin(selected_cabang)]

# 4. Header & KPI Utama
st.title("🏥 Dashboard Realisasi Operasional & Keuangan")
st.markdown("Visualisasi performa bulanan berdasarkan data laporan Helsa-BR 2025.")

col1, col2, col3 = st.columns(3)
with col1:
    total_rev = filtered_df['Revenue'].sum()
    st.metric("Total Revenue (YTD)", f"IDR {total_rev:,.0f}")
with col2:
    avg_ebitda = filtered_df['EBITDA'].mean()
    st.metric("Avg EBITDA", f"IDR {avg_ebitda:,.0f}")
with col3:
    avg_bor = filtered_df['BOR_JKN'].mean()
    st.metric("Avg BOR JKN", f"{avg_bor:.2f}%")

# 5. Visualisasi Timeline Performa (Revenue vs Target)
st.subheader("📈 Timeline Pencapaian Revenue vs Target")
fig_rev = go.Figure()

for cabang in selected_cabang:
    branch_data = filtered_df[filtered_df['Cabang'] == cabang]
    fig_rev.add_trace(go.Bar(x=branch_data['Bulan'], y=branch_data['Revenue'], name=f"Revenue {cabang}"))
    fig_rev.add_trace(go.Scatter(x=branch_data['Bulan'], y=branch_data['Target'], name=f"Target {cabang}", mode='lines+markers'))

fig_rev.update_layout(barmode='group', hovermode="x unified")
st.plotly_chart(fig_rev, use_container_width=True)

# 6. Detail Operasional (Misal: BOR & Volume)
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📉 Tren EBITDA per Bulan")
    fig_ebitda = px.line(filtered_df, x="Bulan", y="EBITDA", color="Cabang", markers=True)
    st.plotly_chart(fig_ebitda, use_container_width=True)

with col_right:
    st.subheader("🏨 Bed Occupancy Rate (BOR)")
    fig_bor = px.bar(filtered_df, x="Bulan", y="BOR_JKN", color="Cabang", barmode="group")
    st.plotly_chart(fig_bor, use_container_width=True)
