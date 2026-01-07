import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ... (kode load_data Anda sebelumnya) ...

def show_growth_chart(df):
    st.subheader("📈 Pertumbuhan Revenue per Cabang 2025")
    
    # 1. Pre-processing: Pastikan urutan bulan benar
    month_order = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 
                   'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
    df['Bulan'] = pd.Categorical(df['Bulan'], categories=month_order, ordered=True)
    df = df.sort_values(['Cabang', 'Bulan'])

    # 2. Hitung Growth (%) per Cabang
    df['Growth'] = df.groupby('Cabang')['Actual Revenue (Total)'].pct_change() * 100

    # 3. Buat Plotly Figure
    fig = go.Figure()
    
    colors = {'Jatirahayu': '#3b82f6', 'Cikampek': '#8b5cf6', 'Citeureup': '#6366f1', 'Ciputat': '#10b981'}

    for cabang in df['Cabang'].unique():
        branch_df = df[df['Cabang'] == cabang]
        
        # Tambahkan Bar Chart
        fig.add_trace(go.Bar(
            x=branch_df['Bulan'],
            y=branch_df['Actual Revenue (Total)'],
            name=cabang,
            marker_color=colors.get(cabang, '#888888'),
            text=branch_df['Actual Revenue (Total)'].apply(lambda x: f"{x/1e6:.1f}M"),
            textposition='auto',
        ))

        # Tambahkan Indikator Growth (Arrow & Percentage)
        for i, row in branch_df.iterrows():
            if pd.notnull(row['Growth']):
                color = "green" if row['Growth'] >= 0 else "red"
                symbol = "▲" if row['Growth'] >= 0 else "▼"
                
                fig.add_annotation(
                    x=row['Bulan'],
                    y=row['Actual Revenue (Total)'],
                    text=f"{symbol} {row['Growth']:.1f}%",
                    showarrow=False,
                    yshift=20, # Posisi di atas bar
                    font=dict(color=color, size=10),
                    xanchor='center'
                )

    fig.update_layout(
        barmode='group',
        xaxis_title="Bulan",
        yaxis_title="Revenue (IDR)",
        legend_title="Cabang",
        hovermode="x unified",
        height=600
    )
    
    st.plotly_chart(fig, use_container_width=True)

# Panggil fungsi di dalam main app
if not df.empty:
    show_growth_chart(filtered_df)
