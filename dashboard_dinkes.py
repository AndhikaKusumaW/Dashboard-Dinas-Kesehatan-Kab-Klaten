import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import base64

# konfigurasi halaman
st.set_page_config(page_title="Dashboard Dinkes Klaten", layout="wide")

# fungsi load data
def load_data_with_sheet(file, sheet_name=None):
    """
    Membaca file Excel pada Sheet tertentu, lalu mencari Header otomatis.
    """
    try:
        if file.name.endswith('.csv'):
            df_raw = pd.read_csv(file, header=None)
        else:
            df_raw = pd.read_excel(file, sheet_name=sheet_name, header=None, engine='openpyxl')
        
        header_idx = 0
        for i in range(min(15, len(df_raw))): 
            row_str = df_raw.iloc[i].astype(str).tolist()
            text_cols = sum([1 for x in row_str if any(c.isalpha() for c in x) and 'nan' not in x.lower()])
        
            if text_cols > (df_raw.shape[1] * 0.4):
                header_idx = i
                break
        
        if file.name.endswith('.csv'):
            df = pd.read_csv(file, header=header_idx)
        else:
            df = pd.read_excel(file, sheet_name=sheet_name, header=header_idx, engine='openpyxl')
            
        return df
        
    except Exception as e:
        return None

# logo
def tampilkan_logo_tengah(file_path, lebar=150):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        bin_str = base64.b64encode(data).decode()
        html_code = f"""
            <div style="display: flex; justify-content: center; margin-bottom: 10px;">
                <img src="data:image/png;base64,{bin_str}" width="{lebar}px">
            </div>
        """
        st.markdown(html_code, unsafe_allow_html=True)
    except FileNotFoundError:
        pass

# header 
tampilkan_logo_tengah("logo.png", lebar=100) 

st.markdown("""
    <div style='text-align: center;'>
        <h2 style='color: #333333; margin-bottom: 0;'>DINAS KESEHATAN KAB. KLATEN</h2>
        <h4 style='color: #555555;'>Portal Data & Informasi Kesehatan</h4>
    </div>
    <hr>
""", unsafe_allow_html=True)

# sidebar
with st.sidebar:
    st.header("📂 Panel Kontrol")
    upload_file = st.file_uploader("Upload File (Excel/CSV):", type=["xlsx", "xls", "csv"])

if upload_file is not None:
    
    selected_sheet = 0
    
    if not upload_file.name.endswith('.csv'):    
        try:
            excel_file = pd.ExcelFile(upload_file)
            sheet_names = excel_file.sheet_names
            
            st.sidebar.markdown("---")
            st.sidebar.subheader("📄 Pilih Sheet Data")
            
            default_index = 1 if len(sheet_names) > 1 else 0
            
            selected_sheet = st.sidebar.selectbox(
                "Pilih Sheet yang mau dibaca:", 
                sheet_names, 
                index=default_index
            )
            st.sidebar.info(f"Membaca sheet: **{selected_sheet}**")
            
        except Exception as e:
            st.error(f"Error membaca struktur Excel: {e}")

    df = load_data_with_sheet(upload_file, sheet_name=selected_sheet)
    
    if df is not None:
        clean_columns = [
            c for c in df.columns 
            if "Unnamed" not in str(c)
            and str(c).strip().lower() not in ['no', 'no.', 'No', 'NO', 'nomor', 'Nomor', 'NOMOR']    
        ]
        
        st.sidebar.markdown("---")
        st.sidebar.subheader("🛠️ Konfigurasi Grafik")
        
        target_col = st.sidebar.selectbox("1. Pilih Kolom Label/Nama:", clean_columns)
        
        # cleaning data
        try:
            df[target_col] = df[target_col].astype(str).str.replace('%','').str.replace(',','')
            df[target_col] = pd.to_numeric(df[target_col], errors='ignore')
        except:
            pass
            
        is_numeric = pd.api.types.is_numeric_dtype(df[target_col])
        
        # visualisasi
        st.subheader(f"📊 Analisis: {target_col}")
        
        col_viz, col_desc = st.columns([2, 1])

        with col_viz:
            if is_numeric:
                avg_val = df[target_col].mean()
                max_val = df[target_col].max()
                
                fig = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = avg_val,
                    title = {'text': f"Rata-rata {target_col}"},
                    gauge = {
                        'axis': {'range': [0, max_val * 1.2]}, 
                        'bar': {'color': "#F68F32"},
                        'bgcolor': "#EAEAEA"
                    }
                ))
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
                
            else:
                unique_ratio = df[target_col].nunique() / len(df)
                
                if unique_ratio > 0.8:
                    st.warning("⚠️ Kolom ini berisi Nama/Label. Silakan pilih kolom nilainya di bawah.")
                    
                    numeric_cols = df.select_dtypes(include=['float', 'int']).columns.tolist()                
                    valid_numeric = [
                        c for c in numeric_cols 
                        if df[c].mean() > 1 or df[c].max() > 100
                        and str(c).strip().lower() not in ['no', 'no.', 'No', 'NO', 'nomor', 'Nomor', 'NOMOR']    
                    ] 
                    
                    if not valid_numeric: valid_numeric = clean_columns 
                    
                    val_col = st.selectbox("2. Pilih Kolom Nilai Capaian:", valid_numeric)
                                    
                    try:
                        df[val_col] = df[val_col].astype(str).str.replace('%','').str.replace(',','')
                        df[val_col] = pd.to_numeric(df[val_col], errors='coerce')
                    except:
                        pass
                    
                    df_sorted = df.sort_values(by=val_col, ascending=True).tail(10)
                    
                    fig = px.bar(df_sorted, x=val_col, y=target_col, orientation='h', text=val_col,
                                 title=f"Capaian: {target_col}",
                                 color_discrete_sequence=['#F68F32'])
                    
                else:                    
                    data_counts = df[target_col].value_counts().reset_index()
                    data_counts.columns = ['Kategori', 'Jumlah']
                    top_10 = data_counts.head(10).sort_values(by='Jumlah', ascending=True)
                    
                    fig = px.bar(top_10, x='Jumlah', y='Kategori', orientation='h', text='Jumlah',
                                 title=f"Frekuensi: {target_col}",
                                 color_discrete_sequence=['#F68F32'])

                fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', height=400)
                st.plotly_chart(fig, use_container_width=True)

        with col_desc:
            st.info("Keterangan Data")
            st.write(f"Sheet Terpilih: **{selected_sheet if selected_sheet else 'Default'}**")
            st.write(f"Jumlah Baris: {len(df)}")
            
            with st.expander("Lihat Data Tabel"):
                st.dataframe(df.head(10))

    else:
        st.error("Gagal membaca file.")

else:
    st.info("Silakan upload file disidebar kiri.")