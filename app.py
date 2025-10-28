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
if 'datum_pasut' not in st.session_state: # Menyimpan (HWS, MSL, LWS) dari input manual
    st.session_state['datum_pasut'] = None
if 'final_data' not in st.session_state:
    st.session_state['final_data'] = None
if 'outlier_action' not in st.session_state:
    st.session_state['outlier_action'] = None  # 'remove', 'keep', atau 'none'
if 'date_format' not in st.session_state:
    st.session_state['date_format'] = None # Menyimpan format tanggal batimetri
if 'date_format_pasut' not in st.session_state:
    st.session_state['date_format_pasut'] = None # Menyimpan format tanggal pasut
if 'time_format_pasut' not in st.session_state:
    st.session_state['time_format_pasut'] = None # Menyimpan format waktu pasut

# --- Judul Aplikasi ---
st.title("Aplikasi Pengolahan Data Batimetri SBES")

# --- Penjelasan Singkat ---
st.markdown("""
Aplikasi ini digunakan untuk mengolah data batimetri dari Single Beam Echosounder.
Langkah-langkahnya meliputi:
1. Upload file data batimetri (folder `data_bati/*.txt`).
2. Pilih format tanggal data batimetri.
3. Upload file data pasang surut (`pasut.txt`) - Kolom Tanggal dan Waktu Terpisah.
4. Pilih format tanggal dan waktu data pasut.
5. Input manual datum pasang surut (HWS, MSL, LWS).
6. Proses pembersihan, deteksi outlier, dan koreksi pasang surut.
7. Transformasi koordinat ke UTM.
8. Download hasil akhir.
""")

# --- Tahap 1: Inisiasi Awal dan Input Data ---
st.header("1. Inisiasi Awal dan Input Data")

uploaded_files_bati = st.file_uploader(
    "Upload file-file batimetri (.txt dari folder data_bati)",
    type=["txt"],
    accept_multiple_files=True,
    key="bati_files"
)

# --- Input Format Tanggal Batimetri (ditempatkan setelah upload file bati) ---
# Pilihan format tanggal umum
format_options_bati = {
    "DD-Mon-YY (misal: 01-Jul-23)": "%d-%b-%y", # Format dari file contoh
    "DD-MM-YY (misal: 01-07-23)": "%d-%m-%y",
    "DD/MM/YY (misal: 01/07/23)": "%d/%m/%y",
    "DD-MM-YYYY (misal: 01-07-2023)": "%d-%m-%Y",
    "DD/MM/YYYY (misal: 01/07/2023)": "%d/%m/%Y",
    "MM-DD-YY (misal: 07-01-23)": "%m-%d-%y",
    "MM/DD/YY (misal: 07/01/23)": "%m/%d/%y",
    "MM-DD-YYYY (misal: 07-01-2023)": "%m-%d-%Y",
    "MM/DD/YYYY (misal: 07/01-2023)": "%m/%d/%Y",
    # Tambahkan opsi lain jika diperlukan
}

selected_format_label_bati = st.selectbox(
    "Pilih format tanggal data batimetri:",
    options=list(format_options_bati.keys()),
    key="date_format_selectbox_bati",
    disabled=not bool(uploaded_files_bati) # Disable jika belum upload file bati
)

# Ambil format yang dipilih dan simpan ke session state
if selected_format_label_bati:
    selected_format_bati = format_options_bati[selected_format_label_bati]
    st.session_state['date_format'] = selected_format_bati
    st.write(f"Format tanggal batimetri yang dipilih: `{selected_format_bati}`")
else:
    # Jika belum dipilih, gunakan default (format lama) atau tunda proses
    st.session_state['date_format'] = None # Atau beri nilai default jika diinginkan
    st.info("Silakan pilih format tanggal batimetri setelah upload file.")


uploaded_file_pasut = st.file_uploader(
    "Upload file data pasang surut (pasut.txt) - Kolom Tanggal dan Waktu Terpisah (tanpa header)",
    type=["txt"],
    key="pasut_file"
)

# --- Input Format Tanggal dan Waktu Pasut (ditempatkan setelah upload file pasut) ---
# Pilihan format tanggal umum untuk pasut - SESUAI DENGAN DATA ANDA
format_options_pasut_date = {
    "DD/MM/YYYY (misal: 21/06/2023)": "%d/%m/%Y", # Format yang digunakan dalam data Anda
    "YYYY-MM-DD (misal: 2023-06-21)": "%Y-%m-%d",
    "DD-MM-YYYY (misal: 21-06-2023)": "%d-%m-%Y",
    "DD-Mon-YYYY (misal: 21-Jun-2023)": "%d-%b-%Y",
    # Tambahkan opsi lain jika diperlukan
}

# Pilihan format waktu umum untuk pasut
format_options_pasut_time = {
    "HH:MM:SS (misal: 13:30:00)": "%H:%M:%S",
    "HH:MM (misal: 13:30)": "%H:%M",
    # Tambahkan opsi lain jika diperlukan
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

    # Ambil format yang dipilih dan simpan ke session state
    if selected_format_label_pasut_date and selected_format_label_pasut_time:
        selected_format_pasut_date = format_options_pasut_date[selected_format_label_pasut_date]
        selected_format_pasut_time = format_options_pasut_time[selected_format_label_pasut_time]
        st.session_state['date_format_pasut'] = selected_format_pasut_date
        st.session_state['time_format_pasut'] = selected_format_pasut_time
        st.write(f"Format tanggal pasut yang dipilih: `{selected_format_pasut_date}`")
        st.write(f"Format waktu pasut yang dipilih: `{selected_format_pasut_time}`")
    else:
        st.session_state['date_format_pasut'] = None
        st.session_state['time_format_pasut'] = None
        st.info("Silakan pilih format tanggal dan waktu pasut.")
else:
    st.session_state['date_format_pasut'] = None
    st.session_state['time_format_pasut'] = None
    st.info("Upload file pasut terlebih dahulu untuk memilih format.")


# Input manual untuk datum pasut
st.subheader("Input Manual Datum Pasang Surut")
hws_input = st.number_input("Tinggi Muka Air (HWS) dalam meter (misal: 2.90)", key="hws_input", format="%.3f")
msl_input = st.number_input("Tinggi Muka Air Rata-rata (MSL) dalam meter (misal: 1.59)", key="msl_input", format="%.3f")
lws_input = st.number_input("Rendah Muka Air (LWS) dalam meter (misal: 0.27)", key="lws_input", format="%.3f")

# Tombol untuk memulai proses - tambahkan pengecekan format
start_processing = st.button("Proses Data", disabled=not all([
    uploaded_files_bati,
    uploaded_file_pasut,
    hws_input is not None,
    msl_input is not None,
    lws_input is not None,
    st.session_state.get('date_format'),
    st.session_state.get('date_format_pasut'),
    st.session_state.get('time_format_pasut')
]))

if start_processing:
    try:
        # --- Proses Data Batimetri ---
        bati_list = []
        for uploaded_file in uploaded_files_bati:
            df_temp = pd.read_csv(uploaded_file, dtype=str, encoding='latin1', sep="\t", header=None)
            bati_list.append(df_temp)
        bati_compile = pd.concat(bati_list, ignore_index=True)

        # Cleaning seperti di notebook
        bati = bati_compile.copy()
        # Gunakan format tanggal yang dipilih dari session state
        format_tanggal_bati = st.session_state['date_format']
        if not format_tanggal_bati:
             st.error("Format tanggal batimetri belum dipilih.")
             st.stop()
        # Gabungkan kolom tanggal dan waktu
        bati["timestamp"] = pd.to_datetime(bati[0] + " " + bati[1], format=f"{format_tanggal_bati} %H:%M:%S", errors='coerce')
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
        bati_drop = bati_drop.sort_values("timestamp").reset_index(drop=True)

        st.session_state['cleaned_bati_data'] = bati_drop
        st.success(f"Data batimetri berhasil diproses. Jumlah baris: {len(bati_drop)}")

        # --- Proses Data Pasut (dengan kolom terpisah, tanpa header) ---
        # Baca file tanpa header
        data_pasut_raw = pd.read_csv(uploaded_file_pasut, dtype=str, sep="\t", encoding='latin1', header=None)

        # Tampilkan preview data pasut (untuk membantu pengguna)
        st.subheader("Preview Data Pasang Surut (sebelum pemrosesan):")
        st.dataframe(data_pasut_raw.head())

        # Ambil format dari session state
        format_date_pasut = st.session_state['date_format_pasut']
        format_time_pasut = st.session_state['time_format_pasut']

        if not format_date_pasut or not format_time_pasut:
             st.error("Format tanggal atau waktu pasut belum dipilih.")
             st.stop()

        # Gunakan indeks kolom secara eksplisit: [0] untuk Date, [1] untuk Time, [2] untuk Depth
        date_col_index = 0
        time_col_index = 1
        depth_col_index = 2

        # Gabungkan tanggal dan waktu
        try:
            # Konversi ke string untuk memastikan operasi gabungan berhasil
            combined_datetime_str = data_pasut_raw[date_col_index].astype(str) + " " + data_pasut_raw[time_col_index].astype(str)
            # Ubah menjadi datetime
            data_pasut_raw["Timestamp"] = pd.to_datetime(combined_datetime_str, format=f"{format_date_pasut} {format_time_pasut}", errors='coerce')
            # Konversi depth ke numerik
            data_pasut_raw["Depth"] = pd.to_numeric(data_pasut_raw[depth_col_index], errors="coerce")
            # Buang baris dengan timestamp atau depth yang error
            data_pasut = data_pasut_raw.dropna(subset=["Timestamp", "Depth"])[["Timestamp", "Depth"]].reset_index(drop=True)

            # Periksa apakah ada data yang valid
            if len(data_pasut) == 0:
                st.error("Tidak ada data pasut yang valid setelah pembersihan. Pastikan format tanggal dan waktu sesuai dengan data.")
                st.stop()

            st.session_state['data_pasut'] = data_pasut
            st.success(f"Data pasut berhasil diproses. Jumlah baris: {len(data_pasut)}")

        except Exception as e:
            st.error(f"Error saat menggabungkan tanggal dan waktu: {e}")
            st.stop()

        # --- Ambil Datum Pasut dari Input Manual ---
        # Simpan input ke session state
        st.session_state['datum_pasut'] = (hws_input, msl_input, lws_input)
        st.success(f"Data datum berhasil disimpan dari input manual. HWS: {hws_input:.3f}, MSL: {msl_input:.3f}, LWS: {lws_input:.3f}")

    except Exception as e:
        st.error(f"Error saat membaca atau memproses file: {e}")
        st.stop()

# --- Tampilkan Hasil Upload dan Input Datum ---
if st.session_state.get('cleaned_bati_data') is not None or st.session_state.get('data_pasut') is not None or st.session_state.get('datum_pasut') is not None:
    st.header("Hasil Upload dan Input Datum")
    if st.session_state.get('cleaned_bati_data') is not None:
        st.subheader("Data Batimetri")
        st.write(f"Jumlah baris setelah cleaning: {len(st.session_state['cleaned_bati_data'])}")
        st.dataframe(st.session_state['cleaned_bati_data'].head())

    if st.session_state.get('data_pasut') is not None:
        st.subheader("Data Pasang Surut")
        st.write(f"Jumlah baris: {len(st.session_state['data_pasut'])}")
        st.dataframe(st.session_state['data_pasut'].head())

        # --- Plot Grafik Pasang Surut ---
        st.subheader("Grafik Pasang Surut")

        try:
            # Ambil data pasut dari session state
            data_pasut_plot = st.session_state['data_pasut']

            # Buat plot
            fig, ax = plt.subplots(figsize=(12, 5))

            # Plot garis
            ax.plot(data_pasut_plot["Timestamp"], data_pasut_plot["Depth"], linewidth=1.5, color='blue')

            # Set judul
            start_date = data_pasut_plot["Timestamp"].min().strftime("%d %b %Y")
            end_date = data_pasut_plot["Timestamp"].max().strftime("%d %b %Y")
            ax.set_title(f"Grafik Pasang Surut ({start_date} – {end_date})", fontsize=14, fontweight='bold')

            # Set label sumbu
            ax.set_xlabel("Waktu Pengamatan", fontsize=12)
            ax.set_ylabel("Tinggi Muka Air (meter)", fontsize=12)

            # Tambahkan grid
            ax.grid(True, linestyle='--', alpha=0.5)

            # Atur rotasi label x-axis agar tidak tumpang tindih
            plt.xticks(rotation=45, ha='right')

            # Tampilkan plot
            st.pyplot(fig)
            plt.clf() # Bersihkan plot agar tidak mengganggu plot berikutnya

            st.success("Grafik pasang surut berhasil dibuat.")

        except Exception as e:
            st.error(f"Terjadi error saat membuat grafik pasang surut: {e}")

    if st.session_state.get('datum_pasut') is not None:
        st.subheader("Datum Pasang Surut (Input Manual)")
        HWS, MSL, LWS = st.session_state['datum_pasut']
        st.write(f"**HWS:** {HWS:.3f} m")
        st.write(f"**MSL:** {MSL:.3f} m")
        st.write(f"**LWS:** {LWS:.3f} m")


# --- Tahap 2: Deteksi dan Penanganan Outlier ---
st.header("2. Deteksi dan Penanganan Outlier")

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
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR

    # Temukan outlier
    outliers = bati_drop[(bati_drop['kedalaman'] < lower_bound) | (bati_drop['kedalaman'] > upper_bound)]
    num_outliers = len(outliers)

    st.write(f"**Jumlah outlier yang terdeteksi (berdasarkan IQR):** {num_outliers}")

    if num_outliers > 0:
        # Tampilkan data outlier jika ditemukan
        st.write("Contoh data outlier:")
        st.dataframe(outliers[['timestamp', 'longitude', 'latitude', 'kedalaman']].head(10))

        # --- DUA TOMBOL PILIHAN ---
        st.subheader("Apakah anda ingin menghapus data outlier?")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("✅ Ya, hapus semua data outlier", key="remove_outliers_btn_new"):
                # Simpan keputusan dan hasilnya
                bati_clean = bati_drop[(bati_drop['kedalaman'] >= lower_bound) & (bati_drop['kedalaman'] <= upper_bound)].copy()
                st.session_state['bati_clean'] = bati_clean
                st.session_state['outlier_action'] = 'remove'
                st.success(f"Outlier telah dihapus. Jumlah baris sekarang: {len(bati_clean)}")

        with col2:
            if st.button("❌ Tidak, lanjutkan dengan data outlier", key="keep_outliers_btn_new"):
                # Simpan data asli
                st.session_state['bati_clean'] = bati_drop.copy()
                st.session_state['outlier_action'] = 'keep'
                st.warning("Penghapusan outlier dibatalkan. Proses akan dilanjutkan dengan data termasuk outlier.")

    else:
        # Jika tidak ada outlier
        st.info("Tidak ditemukan outlier berdasarkan metode IQR.")
        # Langsung simpan data asli
        st.session_state['bati_clean'] = bati_drop.copy()
        st.session_state['outlier_action'] = 'none' # Tidak ada aksi karena tidak ada outlier
        st.success("Tidak ada outlier ditemukan. Proses akan dilanjutkan.")

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
    HWS, MSL, LWS = st.session_state['datum_pasut'] # Ambil dari input manual

    # --- Koreksi Pasut ---
    st.subheader("Melakukan Koreksi Pasang Surut...")
    try:
        bati_koreksi = bati_clean.copy()
        # Interpolasi nilai pasut ke waktu pengukuran batimetri
        bati_koreksi["pasut_interp"] = np.interp(
            bati_koreksi["timestamp"].astype(np.int64),
            data_pasut_koreksi["Timestamp"].astype(np.int64),
            data_pasut_koreksi["Depth"].values  # Gunakan .values untuk numpy array
        )
        # Koreksi Pasang Surut untuk setiap Datum
        bati_koreksi['D_LWS'] = -(bati_koreksi['kedalaman'] + (LWS - bati_koreksi["pasut_interp"]))
        bati_koreksi['D_MSL'] = -(bati_koreksi['kedalaman'] + (MSL - bati_koreksi["pasut_interp"]))
        bati_koreksi['D_HWS'] = -(bati_koreksi['kedalaman'] + (HWS - bati_koreksi["pasut_interp"]))

        st.success("Koreksi pasang surut berhasil.")

    except Exception as e:
        st.error(f"Error saat melakukan koreksi pasang surut: {e}")
        st.stop()

    # --- Transformasi UTM ---
    st.subheader("Melakukan Transformasi Koordinat ke UTM...")
    try:
        def lonlat_to_utm_per_point(df, lon_col="longitude", lat_col="latitude"):
            """ Konversi koordinat(lon/lat) ke UTM dengan deteksi zona otomatis untuk setiap titik """
            lon = df[lon_col].values
            lat = df[lat_col].values
            # 1. Hitung zona UTM tiap titik
            utm_zones = np.floor((lon + 180) / 6).astype(int) + 1
            # 2. Tentukan belahan bumi
            hemispheres = np.where(lat >= 0, "N", "S")
            # 3. Buat EPSG code per titik
            epsg_codes = np.where(lat >= 0, 32600 + utm_zones, 32700 + utm_zones)
            # 4. Siapkan kolom kosong untuk hasil UTM
            x_utm = np.zeros(len(df))
            y_utm = np.zeros(len(df))
            # 5. Loop per zona unik agar efisien
            for epsg in np.unique(epsg_codes):
                mask = epsg_codes == epsg
                transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
                x_tmp, y_tmp = transformer.transform(lon[mask], lat[mask])
                x_utm[mask] = x_tmp
                y_utm[mask] = y_tmp
            # 6. Gabungkan zona dan hemisphere jadi satu kolom, misal '49 S'
            utm_zone_str = [f"{z}{h}" for z, h in zip(utm_zones, hemispheres)]
            # 7. Tambahkan ke DataFrame
            df["Zona_UTM"] = utm_zone_str
            df["X_UTM"] = x_utm
            df["Y_UTM"] = y_utm
            # 8. Info ringkasan zona
            unique_zones = sorted(df["Zona_UTM"].unique())
            st.write(f"Ditemukan {len(unique_zones)} zona UTM: {', '.join(unique_zones)}")
            return df

        bati_koreksi_utm = lonlat_to_utm_per_point(bati_koreksi, lon_col="longitude", lat_col="latitude")

        # Simpan hasil akhir
        st.session_state['final_data'] = bati_koreksi_utm
        st.success("Transformasi UTM berhasil!")

    except Exception as e:
        st.error(f"Error saat melakukan transformasi UTM: {e}")
        st.stop()

else:
    st.warning("Data untuk koreksi belum tersedia. Pastikan Anda telah menyelesaikan tahap upload dan penanganan outlier.")

# --- Tampilkan Hasil Akhir (Koreksi dan Transformasi) ---
if st.session_state.get('final_data') is not None:
    st.header("Hasil Akhir: Data Terkoreksi dan Tertransformasi")
    final_df = st.session_state['final_data']
    st.write("Contoh data setelah koreksi dan transformasi:")
    st.dataframe(final_df.head())

    # Plot lintasan (longitude vs latitude) - versi sederhana
    st.subheader("Sebaran Titik Pengukuran (Longitude vs Latitude)")
    fig, ax = plt.subplots(figsize=(8,6))
    ax.scatter(final_df['longitude'], final_df['latitude'])
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_title('Sebaran Titik Pengukuran Batimetri')
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.axis('equal')
    st.pyplot(fig)
    plt.clf()

    # --- Plot dengan Cartopy (Sebaran Titik Pengukuran dengan Peta dan Garis Pantai) ---
    st.subheader("Sebaran Titik Pengukuran dengan Peta (Menggunakan Cartopy)")

    try:
        import cartopy.crs as ccrs
        import cartopy.feature as cfeature
        # Impor formatter dari cartopy.mpl.ticker, bukan dari ccrs
        from cartopy.mpl.ticker import LongitudeFormatter, LatitudeFormatter

        # Buat figure dan axis dengan proyeksi peta
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())

        # Tambahkan fitur peta dasar: daratan, laut, dan garis pantai
        ax.add_feature(cfeature.LAND, color='lightgreen')
        ax.add_feature(cfeature.OCEAN, color='lightblue')
        ax.add_feature(cfeature.COASTLINE, linewidth=0.5, edgecolor='black') # Garis pantai tebal
        ax.add_feature(cfeature.BORDERS, linestyle=':', linewidth=0.5)

        # Plot titik-titik pengukuran
        # Gunakan kedalaman sebagai warna (colorbar)
        sc = ax.scatter(
            final_df['longitude'],
            final_df['latitude'],
            c=-final_df['kedalaman'],  # Warna berdasarkan kedalaman (negatif untuk sesuai 'turbo_r')
            cmap='turbo_r',           # Palet warna
            s=8,                     # Ukuran titik
            transform=ccrs.PlateCarree(), # Transformasi koordinat
            edgecolors='none',       # Garis pinggir
            linewidth=0.1
        )

        # Tambahkan colorbar
        cbar = plt.colorbar(sc, ax=ax, shrink=0.7)
        cbar.set_label('Kedalaman (m)')

        # Set batas peta agar fokus pada area pengukuran
        # Hitung batas otomatis dari data
        min_lon = final_df['longitude'].min() - 0.2
        max_lon = final_df['longitude'].max() + 0.2
        min_lat = final_df['latitude'].min() - 0.2
        max_lat = final_df['latitude'].max() + 0.2

        ax.set_extent([min_lon, max_lon, min_lat, max_lat], crs=ccrs.PlateCarree())

        # Tambahkan grid dan label
        gl = ax.gridlines(draw_labels=True, linewidth=0.5, color='gray', alpha=0.5, linestyle='--')

        # Atur formatter untuk label longitude dan latitude
        gl.xformatter = LongitudeFormatter()
        gl.yformatter = LatitudeFormatter()

        # Atur ukuran font untuk label koordinat
        gl.xlabel_style = {'size': 8}  # Ukuran font untuk label longitude
        gl.ylabel_style = {'size': 8}  # Ukuran font untuk label latitude

        # Matikan label di atas dan kanan jika ingin tampilan lebih bersih
        gl.top_labels = False
        gl.right_labels = False

        # Atur ukuran font untuk judul plot
        ax.set_title('Sebaran Titik Pengukuran Batimetri', fontsize=14, weight='bold')

        # Tampilkan plot
        st.pyplot(fig)
        plt.clf()

        st.success("Plot Cartopy berhasil dibuat.")

    except ImportError:
        st.warning("Library 'cartopy' belum terinstal. Plot peta tidak dapat ditampilkan.")
        st.info("Untuk menampilkan plot peta, silakan instal cartopy dengan perintah: `pip install cartopy` atau `conda install -c conda-forge cartopy`")

    except Exception as e:
        st.error(f"Terjadi error saat membuat plot Cartopy: {e}")


# --- Tahap 4: Download ---
st.header("4. Download Hasil")

if st.session_state.get('final_data') is not None:
    final_df = st.session_state['final_data']
    st.success("✅ Proses Pengolahan Data Selesai! Data siap untuk diunduh.")

    # Buat file-file output
    output_files = {}
    for zona in final_df["Zona_UTM"].unique():
        subset_zone = final_df[final_df["Zona_UTM"] == zona]
        for datum in ["D_LWS", "D_MSL", "D_HWS"]:
            file_name = f"Batimetri_{zona.replace(' ', '')}_{datum.split('_')[1]}.txt"
            subset_xyz = subset_zone[["X_UTM", "Y_UTM", datum]].copy()
            subset_xyz.columns = ["X", "Y", "Z"]
            output_files[file_name] = subset_xyz.to_csv(sep=' ', index=False, header=False, float_format='%.3f')

    # Tawarkan download
    st.subheader("Pilih file yang ingin Anda unduh:")
    for file_name, file_content in output_files.items():
        st.download_button(
            label=f"📥 Download {file_name}",
            data=file_content,
            file_name=file_name,
            mime="text/plain"
        )

    # Tombol untuk proses ulang
    if st.button("🔄 Proses Ulang"):
        # Reset session state
        st.session_state.clear()
        st.rerun()

else:
    st.warning("Data akhir belum tersedia. Pastikan semua tahap sebelumnya telah selesai.")
    st.info("Jika Anda yakin proses sudah selesai, silakan klik tombol 'Proses Ulang' di bawah ini.")
    if st.button("🔄 Proses Ulang"):
        st.session_state.clear()
        st.rerun()

# --- Tombol Kembali ke Awal ---
if st.session_state.get('final_data') is not None:
    st.button("↩️ Kembali ke Awal", on_click=lambda: st.session_state.clear() or st.rerun())
