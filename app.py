import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pyproj import Transformer
import glob
import os

# --- Inisialisasi Session State ---
if 'cleaned_bati_data' not in st.session_state:
    st.session_state['cleaned_bati_data'] = None
if 'bati_clean' not in st.session_state:
    st.session_state['bati_clean'] = None
if 'data_pasut' not in st.session_state:
    st.session_state['data_pasut'] = None
if 'datum_pasut' not in st.session_state:
    st.session_state['datum_pasut'] = None
if 'final_data' not in st.session_state:
    st.session_state['final_data'] = None
if 'outlier_action' not in st.session_state:
    st.session_state['outlier_action'] = None
if 'date_format' not in st.session_state:
    st.session_state['date_format'] = None
if 'date_format_pasut' not in st.session_state:
    st.session_state['date_format_pasut'] = None
if 'time_format_pasut' not in st.session_state:
    st.session_state['time_format_pasut'] = None
if 'coord_system' not in st.session_state:
    st.session_state['coord_system'] = 'Geografis (Longitude/Latitude)'
if 'utm_zone_manual' not in st.session_state:
    st.session_state['utm_zone_manual'] = None

# --- Judul Aplikasi ---
st.title("Aplikasi Pengolahan Data Batimetri SBES")

# --- Penjelasan Singkat ---
st.markdown("""
Aplikasi ini digunakan untuk mengolah data batimetri dari Single Beam Echosounder.
Langkah-langkahnya meliputi:
1. Upload file data batimetri dan pilih sistem koordinat (Geografis atau UTM).
2. Pilih format tanggal data batimetri.
3. Upload file data pasang surut (`pasut.txt`) - Kolom Tanggal dan Waktu Terpisah.
4. Pilih format tanggal dan waktu data pasut.
5. Input manual datum pasang surut (HWS, MSL, LWS).
6. Proses pembersihan, deteksi outlier, dan koreksi pasang surut.
7. Transformasi koordinat ke UTM (jika input masih Geografis).
8. Download hasil akhir.

Disusun Oleh: Dharmawan Abdullah, S.T. (2025)
""")

# --- Tahap 1: Inisiasi Awal dan Input Data ---
st.header("1. Inisiasi Awal dan Input Data")

# 1.1 Pilih Sistem Koordinat
st.subheader("Pilih Sistem Koordinat Data Batimetri")
coord_system = st.radio(
    "Sistem koordinat data batimetri yang akan diupload:",
    options=["Geografis (Longitude/Latitude)", "UTM (X, Y)"],
    key="coord_system_radio",
    horizontal=True
)
st.session_state['coord_system'] = coord_system

utm_zone_input = None
if coord_system == "UTM (X, Y)":
    utm_zone_input = st.text_input(
        "Masukkan Zona UTM data Anda (misal: 49S, 50N):", 
        key="utm_zone_input",
        placeholder="Contoh: 49S"
    )
    st.session_state['utm_zone_manual'] = utm_zone_input.strip().upper() if utm_zone_input else None
    st.info("Pastikan kolom ke-3 adalah X UTM dan kolom ke-4 adalah Y UTM.")
else:
    st.session_state['utm_zone_manual'] = None
    st.info("Pastikan kolom ke-3 adalah Longitude dan kolom ke-4 adalah Latitude.")

st.divider()

# 1.2 Upload dan Format Data Batimetri
uploaded_files_bati = st.file_uploader(
    "Upload file-file batimetri (.txt)",
    type=["txt"],
    accept_multiple_files=True,
    key="bati_files"
)

format_options_bati = {
    "DD-Mon-YY (misal: 01-Jul-23)": "%d-%b-%y",
    "DD-MM-YY (misal: 01-07-23)": "%d-%m-%y",
    "DD/MM/YY (misal: 01/07/23)": "%d/%m/%y",
    "DD-MM-YYYY (misal: 01-07-2023)": "%d-%m-%Y",
    "DD/MM/YYYY (misal: 01/07/2023)": "%d/%m/%Y",
    "MM-DD-YY (misal: 07-01-23)": "%m-%d-%y",
    "MM/DD/YY (misal: 07/01/23)": "%m/%d/%y",
    "MM-DD-YYYY (misal: 07-01-2023)": "%m-%d-%Y",
    "MM/DD/YYYY (misal: 07/01-2023)": "%m/%d/%Y",
}

selected_format_label_bati = st.selectbox(
    "Pilih format tanggal data batimetri:",
    options=list(format_options_bati.keys()),
    key="date_format_selectbox_bati",
    disabled=not bool(uploaded_files_bati)
)

if selected_format_label_bati:
    selected_format_bati = format_options_bati[selected_format_label_bati]
    st.session_state['date_format'] = selected_format_bati
    st.write(f"Format tanggal batimetri yang dipilih: `{selected_format_bati}`")
else:
    st.session_state['date_format'] = None

st.divider()

# 1.3 Upload dan Format Data Pasut
uploaded_file_pasut = st.file_uploader(
    "Upload file data pasang surut - Kolom Tanggal dan Waktu Terpisah (tanpa header)",
    type=["txt"],
    key="pasut_file"
)

format_options_pasut_date = {
    "DD/MM/YYYY (misal: 21/06/2023)": "%d/%m/%Y",
    "YYYY-MM-DD (misal: 2023-06-21)": "%Y-%m-%d",
    "DD-MM-YYYY (misal: 21-06-2023)": "%d-%m-%Y",
    "DD-Mon-YYYY (misal: 21-Jun-2023)": "%d-%b-%Y",
}

format_options_pasut_time = {
    "HH:MM:SS (misal: 13:30:00)": "%H:%M:%S",
    "HH:MM (misal: 13:30)": "%H:%M",
}

if uploaded_file_pasut:
    selected_format_label_pasut_date = st.selectbox(
        "Pilih format kolom Tanggal data pasut:",
        options=list(format_options_pasut_date.keys()),
        key="date_format_selectbox_pasut_date"
    )
    selected_format_label_pasut_time = st.selectbox(
        "Pilih format kolom Waktu data pasut:",
        options=list(format_options_pasut_time.keys()),
        key="time_format_selectbox_pasut_time"
    )

    if selected_format_label_pasut_date and selected_format_label_pasut_time:
        st.session_state['date_format_pasut'] = format_options_pasut_date[selected_format_label_pasut_date]
        st.session_state['time_format_pasut'] = format_options_pasut_time[selected_format_label_pasut_time]
        st.write(f"Format tanggal pasut: `{st.session_state['date_format_pasut']}` | Format waktu: `{st.session_state['time_format_pasut']}`")
    else:
        st.session_state['date_format_pasut'] = None
        st.session_state['time_format_pasut'] = None
else:
    st.session_state['date_format_pasut'] = None
    st.session_state['time_format_pasut'] = None

st.divider()

# 1.4 Input Manual Datum
st.subheader("Input Manual Datum Pasang Surut")
hws_input = st.number_input("Tinggi Muka Air (HWS) dalam meter", key="hws_input", format="%.3f")
msl_input = st.number_input("Tinggi Muka Air Rata-rata (MSL) dalam meter", key="msl_input", format="%.3f")
lws_input = st.number_input("Rendah Muka Air (LWS) dalam meter", key="lws_input", format="%.3f")

# Validasi tombol proses
is_utm_valid = (coord_system == "Geografis (Longitude/Latitude)") or (st.session_state.get('utm_zone_manual') not in [None, ""])

start_processing = st.button("Proses Data", disabled=not all([
    uploaded_files_bati,
    uploaded_file_pasut,
    hws_input is not None,
    msl_input is not None,
    lws_input is not None,
    st.session_state.get('date_format'),
    st.session_state.get('date_format_pasut'),
    st.session_state.get('time_format_pasut'),
    is_utm_valid
]))

if start_processing:
    try:
        # --- Proses Data Batimetri ---
        bati_list = []
        for uploaded_file in uploaded_files_bati:
            df_temp = pd.read_csv(uploaded_file, dtype=str, encoding='latin1', sep="\t", header=None)
            bati_list.append(df_temp)
        bati_compile = pd.concat(bati_list, ignore_index=True)

        bati = bati_compile.copy()
        format_tanggal_bati = st.session_state['date_format']
        bati["timestamp"] = pd.to_datetime(bati[0] + " " + bati[1], format=f"{format_tanggal_bati} %H:%M:%S", errors='coerce')
        
        # LOGIKA CABANG BERDASARKAN SISTEM KOORDINAT
        if st.session_state['coord_system'] == "Geografis (Longitude/Latitude)":
            bati = bati[["timestamp", 2, 3, 4]]
            bati.columns = ["timestamp", "longitude", "latitude", "kedalaman"]

            def clean_longitude(val):
                if pd.isna(val): return None
                s = str(val).strip().replace("°E", "")
                try: return float(s)
                except: return None

            def clean_latitude(val):
                if pd.isna(val): return None
                s = str(val).strip().upper().replace("°", "")
                if "S" in s: s = s.replace("S", ""); sign = -1
                elif "N" in s: s = s.replace("N", ""); sign = 1
                else: sign = 1
                try: return float(s) * sign
                except ValueError: return None

            bati["longitude"] = bati["longitude"].apply(clean_longitude)
            bati["latitude"] = bati["latitude"].apply(clean_latitude)
            bati["kedalaman"] = pd.to_numeric(bati["kedalaman"], errors="coerce")
            bati_drop = bati.dropna(subset=["kedalaman", "longitude", "latitude", "timestamp"]).reset_index(drop=True)
            
        else: # UTM
            bati = bati[["timestamp", 2, 3, 4]]
            bati.columns = ["timestamp", "X_UTM", "Y_UTM", "kedalaman"]
            bati["X_UTM"] = pd.to_numeric(bati["X_UTM"], errors="coerce")
            bati["Y_UTM"] = pd.to_numeric(bati["Y_UTM"], errors="coerce")
            bati["kedalaman"] = pd.to_numeric(bati["kedalaman"], errors="coerce")
            bati_drop = bati.dropna(subset=["kedalaman", "X_UTM", "Y_UTM", "timestamp"]).reset_index(drop=True)
            
            # Lakukan inverse transform ke Lat/Lon HANYA untuk keperluan visualisasi Cartopy
            zone_str = st.session_state['utm_zone_manual']
            zone_num = int(zone_str[:-1])
            hemisphere = zone_str[-1]
            epsg_code = 32600 + zone_num if hemisphere == 'N' else 32700 + zone_num
            
            transformer_inv = Transformer.from_crs(f"EPSG:{epsg_code}", "EPSG:4326", always_xy=True)
            lon_vals, lat_vals = transformer_inv.transform(bati_drop["X_UTM"].values, bati_drop["Y_UTM"].values)
            bati_drop["longitude"] = lon_vals
            bati_drop["latitude"] = lat_vals

        bati_drop = bati_drop.sort_values("timestamp").reset_index(drop=True)
        st.session_state['cleaned_bati_data'] = bati_drop
        st.success(f"Data batimetri berhasil diproses. Jumlah baris: {len(bati_drop)}")

        # --- Proses Data Pasut ---
        data_pasut_raw = pd.read_csv(uploaded_file_pasut, dtype=str, sep="\t", encoding='latin1', header=None)
        format_date_pasut = st.session_state['date_format_pasut']
        format_time_pasut = st.session_state['time_format_pasut']

        combined_datetime_str = data_pasut_raw[0].astype(str) + " " + data_pasut_raw[1].astype(str)
        data_pasut_raw["Timestamp"] = pd.to_datetime(combined_datetime_str, format=f"{format_date_pasut} {format_time_pasut}", errors='coerce')
        data_pasut_raw["Depth"] = pd.to_numeric(data_pasut_raw[2], errors="coerce")
        data_pasut = data_pasut_raw.dropna(subset=["Timestamp", "Depth"])[["Timestamp", "Depth"]].reset_index(drop=True)

        if len(data_pasut) == 0:
            st.error("Tidak ada data pasut yang valid. Periksa format tanggal/waktu.")
            st.stop()

        st.session_state['data_pasut'] = data_pasut
        st.success(f"Data pasut berhasil diproses. Jumlah baris: {len(data_pasut)}")

        # --- Simpan Datum ---
        st.session_state['datum_pasut'] = (hws_input, msl_input, lws_input)
        st.success(f"Datum disimpan: HWS={hws_input:.3f}, MSL={msl_input:.3f}, LWS={lws_input:.3f}")

    except Exception as e:
        st.error(f"Error saat membaca atau memproses file: {e}")
        st.stop()

# --- Tampilkan Hasil Upload ---
if st.session_state.get('cleaned_bati_data') is not None:
    st.header("Hasil Upload dan Input Datum")
    st.subheader("Data Batimetri")
    st.write(f"Jumlah baris setelah cleaning: {len(st.session_state['cleaned_bati_data'])}")
    st.dataframe(st.session_state['cleaned_bati_data'].head())

if st.session_state.get('data_pasut') is not None:
    st.subheader("Data Pasang Surut")
    st.write(f"Jumlah baris: {len(st.session_state['data_pasut'])}")
    st.dataframe(st.session_state['data_pasut'].head())
    
    # Plot Pasut
    try:
        fig, ax = plt.subplots(figsize=(12, 5))
        ax.plot(st.session_state['data_pasut']["Timestamp"], st.session_state['data_pasut']["Depth"], linewidth=1.5, color='blue')
        start_date = st.session_state['data_pasut']["Timestamp"].min().strftime("%d %b %Y")
        end_date = st.session_state['data_pasut']["Timestamp"].max().strftime("%d %b %Y")
        ax.set_title(f"Grafik Pasang Surut ({start_date} – {end_date})", fontsize=14, fontweight='bold')
        ax.set_xlabel("Waktu Pengamatan", fontsize=12)
        ax.set_ylabel("Tinggi Muka Air (meter)", fontsize=12)
        ax.grid(True, linestyle='--', alpha=0.5)
        plt.xticks(rotation=45, ha='right')
        st.pyplot(fig)
        plt.clf()
    except Exception as e:
        st.error(f"Error plot pasut: {e}")

if st.session_state.get('datum_pasut') is not None:
    HWS, MSL, LWS = st.session_state['datum_pasut']
    st.write(f"**HWS:** {HWS:.3f} m | **MSL:** {MSL:.3f} m | **LWS:** {LWS:.3f} m")


# --- Tahap 2: Deteksi dan Penanganan Outlier ---
st.header("2. Deteksi dan Penanganan Outlier")

# Inisialisasi session state untuk pengali IQR
if 'iqr_multiplier' not in st.session_state:
    st.session_state['iqr_multiplier'] = 1.5
if 'outlier_checked' not in st.session_state:
    st.session_state['outlier_checked'] = False

if st.session_state['cleaned_bati_data'] is not None:
    bati_drop = st.session_state['cleaned_bati_data']

    # Plot sebelum deteksi outlier
    st.subheader("Data Sebelum Penanganan Outlier:")
    fig, ax = plt.subplots()
    ax.plot(bati_drop["timestamp"], bati_drop["kedalaman"], color='black', linewidth=0.8)
    ax.set_xlabel('Date')
    ax.set_ylabel('Depth [m]')
    ax.grid(True)
    st.pyplot(fig)
    plt.clf()

    # Hitung IQR dan batas
    Q1 = bati_drop['kedalaman'].quantile(0.25)
    Q3 = bati_drop['kedalaman'].quantile(0.75)
    IQR = Q3 - Q1
    
    st.write(f"**Statistik Data:**")
    st.write(f"- Q1 (Kuartil 1): {Q1:.3f} m")
    st.write(f"- Q3 (Kuartil 3): {Q3:.3f} m")
    st.write(f"- IQR: {IQR:.3f} m")

    # Input nilai pengali IQR
    st.subheader("Pengaturan Nilai Pengali IQR")
    st.info("Nilai pengali default adalah 1.5. Anda dapat memodifikasinya untuk menyesuaikan jumlah outlier yang terdeteksi.")
    
    iqr_multiplier_input = st.number_input(
        "Masukkan nilai pengali IQR:",
        min_value=0.1,
        max_value=10.0,
        value=st.session_state['iqr_multiplier'],
        step=0.1,
        format="%.1f",
        key="iqr_multiplier_input",
        help="Nilai pengali untuk menghitung batas outlier. Semakin kecil nilai, semakin banyak outlier yang terdeteksi."
    )

    # Tombol untuk menerapkan pengali baru
    col_apply, col_reset = st.columns(2)
    with col_apply:
        apply_multiplier = st.button("✅ Terapkan Nilai Pengali", type="primary")
    with col_reset:
        reset_multiplier = st.button("🔄 Reset ke Default (1.5)")

    if reset_multiplier:
        st.session_state['iqr_multiplier'] = 1.5
        st.session_state['outlier_checked'] = False
        st.rerun()

    if apply_multiplier:
        st.session_state['iqr_multiplier'] = iqr_multiplier_input
        st.session_state['outlier_checked'] = True
        st.rerun()

    # Hitung outlier dengan pengali saat ini
    current_multiplier = st.session_state['iqr_multiplier']
    lower_bound = Q1 - current_multiplier * IQR
    upper_bound = Q3 + current_multiplier * IQR

    st.write(f"**Batas Outlier saat ini (pengali = {current_multiplier}):**")
    st.write(f"- Batas Bawah: {lower_bound:.3f} m")
    st.write(f"- Batas Atas: {upper_bound:.3f} m")

    # Temukan outlier
    outliers = bati_drop[(bati_drop['kedalaman'] < lower_bound) | (bati_drop['kedalaman'] > upper_bound)]
    num_outliers = len(outliers)
    total_data = len(bati_drop)
    percentage = (num_outliers / total_data) * 100 if total_data > 0 else 0

    st.write(f"**Jumlah outlier yang terdeteksi:** {num_outliers} dari {total_data} data ({percentage:.2f}%)")

    # Tampilkan data outlier jika ditemukan
    if num_outliers > 0:
        st.write("Contoh data outlier (10 teratas):")
        st.dataframe(outliers[['timestamp', 'longitude', 'latitude', 'kedalaman']].head(10))

    # Tahap pengecekan: apakah user ingin memodifikasi atau lanjut
    if not st.session_state.get('outlier_checked', False):
        st.subheader("Langkah Selanjutnya")
        st.info("Silakan periksa jumlah outlier di atas. Jika sudah sesuai, klik 'Lanjut ke Penanganan Outlier'. Jika belum sesuai, ubah nilai pengali IQR dan klik 'Terapkan Nilai Pengali'.")
        
        if st.button("➡️ Lanjut ke Penanganan Outlier", type="primary"):
            st.session_state['outlier_checked'] = True
            st.rerun()
    else:
        # Setelah user puas dengan jumlah outlier, tampilkan pilihan hapus/pertahankan
        st.subheader("Penanganan Outlier")
        st.success(f"Nilai pengali IQR ditetapkan: {current_multiplier}. Jumlah outlier terdeteksi: {num_outliers}.")

        if num_outliers > 0:
            st.write("Apakah Anda ingin menghapus data outlier?")
            col1, col2 = st.columns(2)

            with col1:
                if st.button("✅ Ya, hapus semua data outlier", key="remove_outliers_btn_final"):
                    bati_clean = bati_drop[(bati_drop['kedalaman'] >= lower_bound) & (bati_drop['kedalaman'] <= upper_bound)].copy()
                    st.session_state['bati_clean'] = bati_clean
                    st.session_state['outlier_action'] = 'remove'
                    st.success(f"Outlier telah dihapus. Jumlah baris sekarang: {len(bati_clean)}")

            with col2:
                if st.button("❌ Tidak, lanjutkan dengan data outlier", key="keep_outliers_btn_final"):
                    st.session_state['bati_clean'] = bati_drop.copy()
                    st.session_state['outlier_action'] = 'keep'
                    st.warning("Penghapusan outlier dibatalkan. Proses akan dilanjutkan dengan data termasuk outlier.")
        else:
            st.info("Tidak ditemukan outlier berdasarkan metode IQR dengan pengali saat ini.")
            st.session_state['bati_clean'] = bati_drop.copy()
            st.session_state['outlier_action'] = 'none'
            st.success("Tidak ada outlier ditemukan. Proses akan dilanjutkan.")

        # Tombol untuk kembali ke pengaturan pengali
        st.divider()
        if st.button("🔙 Kembali ke Pengaturan Pengali IQR"):
            st.session_state['outlier_checked'] = False
            st.rerun()

# --- Tampilkan hasil penanganan outlier ---
if st.session_state.get('bati_clean') is not None and st.session_state.get('outlier_action') is not None:
    st.header("Hasil Setelah Penanganan Outlier")
    bati_clean = st.session_state['bati_clean']
    action = st.session_state['outlier_action']

    st.subheader("Plot Kedalaman Setelah Penanganan Outlier:")
    fig, ax = plt.subplots()
    ax.plot(bati_clean["timestamp"], bati_clean["kedalaman"], color='black', linewidth=0.8)
    ax.set_xlabel('Date')
    ax.set_ylabel('Depth [m]')
    ax.grid(True)
    st.pyplot(fig)
    plt.clf()

    if action == 'remove':
        st.write(f"Outlier telah dihapus. Jumlah baris sekarang: {len(bati_clean)}")
    elif action == 'keep':
        st.write(f"Data outlier dipertahankan. Jumlah baris: {len(bati_clean)}")
    elif action == 'none':
        st.write(f"Tidak ada outlier ditemukan. Jumlah baris: {len(bati_clean)}")


# --- Tahap 3: Koreksi Pasut dan Transformasi UTM ---
st.header("3. Koreksi Pasang Surut dan Transformasi UTM")

if all(v is not None for v in [st.session_state['bati_clean'], st.session_state['data_pasut'], st.session_state['datum_pasut']]):
    bati_clean = st.session_state['bati_clean']
    data_pasut_koreksi = st.session_state['data_pasut']
    HWS, MSL, LWS = st.session_state['datum_pasut']

    st.subheader("Melakukan Koreksi Pasang Surut...")
    try:
        bati_koreksi = bati_clean.copy()
        bati_koreksi["pasut_interp"] = np.interp(
            bati_koreksi["timestamp"].astype(np.int64),
            data_pasut_koreksi["Timestamp"].astype(np.int64),
            data_pasut_koreksi["Depth"].values
        )
        bati_koreksi['D_LWS'] = -(bati_koreksi['kedalaman'] + (LWS - bati_koreksi["pasut_interp"]))
        bati_koreksi['D_MSL'] = -(bati_koreksi['kedalaman'] + (MSL - bati_koreksi["pasut_interp"]))
        bati_koreksi['D_HWS'] = -(bati_koreksi['kedalaman'] + (HWS - bati_koreksi["pasut_interp"]))
        st.success("Koreksi pasang surut berhasil.")
    except Exception as e:
        st.error(f"Error koreksi pasut: {e}"); st.stop()

    st.subheader("Melakukan Transformasi Koordinat ke UTM...")
    try:
        if st.session_state['coord_system'] == "Geografis (Longitude/Latitude)":
            # Jalankan transformasi Geografis ke UTM
            def lonlat_to_utm_per_point(df, lon_col="longitude", lat_col="latitude"):
                lon = df[lon_col].values; lat = df[lat_col].values
                utm_zones = np.floor((lon + 180) / 6).astype(int) + 1
                hemispheres = np.where(lat >= 0, "N", "S")
                epsg_codes = np.where(lat >= 0, 32600 + utm_zones, 32700 + utm_zones)
                x_utm, y_utm = np.zeros(len(df)), np.zeros(len(df))
                for epsg in np.unique(epsg_codes):
                    mask = epsg_codes == epsg
                    transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
                    x_utm[mask], y_utm[mask] = transformer.transform(lon[mask], lat[mask])
                df["Zona_UTM"] = [f"{z}{h}" for z, h in zip(utm_zones, hemispheres)]
                df["X_UTM"], df["Y_UTM"] = x_utm, y_utm
                st.write(f"Ditemukan {len(sorted(df['Zona_UTM'].unique()))} zona UTM.")
                return df
            bati_koreksi_utm = lonlat_to_utm_per_point(bati_koreksi)
        else:
            # Data sudah UTM, lewati transformasi
            bati_koreksi_utm = bati_koreksi.copy()
            bati_koreksi_utm["Zona_UTM"] = st.session_state['utm_zone_manual']
            st.success(f"Data sudah dalam format UTM. Zona UTM ditetapkan sebagai: {st.session_state['utm_zone_manual']}")

        st.session_state['final_data'] = bati_koreksi_utm
        st.success("Transformasi UTM berhasil/selesai!")
    except Exception as e:
        st.error(f"Error transformasi UTM: {e}"); st.stop()
else:
    st.warning("Data untuk koreksi belum tersedia.")


# --- Tampilkan Hasil Akhir ---
if st.session_state.get('final_data') is not None:
    st.header("Hasil Akhir: Data Terkoreksi dan Tertransformasi")
    final_df = st.session_state['final_data']
    st.write("Contoh data setelah koreksi dan transformasi:")
    st.dataframe(final_df.head())

    # Plot lintasan sederhana
    st.subheader("Sebaran Titik Pengukuran")
    fig, ax = plt.subplots(figsize=(8,6))
    ax.scatter(final_df['longitude'], final_df['latitude'], s=5)
    ax.set_xlabel('Longitude'); ax.set_ylabel('Latitude')
    ax.grid(True, linestyle='--', alpha=0.5); ax.axis('equal')
    st.pyplot(fig); plt.clf()

    # Plot Cartopy (DIPERBAIKI DENGAN FALLBACK)
    st.subheader("Sebaran Titik Pengukuran dengan Peta (Cartopy)")
    
    # Pastikan data memiliki longitude dan latitude
    if 'longitude' not in final_df.columns or 'latitude' not in final_df.columns:
        st.error("Data tidak memiliki kolom longitude dan latitude untuk plotting Cartopy.")
    else:
        try:
            import cartopy.crs as ccrs
            import cartopy.feature as cfeature
            from cartopy.mpl.ticker import LongitudeFormatter, LatitudeFormatter
            
            # Test apakah Cartopy bisa membuat plot sederhana
            fig_test = plt.figure()
            plt.close(fig_test)  # Tutup test figure
            
            # Buat figure dengan ukuran yang lebih kecil
            fig = plt.figure(figsize=(8, 6), dpi=100)
            ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
            
            # Tambahkan fitur peta dengan cara yang lebih sederhana
            ax.stock_img()  # Gunakan stock image dari Cartopy
            ax.coastlines(resolution='110m', linewidth=0.8)
            
            # Dapatkan data koordinat
            lons = final_df['longitude'].values
            lats = final_df['latitude'].values
            depths = -final_df['kedalaman'].values  # Negatif untuk visualisasi
            
            # Plot titik-titik
            sc = ax.scatter(
                lons, lats,
                c=depths,
                cmap='turbo_r', 
                s=10,
                transform=ccrs.PlateCarree(),
                edgecolors='none',
                alpha=0.7
            )
            
            # Colorbar yang lebih sederhana
            cbar = plt.colorbar(sc, ax=ax, shrink=0.6, pad=0.02)
            cbar.set_label('Kedalaman (m)', fontsize=10)
            
            # Set extent dengan buffer yang lebih besar
            min_lon, max_lon = lons.min(), lons.max()
            min_lat, max_lat = lats.min(), lats.max()
            
            # Tambahkan padding 20%
            lon_pad = (max_lon - min_lon) * 0.2
            lat_pad = (max_lat - min_lat) * 0.2
            
            ax.set_extent([
                min_lon - lon_pad, max_lon + lon_pad,
                min_lat - lat_pad, max_lat + lat_pad
            ], crs=ccrs.PlateCarree())
            
            # Grid sederhana
            gl = ax.gridlines(draw_labels=False, linestyle='--', alpha=0.3)
            
            ax.set_title('Sebaran Titik Pengukuran', fontsize=12, pad=10)
            
            # Tight layout untuk menghindari overlap
            plt.tight_layout()
            
            # Tampilkan di Streamlit
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)  # Tutup figure untuk menghemat memori
            
            st.success("✅ Plot Cartopy berhasil dibuat.")
            
        except ImportError as ie:
            st.warning("️ Library 'cartopy' tidak tersedia di server ini.")
            st.info("Plot Cartopy memerlukan instalasi cartopy. Jika Anda menggunakan Streamlit Cloud, tambahkan 'cartopy' di requirements.txt")
            
            # Fallback: Tampilkan plot biasa yang lebih detail
            st.info("Menggunakan plot alternatif...")
            fig_alt, ax_alt = plt.subplots(figsize=(8, 6))
            scatter = ax_alt.scatter(
                final_df['longitude'], 
                final_df['latitude'], 
                c=-final_df['kedalaman'],
                cmap='turbo_r', 
                s=10,
                alpha=0.6
            )
            plt.colorbar(scatter, label='Kedalaman (m)')
            ax_alt.set_xlabel('Longitude')
            ax_alt.set_ylabel('Latitude')
            ax_alt.set_title('Sebaran Titik Pengukuran Batimetri')
            ax_alt.grid(True, alpha=0.3)
            ax_alt.axis('equal')
            st.pyplot(fig_alt, use_container_width=True)
            plt.close(fig_alt)
            
        except Exception as e:
            st.error(f"❌ Error saat membuat plot Cartopy: {type(e).__name__}")
            st.error(f"Detail: {str(e)}")
            st.info("💡 Pastikan data koordinat valid (Longitude: -180 sampai 180, Latitude: -90 sampai 90)")
            
            # Tampilkan info debug
            st.write("**Debug Info:**")
            st.write(f"- Jumlah data: {len(final_df)}")
            st.write(f"- Longitude range: {final_df['longitude'].min():.4f} sampai {final_df['longitude'].max():.4f}")
            st.write(f"- Latitude range: {final_df['latitude'].min():.4f} sampai {final_df['latitude'].max():.4f}")
            st.write(f"- Depth range: {final_df['kedalaman'].min():.2f} sampai {final_df['kedalaman'].max():.2f}")


# --- Tahap 4: Download ---
st.header("4. Download Hasil")

if st.session_state.get('final_data') is not None:
    final_df = st.session_state['final_data']
    st.success("✅ Proses Pengolahan Data Selesai! Data siap untuk diunduh.")

    output_files = {}
    for zona in final_df["Zona_UTM"].unique():
        subset_zone = final_df[final_df["Zona_UTM"] == zona]
        for datum in ["D_LWS", "D_MSL", "D_HWS"]:
            file_name = f"Batimetri_{zona.replace(' ', '')}_{datum.split('_')[1]}.txt"
            subset_xyz = subset_zone[["X_UTM", "Y_UTM", datum]].copy()
            subset_xyz.columns = ["X", "Y", "Z"]
            output_files[file_name] = subset_xyz.to_csv(sep=' ', index=False, header=False, float_format='%.3f')

    st.subheader("Pilih file yang ingin Anda unduh:")
    for file_name, file_content in output_files.items():
        st.download_button(label=f" Download {file_name}", data=file_content, file_name=file_name, mime="text/plain")

    if st.button("🔄 Proses Ulang"):
        st.session_state.clear(); st.rerun()
else:
    st.warning("Data akhir belum tersedia.")
    if st.button("🔄 Proses Ulang"):
        st.session_state.clear(); st.rerun()

if st.session_state.get('final_data') is not None:
    st.button("↩️ Kembali ke Awal", on_click=lambda: st.session_state.clear() or st.rerun())
