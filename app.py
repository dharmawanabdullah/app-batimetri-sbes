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
    st.session_state['outlier_action'] = None  # 'remove', 'keep', atau 'none'

# --- Judul Aplikasi ---
st.title("Aplikasi Pengolahan Data Batimetri SBES")

# --- Penjelasan Singkat ---
st.markdown("""
Aplikasi ini digunakan untuk mengolah data batimetri dari Single Beam Echosounder.
Langkah-langkahnya meliputi:
1. Input Data Batimetri, Pasut, dan Datum Pasut.
2. Deteksi dan Penanganan Outlier (Data Error).
3. Koreksi Pasang Surut dan Transformasi UTM.
4. Download Hasil.
""")

# --- Tahap 1: Upload File ---
st.header("1. Input Data Batimetri, Pasut, dan Datum Pasut")

uploaded_files_bati = st.file_uploader(
    "Upload file-file batimetri (.txt dari folder data_bati)",
    type=["txt"],
    accept_multiple_files=True,
    key="bati_files"
)
uploaded_file_pasut = st.file_uploader(
    "Upload file data pasang surut (pasut.txt)",
    type=["txt"],
    key="pasut_file"
)
uploaded_file_datum = st.file_uploader(
    "Upload file datum pasang surut (datum_pasut.txt)",
    type=["txt"],
    key="datum_file"
)

if st.button("Proses Data", disabled=not all([uploaded_files_bati, uploaded_file_pasut, uploaded_file_datum])):
    try:
        # --- Proses Data Batimetri ---
        bati_list = []
        for uploaded_file in uploaded_files_bati:
            df_temp = pd.read_csv(uploaded_file, dtype=str, encoding='latin1', sep="\t", header=None)
            bati_list.append(df_temp)
        bati_compile = pd.concat(bati_list, ignore_index=True)

        # Cleaning seperti di notebook
        bati = bati_compile.copy()
        bati["timestamp"] = pd.to_datetime(bati[0] + " " + bati[1], format="%d-%b-%y %H:%M:%S", errors='coerce')
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

        # --- Proses Data Pasut ---
        data_pasut = pd.read_csv(uploaded_file_pasut, dtype=str, sep="\t", encoding='latin1')
        data_pasut["Timestamp"] = pd.to_datetime(data_pasut["Timestamp"], format="%Y-%m-%d %H:%M:%S", errors='coerce')
        data_pasut["Depth"] = pd.to_numeric(data_pasut["Depth"], errors="coerce")
        data_pasut = data_pasut.dropna()
        st.session_state['data_pasut'] = data_pasut
        st.success(f"Data pasut berhasil diproses. Jumlah baris: {len(data_pasut)}")

        # --- Proses Datum Pasut ---
        datum_pasut = pd.read_csv(uploaded_file_datum, dtype=str, sep="\t", encoding='latin1')
        datum_pasut = datum_pasut.apply(pd.to_numeric, errors='coerce')
        HWS = datum_pasut["HWS"].iloc[0]
        MSL = datum_pasut["MSL"].iloc[0]
        LWS = datum_pasut["LWS"].iloc[0]
        st.session_state['datum_pasut'] = (HWS, MSL, LWS)
        st.success(f"Data datum berhasil diproses. HWS: {HWS:.3f}, MSL: {MSL:.3f}, LWS: {LWS:.3f}")

        # Tampilkan pesan bahwa upload selesai
        st.info("Upload dan pembersihan awal selesai. Silakan lanjutkan ke tahap berikutnya.")

    except Exception as e:
        st.error(f"Error saat membaca atau memproses file: {e}")
        st.stop()

# --- Tampilkan Hasil Upload ---
if st.session_state.get('cleaned_bati_data') is not None or st.session_state.get('data_pasut') is not None or st.session_state.get('datum_pasut') is not None:
    st.header("Hasil Upload dan Pembersihan Awal")
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
            data_pasut = st.session_state['data_pasut']

            # Buat plot
            fig, ax = plt.subplots(figsize=(12, 5))

            # Plot garis
            ax.plot(data_pasut["Timestamp"], data_pasut["Depth"], linewidth=1.5, color='blue')

            # Set judul
            start_date = data_pasut["Timestamp"].min().strftime("%d %b %Y")
            end_date = data_pasut["Timestamp"].max().strftime("%d %b %Y")
            ax.set_title(f"Grafik Pasang Surut ({start_date} – {end_date})", fontsize=14, fontweight='bold')

            # Set label sumbu
            ax.set_xlabel("Waktu Pengamatan", fontsize=12)
            ax.set_ylabel("Tinggi Muka Air (meter)", fontsize=12)

            # Tambahkan grid
            ax.grid(True, linestyle='--', alpha=0.5)

            # Atur rotasi label x-axis agar tidak tumpang tindih
            plt.xticks(rotation=0, ha='center', fontsize=10)

            # Atur rotasi label y-axis 
            plt.yticks(fontsize=8)

            # Tampilkan plot
            st.pyplot(fig)
            plt.clf() # Bersihkan plot agar tidak mengganggu plot berikutnya

            st.success("Grafik pasang surut berhasil dibuat.")
        except Exception as e:
            st.error(f"Terjadi error saat membuat grafik pasang surut: {e}")

    if st.session_state.get('datum_pasut') is not None:
        st.subheader("Data Datum Pasang Surut")
        HWS, MSL, LWS = st.session_state['datum_pasut']
        st.write(f"HWS: {HWS:.3f}, MSL: {MSL:.3f}, LWS: {LWS:.3f}")


# --- Tahap 2: Deteksi dan Penanganan Outlier ---
st.header("2. Deteksi dan Penanganan Outlier (Data Error)")

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
    data_pasut = st.session_state['data_pasut']
    HWS, MSL, LWS = st.session_state['datum_pasut']

    # --- Koreksi Pasut ---
    st.subheader("Melakukan Koreksi Pasang Surut...")
    try:
        bati_koreksi = bati_clean.copy()
        # Interpolasi nilai pasut ke waktu pengukuran batimetri
        bati_koreksi["pasut_interp"] = np.interp(
            bati_koreksi["timestamp"].astype(np.int64),
            data_pasut["Timestamp"].astype(np.int64),
            data_pasut["Depth"].values  # Gunakan .values untuk numpy array
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
    st.dataframe(final_df)

    # Plot lintasan (longitude vs latitude) - versi sederhana
    st.subheader("Sebaran Titik Pengukuran (Longitude vs Latitude)")
    fig, ax = plt.subplots(figsize=(8,6))
    ax.scatter(final_df['longitude'], final_df['latitude'], s=6)
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
            c=-final_df['kedalaman'],  # Warna berdasarkan kedalaman
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