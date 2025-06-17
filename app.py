'''
pip install -r requirements.txt
streamlit run app.py
'''

import streamlit as st
import time
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from utils import fetch_data, add_technical_indicators, linear_regression, kirim_telegram
import base64

print(hasattr(st, "modal"))

# --- Session State Initialization (HANYA untuk alert) ---
if 'show_alert' not in st.session_state:
    st.session_state.show_alert = False
if 'alert_start_time' not in st.session_state:
    st.session_state.alert_start_time = None

# Langsung ke Dashboard
st.title("📊 Crypto IDX -> CRY/IDX")

# st.write("Selamat datang di analisa regresi linier Crypto IDX.")

# --- Sidebar Settings ---
st.sidebar.markdown("---")

st.sidebar.title("Settings")
pair_code = st.sidebar.text_input("Asset Pair", value="CRYIDX.B")
timeframe = st.sidebar.selectbox("Timeframe (menit)", ["30s", "1", "5", "15"], index=0)
refresh_interval = st.sidebar.slider("Refresh Interval (detik)", 5, 60, 10)
theme = st.sidebar.radio("Theme", ("Dark", "Light"))
run = st.sidebar.toggle("Start / Stop", value=False)

bot_token = st.sidebar.text_input("Telegram Bot Token", type="password")
chat_id = st.sidebar.text_input("Telegram Chat ID")
data_length = 30

def play_alert_sound(file_path="alert.mp3"):
    with open(file_path, "rb") as audio_file:
        audio_bytes = audio_file.read()
        b64_audio = base64.b64encode(audio_bytes).decode()
        audio_html = f"""
        <audio autoplay>
            <source src="data:audio/mp3;base64,{b64_audio}" type="audio/mp3">
            Your browser does not support the audio element.
        </audio>
        """
        st.markdown(audio_html, unsafe_allow_html=True)

def plot_regresi(df, hasil_regresi, theme):
    fig = go.Figure()

    fig.add_trace(go.Scatter(x=df['datetime'], y=df['close'], mode='lines', name='Close', line=dict(color='lightblue')))
    fig.add_trace(go.Scatter(x=df['datetime'], y=df['high'], mode='lines', name='High', line=dict(color='orange')))
    fig.add_trace(go.Scatter(x=df['datetime'], y=df['low'], mode='lines', name='Low', line=dict(color='lightgreen')))

    fig.add_trace(go.Scatter(x=df['datetime'], y=df['SMA20'], mode='lines', name='SMA20', line=dict(color='orange', dash='dash')))
    fig.add_trace(go.Scatter(x=df['datetime'], y=df['EMA20'], mode='lines', name='EMA20', line=dict(color='magenta', dash='dash')))

    fig.add_trace(go.Scatter(x=df['datetime'], y=hasil_regresi['prediksi'], mode='lines', name='Linear Regression', line=dict(color='red', dash='dot')))

    colors = ['green', 'orange', 'purple', 'brown', 'maroon', 'blue', 'red']
    for idx, (atas, bawah) in enumerate(zip(hasil_regresi['toleransi_atas'], hasil_regresi['toleransi_bawah'])):
        fig.add_trace(go.Scatter(x=df['datetime'], y=atas, mode='lines', name=f'Toleransi {idx+1} Atas', line=dict(color=colors[idx % len(colors)], dash='dot')))
        fig.add_trace(go.Scatter(x=df['datetime'], y=bawah, mode='lines', name=f'Toleransi {idx+1} Bawah', line=dict(color=colors[idx % len(colors)], dash='dot')))

    if len(hasil_regresi['toleransi_atas']) >= 2:
        atas_bawah = hasil_regresi['toleransi_atas'][-2]
        atas_atas = hasil_regresi['toleransi_atas'][-1]
        fig.add_trace(go.Scatter(x=df['datetime'], y=atas_atas, fill=None, mode='lines', line=dict(width=0), showlegend=False))
        fig.add_trace(go.Scatter(x=df['datetime'], y=atas_bawah, fill='tonexty', mode='lines', line=dict(width=0), fillcolor='rgba(255,0,0,0.1)', name='Zona Merah'))

    if len(hasil_regresi['toleransi_bawah']) >= 2:
        bawah_atas = hasil_regresi['toleransi_bawah'][-2]
        bawah_bawah = hasil_regresi['toleransi_bawah'][-1]
        fig.add_trace(go.Scatter(x=df['datetime'], y=bawah_bawah, fill=None, mode='lines', line=dict(width=0), showlegend=False))
        fig.add_trace(go.Scatter(x=df['datetime'], y=bawah_atas, fill='tonexty', mode='lines', line=dict(width=0), fillcolor='rgba(0,0,255,0.1)', name='Zona Biru'))

    fig.update_layout(
        template="plotly_dark" if theme == "Dark" else "plotly_white",
        title="Price + Regression Bands",
        xaxis_title="Datetime",
        yaxis_title="Price",
        yaxis=dict(tickformat=".8f"),  
        height=600,
        legend_title="Legend",
        showlegend=False
    )
    return fig

def plot_macd_rsi(df, theme):
    fig = go.Figure()

    fig.add_trace(go.Scatter(x=df['datetime'], y=df['MACD'], mode='lines', name='MACD', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=df['datetime'], y=df['Signal_Line'], mode='lines', name='Signal Line', line=dict(color='red', dash='dash')))

    fig.update_layout(
        template="plotly_dark" if theme == "Dark" else "plotly_white",
        title="MACD & RSI",
        xaxis_title="Datetime",
        yaxis_title="MACD",
        height=400,
        legend_title="Legend",
    )

    fig.add_trace(go.Scatter(x=df['datetime'], y=df['RSI'], mode='lines', name='RSI', line=dict(color='green'), yaxis='y2'))

    fig.update_layout(
        yaxis2=dict(
            title='RSI',
            overlaying='y',
            side='right',
            range=[0, 100],
            showgrid=False
        ),
        shapes=[
            dict(type='line', xref='paper', x0=0, x1=1, yref='y2', y0=70, y1=70, line=dict(color='red', dash='dash')),
            dict(type='line', xref='paper', x0=0, x1=1, yref='y2', y0=30, y1=30, line=dict(color='blue', dash='dash'))
        ]
    )
    return fig

# --- Main Loop ---
if run:
    placeholder = st.empty()
    aa = 1

    if 'slope_history' not in st.session_state:
        st.session_state.slope_history = []

    while True:
        raw_data = fetch_data(pair_code, timeframe)
        if len(raw_data) < 30:
            raw_data = fetch_data(pair_code, timeframe, 1)

        if raw_data is None:
            st.error("Gagal mendapatkan data. Program berhenti.")
            time.sleep(5)
            continue

        all_columns = ["timestamp", "open", "high", "low", "close", "col6", "col7", "col8", "col9", "col10", "col11"]
        df = pd.DataFrame(raw_data, columns=all_columns)

        if df.empty:
            st.error("Gagal ambil data, retrying...")
            time.sleep(5)
            continue

        df = df[["timestamp", "open", "high", "low", "close"]]
        df = df.tail(data_length)
        df = add_technical_indicators(df)
        hasil_regresi = linear_regression(df)

        TOLERANSI = 0.000001
        toleransi_levels = [TOLERANSI * i for i in range(1, 8)]

        toleransi_atas_tertinggi = hasil_regresi['prediksi'] + toleransi_levels[-1]
        toleransi_bawah_terendah = hasil_regresi['prediksi'] - toleransi_levels[-1]

        low_terakhir = df['low'].iloc[-1]
        high_terakhir = df['high'].iloc[-1]

        atas_bawah = hasil_regresi['toleransi_atas'][-2]
        atas_atas = hasil_regresi['toleransi_atas'][-1]

        bawah_atas = hasil_regresi['toleransi_bawah'][-2]
        bawah_bawah = hasil_regresi['toleransi_bawah'][-1]

        alert_message = None

        slope = hasil_regresi['slope']

        st.session_state.slope_history.append(slope)
        if len(st.session_state.slope_history) > 10:
            st.session_state.slope_history.pop(0)


        alert_message = None
        alarm = None

        if len(st.session_state.slope_history) >= 6:
            slope_sekarang = st.session_state.slope_history[-1]
            slope_5_menit_lalu = st.session_state.slope_history[-6]

            # Slope naik dan masuk zona biru
            if slope_sekarang > slope_5_menit_lalu and bawah_bawah[-1] <= low_terakhir <= bawah_atas[-1]:
                alarm = "alert1.mp3"                
                alert_message = (
                    f"🚨 Harga (Low) <b>{pair_code}</b> MASUK <b>ZONA BIRU</b> dengan slope NAIK!\n\n"
                    f"Harga Low: {low_terakhir}\nRentang: {bawah_bawah[-1]} - {bawah_atas[-1]}\n"
                    f"Slope sekarang: {slope_sekarang:.10f}\nSlope 5 bar lalu: {slope_5_menit_lalu:.10f}"
                )

            # Slope turun dan masuk zona merah
            elif slope_sekarang < slope_5_menit_lalu and atas_bawah[-1] <= high_terakhir <= atas_atas[-1]:
                alarm = "alert2.mp3"                 
                alert_message = (
                    f"🚨 Harga (High) <b>{pair_code}</b> MASUK <b>ZONA MERAH</b> dengan slope TURUN!\n\n"
                    f"Harga High: {high_terakhir}\nRentang: {atas_bawah[-1]} - {atas_atas[-1]}\n"
                    f"Slope sekarang: {slope_sekarang:.10f}\nSlope 5 bar lalu: {slope_5_menit_lalu:.10f}"
                )

        if alert_message:
            print(alert_message)
            st.session_state.show_alert = True
            st.session_state.alert_start_time = time.time()
            play_alert_sound(alarm)

        if st.session_state.show_alert:
            elapsed = time.time() - st.session_state.alert_start_time
            if elapsed <= 30:
                with st.expander("🚨 ALERT (Klik untuk buka/tutup)"):
                    st.markdown(alert_message, unsafe_allow_html=True)
                    st.markdown(f"⏱️ Tersisa {int(30 - elapsed)} detik sebelum alert ditutup otomatis...")
            else:
                st.session_state.show_alert = False
                st.session_state.alert_start_time = None

        if alert_message and bot_token and chat_id:
            kirim_telegram(alert_message, bot_token, chat_id)

        # Ambil nilai prediksi regresi saat ini dan sebelumnya
        prediksi_terakhir = hasil_regresi['prediksi'][-1]
        prediksi_sebelumnya = hasil_regresi['prediksi'][-2]

        with placeholder.container():

            # Informasi cara penggunaan strategi dalam kotak merah putus-putus
            st.markdown(
                """
                <div style="border: 2px dashed red; padding: 15px; margin-bottom: 20px; border-radius: 8px;">
                <h4>🛠️ Cara Penggunaan Strategi:</h4>
                <ul>
                  <li><b>BUY</b> → jika garis <i>close</i> atau <i>low</i> berada di zona <span style="color:blue;">buy (berwarna biru)</span></li>
                  <li><b>SELL</b> → jika garis <i>close</i> atau <i>high</i> memasuki area <span style="color:red;">sell (berwarna merah)</span></li>
                </ul>
                <p><b>⚠️ Saran:</b> Alarm akan otomatis berbunyi pada saat memasuki area BUY / SELL tersebut. Selalu konfirmasi sinyal BUY atau SELL dengan indikator pendukung lain (misal MACD, RSI, volume) sebelum mengambil keputusan.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            slope = hasil_regresi['slope']

            # --- Analisis Tren Regresi dan Rekomendasi ---
            if prediksi_terakhir > prediksi_sebelumnya:
                tren_market = "📈 Naik (Bullish)"
                saran = "✅ Saran: BUY atau HOLD"
                saran_trend = "🔔 Ikuti tren: Utamakan BUY saat harga masuk zona BUY."                
            elif prediksi_terakhir < prediksi_sebelumnya:  
                tren_market = "📉 Turun (Bearish)"     
                saran = "🔻 Saran: SELL atau tunggu pembalikan"
                saran_trend = "🔔 Ikuti tren: Utamakan SELL saat harga masuk zona SELL."                
            else:
                tren_market = "⏸️ Sideways (Datar)"
                saran = "⚠️ Saran: HOLD / Wait and see"
                saran_trend = "🔔 Tren datar, berhati-hati dan tunggu sinyal jelas."                

            # Ambil jumlah baris data yang dipakai
            jumlah_baris = len(df)

            # Konversi menit ke jam (misal 1 baris = 1 menit)
            jam = jumlah_baris / 60

            tren_info = f"""
            ### 🧠 Analisa Tren Regresi
            - **Slope garis regresi**: `{slope:.10f}`
            - **Status tren**: {tren_market}
            - **Rekomendasi**: {saran}
            - **Saran mengikuti tren**: {saran_trend}            
            - **Data yang digunakan**: {jumlah_baris} baris (~{jam:.2f} jam)
            """

            st.markdown(tren_info)

            fig1 = plot_regresi(df, hasil_regresi, theme)
            st.plotly_chart(fig1, use_container_width=True, key=f"fig1{aa}")

            fig2 = plot_macd_rsi(df, theme)
            st.plotly_chart(fig2, use_container_width=True, key=f"fig2{aa}")

        time.sleep(refresh_interval)
        aa += 1
