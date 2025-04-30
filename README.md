Kode ini adalah sebuah **dashboard analisis teknikal harga aset** berbasis web menggunakan **Streamlit**. Meskipun kode itu kompleks, konsep di baliknya cukup terstruktur dan mengikuti alur kerja yang logis dari pengumpulan data sampai visualisasi dan alert. Berikut penjelasan konsep dan strategi yang digunakan tanpa membahas kode spesifik:

---

## 🧠 **Fitur yang ada di Aplikasi**

### 1. **Otentikasi Pengguna**
Aplikasi dimulai dengan sistem login sederhana. Ini membatasi akses agar hanya pengguna tertentu yang dapat melihat dan menggunakan dashboard, melindungi data dan logika dari penggunaan sembarangan.

---

### 2. **Pengumpulan dan Pemrosesan Data Harga**
Aplikasi ini mengakses **data harga historis aset** secara berkala dari sumber eksternal (API pihak ketiga). Data ini kemudian diolah:
- Menjadi *DataFrame* yang dapat dianalisis.
- Dihitung indikator teknikalnya seperti:
  - **SMA** (Simple Moving Average)
  - **EMA** (Exponential Moving Average)
  - **MACD** (Moving Average Convergence Divergence)
  - **RSI** (Relative Strength Index)

---

### 3. **Model Regresi Linier**
Data harga kemudian dianalisis menggunakan **regresi linier** untuk:
- Mengestimasi tren harga jangka pendek atau menengah.
- Menentukan **batas toleransi atas/bawah** dari prediksi model untuk mendeteksi anomali harga (misal: breakout).

---

### 4. **Visualisasi Interaktif**
Dengan bantuan **Plotly**, hasil analisis ditampilkan dalam dua grafik utama:
- Grafik harga dengan garis tren dan zona toleransi.
- Grafik MACD & RSI untuk mendeteksi momentum dan potensi reversal.

Visualisasi ini:
- Bersifat interaktif.
- Dapat dikustomisasi melalui **sidebar** (timeframe, tema, refresh rate, dll).

---

### 5. **Sistem Monitoring Otomatis**
Aplikasi berjalan dalam loop jika diaktifkan:
- Setiap beberapa detik, data baru diambil dan diproses ulang.
- Jika harga menyentuh batas atas/bawah dari zona toleransi, sistem **mengirimkan peringatan ke Telegram** (jika token dan chat ID tersedia).

---

### 6. **Penggunaan Telegram sebagai Alert Notifikasi**
Ini merupakan bentuk integrasi **external notification system**. Sangat penting untuk sistem trading semi-otomatis, karena:
- Memungkinkan pengguna mendapatkan peringatan real-time tanpa harus membuka dashboard terus-menerus.
- Berguna untuk pengambilan keputusan cepat.

---

## 🔧 **Strategi yang Digunakan**

| Strategi | Penjelasan |
|----------|------------|
| **Polling Periodik** | Mengambil data setiap beberapa detik sesuai pengaturan pengguna. Cocok untuk monitoring harga real-time. |
| **Multi-layered Tolerance Band** | Zona toleransi bertingkat digunakan untuk membedakan level sinyal (waspada, kuat, ekstrim). Ini memperkaya sinyal trading. |
| **Modularisasi Kode** | Fungsi-fungsi penting (seperti fetching data, indikator, regresi, alert) dipecah dalam modul terpisah (`utils.py`). Ini memperkuat maintainability. |
| **Interaktivitas dan Visual Feedback** | UI/UX pengguna diperhatikan dengan tombol start/stop, tema visual, dan notifikasi. |

---

## 🎯 **Tujuan Umum Aplikasi**

Aplikasi ini dibuat **semata-mata untuk tujuan pembelajaran dan edukasi** dalam memahami konsep **analisis teknikal terhadap data harga aset**. Tujuan utamanya meliputi:

- Mempelajari regresi linier untuk mengidentifikasi tren harga.
- Menggunakan indikator teknikal populer seperti SMA, EMA, MACD, dan RSI.
- Menganalisis zona toleransi untuk mendeteksi potensi sinyal breakout harga.
- Melatih pembuatan sistem dashboard analitik berbasis Python dan Streamlit.

⚠️ **Catatan Penting:**
- Aplikasi ini **tidak dimaksudkan untuk mempromosikan judi online, trading ilegal, atau aktivitas spekulatif berisiko tinggi**.
- Aplikasi **bukan alat prediksi harga resmi** dan **tidak memberikan jaminan keuntungan**.
- Segala penggunaan di luar konteks edukasi merupakan tanggung jawab pengguna masing-masing.
