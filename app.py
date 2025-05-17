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


# --- Session State Initialization ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'show_alert' not in st.session_state:
    st.session_state.show_alert = False
if 'alert_start_time' not in st.session_state:
    st.session_state.alert_start_time = None


# --- Login State ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None

# --- Simple Auth (hardcoded) ---
VALID_USERS = {
    "admin": "binomo",  # username: password
    "user": "1235678"
}

# --- Login Form ---
if not st.session_state.logged_in:
    st.title("🔐 Login Dashboard")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            if username in VALID_USERS and password == VALID_USERS[username]:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success(f"Selamat datang, {username}!")
                st.rerun()  # Rerun untuk memperbarui status login                
            else:
                st.error("Username atau password salah.")
    st.stop()  # hentikan eksekusi halaman jika belum login


# Setelah login
st.title("📊 Crypto IDX -> CRY/IDX")
st.write("Selamat datang di analisa regresi linier Crypto IDX.")

# --- Sidebar Settings ---
st.sidebar.markdown("---")
if st.sidebar.button("🔓 Logout"):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.rerun()

st.sidebar.title("Settings")
pair_code = st.sidebar.text_input("Asset Pair", value="CRYIDX.B")
timeframe = st.sidebar.selectbox("Timeframe (menit)", ["30s", "1", "5", "15"], index=0)
refresh_interval = st.sidebar.slider("Refresh Interval (detik)", 5, 60, 10)
theme = st.sidebar.radio("Theme", ("Dark", "Light"))
run = st.sidebar.toggle("Start / Stop", value=False)

bot_token = st.sidebar.text_input("Telegram Bot Token", type="password")
chat_id = st.sidebar.text_input("Telegram Chat ID")


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

    # Harga close
    fig.add_trace(go.Scatter(x=df['datetime'], y=df['close'], mode='lines', name='Close', line=dict(color='lightblue')))
    # Harga high
    fig.add_trace(go.Scatter(x=df['datetime'], y=df['high'], mode='lines', name='High', line=dict(color='orange')))
    # Harga low
    fig.add_trace(go.Scatter(x=df['datetime'], y=df['low'], mode='lines', name='Low', line=dict(color='lightgreen')))

    # SMA & EMA
    fig.add_trace(go.Scatter(x=df['datetime'], y=df['SMA20'], mode='lines', name='SMA20', line=dict(color='orange', dash='dash')))
    fig.add_trace(go.Scatter(x=df['datetime'], y=df['EMA20'], mode='lines', name='EMA20', line=dict(color='magenta', dash='dash')))

    # Garis regresi utama
    fig.add_trace(go.Scatter(x=df['datetime'], y=hasil_regresi['prediksi'], mode='lines', name='Linear Regression', line=dict(color='red', dash='dot')))

    # Garis toleransi
    colors = ['green', 'orange', 'purple', 'brown', 'maroon', 'blue', 'red']
    for idx, (atas, bawah) in enumerate(zip(hasil_regresi['toleransi_atas'], hasil_regresi['toleransi_bawah'])):
        fig.add_trace(go.Scatter(x=df['datetime'], y=atas, mode='lines', name=f'Toleransi {idx+1} Atas', line=dict(color=colors[idx % len(colors)], dash='dot')))
        fig.add_trace(go.Scatter(x=df['datetime'], y=bawah, mode='lines', name=f'Toleransi {idx+1} Bawah', line=dict(color=colors[idx % len(colors)], dash='dot')))

    # --- Tambahkan latar belakang merah di antara 2 garis atas terakhir
    if len(hasil_regresi['toleransi_atas']) >= 2:
        atas_bawah = hasil_regresi['toleransi_atas'][-2]
        atas_atas = hasil_regresi['toleransi_atas'][-1]
        fig.add_trace(go.Scatter(
            x=df['datetime'], y=atas_atas,
            fill=None, mode='lines', line=dict(width=0), showlegend=False
        ))
        fig.add_trace(go.Scatter(
            x=df['datetime'], y=atas_bawah,
            fill='tonexty', mode='lines',
            line=dict(width=0),
            fillcolor='rgba(255,0,0,0.1)',  # merah transparan
            name='Zona Merah'
        ))

    # --- Tambahkan latar belakang biru di antara 2 garis bawah terakhir
    if len(hasil_regresi['toleransi_bawah']) >= 2:
        bawah_atas = hasil_regresi['toleransi_bawah'][-2]
        bawah_bawah = hasil_regresi['toleransi_bawah'][-1]
        fig.add_trace(go.Scatter(
            x=df['datetime'], y=bawah_bawah,
            fill=None, mode='lines', line=dict(width=0), showlegend=False
        ))
        fig.add_trace(go.Scatter(
            x=df['datetime'], y=bawah_atas,
            fill='tonexty', mode='lines',
            line=dict(width=0),
            fillcolor='rgba(0,0,255,0.1)',  # biru transparan
            name='Zona Biru'
        ))

    fig.update_layout(
        template="plotly_dark" if theme == "Dark" else "plotly_white",
        title="Price + Regression Bands",
        xaxis_title="Datetime",
        yaxis_title="Price",
        height=600,
        legend_title="Legend",
        showlegend=False
    )
    return fig

def plot_macd_rsi(df, theme):
    fig = go.Figure()

    # MACD & Signal
    fig.add_trace(go.Scatter(x=df['datetime'], y=df['MACD'], mode='lines', name='MACD', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=df['datetime'], y=df['Signal_Line'], mode='lines', name='Signal Line', line=dict(color='red', dash='dash')))

    # RSI (Secondary Y)
    fig.update_layout(
        template="plotly_dark" if theme == "Dark" else "plotly_white",
        title="MACD & RSI",
        xaxis_title="Datetime",
        yaxis_title="MACD",
        height=400,
        legend_title="Legend",
    )

    fig.add_trace(go.Scatter(
        x=df['datetime'], y=df['RSI'], mode='lines', name='RSI',
        line=dict(color='green'),
        yaxis='y2'
    ))

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
    while True:
        raw_data = fetch_data(pair_code, timeframe)        
        if len(raw_data) < 100:
            raw_data = fetch_data(pair_code, timeframe, 1)

        # print(len(raw_data))

        if raw_data is None:
            st.error("Gagal mendapatkan data. Program berhenti.")
            time.sleep(5)
            continue

        all_columns = ["timestamp", "open", "high", "low", "close", "col6", "col7", "col8", "col9", "col10", "col11"]
        df = pd.DataFrame(raw_data, columns=all_columns)
        
        # print(len(df))

        if df.empty:
            st.error("Gagal ambil data, retrying...")
            time.sleep(5)
            continue

        df = df[["timestamp", "open", "high", "low", "close"]]
        df = df.tail(1140)
        df = add_technical_indicators(df)
        hasil_regresi = linear_regression(df)

        # --- CEK ALERT ---
        # Hitung toleransi tertinggi dan terendah
        TOLERANSI = 0.000001  # kamu bisa jadikan slider di sidebar juga kalau mau
        
        toleransi_levels = [TOLERANSI * i for i in range(1, 8)]
        
        toleransi_atas_tertinggi = hasil_regresi['prediksi'] + toleransi_levels[-1]
        toleransi_bawah_terendah = hasil_regresi['prediksi'] - toleransi_levels[-1]


        low_terakhir = df['low'].iloc[-1]
        high_terakhir = df['high'].iloc[-1]

        # Ambil zona merah (atas)
        atas_bawah = hasil_regresi['toleransi_atas'][-2]
        atas_atas = hasil_regresi['toleransi_atas'][-1]

        # Ambil zona biru (bawah)
        bawah_atas = hasil_regresi['toleransi_bawah'][-2]
        bawah_bawah = hasil_regresi['toleransi_bawah'][-1]

        alert_message = None

        # Cek apakah harga HIGH menyentuh Zona Merah
        if atas_bawah[-1] <= high_terakhir <= atas_atas[-1]:
            alert_message = f"🚨 Harga (High) <b>{pair_code}</b> MASUK <b>ZONA MERAH</b>!\n\nHarga High: {high_terakhir}\nRentang: {atas_bawah[-1]} - {atas_atas[-1]}"

        # Cek apakah harga LOW menyentuh Zona Biru
        elif bawah_bawah[-1] <= low_terakhir <= bawah_atas[-1]:
            alert_message = f"🚨 Harga (Low) <b>{pair_code}</b> MASUK <b>ZONA BIRU</b>!\n\nHarga Low: {low_terakhir}\nRentang: {bawah_bawah[-1]} - {bawah_atas[-1]}"


        if alert_message:
            print(alert_message)

        # Set trigger jika alert muncul
        if alert_message:
            st.session_state.show_alert = True
            st.session_state.alert_start_time = time.time()
            play_alert_sound("alert.mp3")  # atau nama file lain

        # Tampilkan modal jika kondisi masih berlaku (max 30 detik)
        if st.session_state.show_alert:
            elapsed = time.time() - st.session_state.alert_start_time
            if elapsed <= 30:
                with st.expander("🚨 ALERT (Klik untuk buka/tutup)"):
                    st.markdown(alert_message, unsafe_allow_html=True)
                    st.markdown(f"⏱️ Tersisa {int(30 - elapsed)} detik sebelum alert ditutup otomatis...")
                
                # with st.modal("🚨 ALERT (auto-close in 30s)"):
                #     st.markdown(alert_message, unsafe_allow_html=True)
                #     st.markdown(f"⏱️ Menutup otomatis dalam {int(30 - elapsed)} detik...")
            else:
                st.session_state.show_alert = False
                st.session_state.alert_start_time = None

        if alert_message and bot_token and chat_id:
            kirim_telegram(alert_message, bot_token, chat_id)

        with placeholder.container():
            # Tidak perlu columns kalau satu layout
            fig1 = plot_regresi(df, hasil_regresi, theme)
            st.plotly_chart(fig1, use_container_width=True, key=f"fig1{aa}")

            fig2 = plot_macd_rsi(df, theme)
            st.plotly_chart(fig2, use_container_width=True, key=f"fig2{aa}")

        time.sleep(refresh_interval)

        aa = aa + 1
