import streamlit as st
import google.generativeai as genai
import PyPDF2
import pytesseract
from PIL import Image
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import re
import os
import io
from typing import List, Dict, Any
from dataclasses import dataclass
import time
from dotenv import load_dotenv
from config import AVAILABLE_MODELS, KEMENTERIAN_LEMBAGA_INDONESIA, DEFAULT_MODEL
from export_utils import create_excel_report, create_pdf_report

# Load environment variables
load_dotenv()

# Konfigurasi halaman
st.set_page_config(
    page_title="Analisis Tumpang Tindih Tugas Instansi",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS untuk styling (sama seperti sebelumnya)
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #2a5298;
    }
    
    .overlap-high {
        background-color: #ffebee;
        border-left-color: #f44336;
    }
    
    .overlap-medium {
        background-color: #fff3e0;
        border-left-color: #ff9800;
    }
    
    .overlap-low {
        background-color: #e8f5e8;
        border-left-color: #4caf50;
    }
    
    .stButton > button {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 2rem;
        font-weight: bold;
    }
    
    .file-upload-section {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        border: 1px solid #dee2e6;
    }
    
    .uploaded-file-item {
        background: #e3f2fd;
        padding: 0.5rem;
        margin: 0.2rem 0;
        border-radius: 4px;
        font-size: 0.9rem;
    }

    .config-info {
        background: #e8f5e8;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #4caf50;
        margin-bottom: 1rem;
    }

    .config-error {
        background: #ffebee;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #f44336;
        margin-bottom: 1rem;
    }
    
    .model-card {
        background: #f8f9fa;
        padding: 0.8rem;
        border-radius: 6px;
        margin: 0.5rem 0;
        border-left: 3px solid #2a5298;
    }
    
    .model-recommended {
        background: #e8f5e8;
        border-left-color: #4caf50;
    }
    
    .instansi-info {
        background: #e3f2fd;
        padding: 0.5rem;
        border-radius: 4px;
        font-size: 0.9rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

@dataclass
class InstansiData:
    nama: str
    tugas_pokok: List[str]
    fungsi: List[str]
    program: List[str]
    kegiatan: List[str]
    anggaran: str
    target_sasaran: List[str]
    dokumen_sumber: List[str]

class DocumentProcessor:
    def __init__(self):
        # Set Tesseract path from environment variable
        tesseract_cmd = os.getenv('TESSERACT_CMD')
        if tesseract_cmd and os.path.exists(tesseract_cmd):
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    
    def extract_text_from_pdf(self, pdf_file) -> str:
        """Ekstrak teks dari PDF dengan fallback yang lebih robust"""
        try:
            # Reset file pointer
            pdf_file.seek(0)
            
            # Coba ekstrak teks langsung
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            # Jika teks kosong atau minimal, gunakan OCR
            if len(text.strip()) < 100:
                return self.ocr_pdf_simple(pdf_file)
            
            return text
        except Exception as e:
            st.warning(f"Error ekstraksi PDF dengan PyPDF2: {e}")
            return self.ocr_pdf_simple(pdf_file)
    
    def ocr_pdf_simple(self, pdf_file) -> str:
        """OCR sederhana tanpa poppler dependency"""
        try:
            # Reset file pointer
            pdf_file.seek(0)
            
            # Coba gunakan PyMuPDF sebagai alternatif yang lebih reliable
            try:
                import fitz  # PyMuPDF
                
                # Convert PDF to images using PyMuPDF
                pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
                text = ""
                
                for page_num in range(len(pdf_document)):
                    page = pdf_document.load_page(page_num)
                    
                    # Convert to image
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
                    img_data = pix.tobytes("png")
                    
                    # Convert to PIL Image
                    image = Image.open(io.BytesIO(img_data))
                    
                    # OCR
                    page_text = pytesseract.image_to_string(image, lang='ind+eng')
                    text += f"\n--- Halaman {page_num + 1} ---\n{page_text}\n"
                
                pdf_document.close()
                return text
                
            except ImportError:
                # Fallback: basic text extraction without images
                st.warning("⚠️ PyMuPDF tidak tersedia. Menggunakan ekstraksi teks dasar.")
                
                # Try alternative: extract what we can from PyPDF2
                pdf_file.seek(0)
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                text = ""
                
                for i, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text.strip():
                        text += f"\n--- Halaman {i + 1} ---\n{page_text}\n"
                
                if not text.strip():
                    return "Error: Tidak dapat mengekstrak teks dari PDF. Pastikan PDF tidak terenkripsi dan dapat dibaca."
                
                return text
            
        except Exception as e:
            st.error(f"Error OCR: {e}")
            return f"Error: Gagal memproses PDF - {str(e)}"
    
    def process_multiple_files(self, uploaded_files: List, file_names: List[str]) -> str:
        """Proses multiple files untuk satu instansi"""
        combined_text = ""
        
        for i, (file, name) in enumerate(zip(uploaded_files, file_names)):
            st.info(f"📄 Memproses file {i+1}/{len(uploaded_files)}: {name}")
            
            # Extract text
            text = self.extract_text_from_pdf(file)
            
            if text and not text.startswith("Error:"):
                combined_text += f"\n\n{'='*50}\n"
                combined_text += f"DOKUMEN: {name}\n"
                combined_text += f"{'='*50}\n"
                combined_text += text
            else:
                st.warning(f"⚠️ Gagal mengekstrak teks dari {name}: {text}")
        
        return combined_text

class GeminiAnalyzer:
    def __init__(self, api_key: str, model_name: str = DEFAULT_MODEL):
        genai.configure(api_key=api_key)
        self.model_name = model_name
        self.model = genai.GenerativeModel(model_name)
    
    def extract_instansi_data(self, combined_text: str, nama_instansi: str, file_names: List[str]) -> InstansiData:
        """Ekstrak data terstruktur dari multiple dokumen instansi"""
        
        # Batasi teks untuk efisiensi
        limited_text = self._smart_text_limiting(combined_text, max_chars=6000)
        
        prompt = f"""
        Analisis kumpulan dokumen instansi pemerintah Indonesia berikut dan ekstrak informasi dalam format JSON:

        Nama Instansi: {nama_instansi}
        Dokumen yang Dianalisis: {', '.join(file_names)}
        
        Dokumen Gabungan:
        {limited_text}

        INSTRUKSI EKSTRAKSI (Konteks Indonesia):
        Dari berbagai dokumen di atas, ekstrak dan konsolidasi informasi berikut sesuai dengan konteks pemerintahan Indonesia:
        
        1. Tugas Pokok (tugas_pokok): tugas utama instansi berdasarkan peraturan perundang-undangan
        2. Fungsi (fungsi): fungsi-fungsi spesifik yang disebutkan dalam SOTK atau dokumen resmi
        3. Program (program): program kerja strategis sesuai Renstra/RPJMN
        4. Kegiatan (kegiatan): kegiatan operasional spesifik dalam Renja/DIPA
        5. Anggaran (anggaran): informasi alokasi anggaran APBN/APBD
        6. Target Sasaran (target_sasaran): target/indikator kinerja yang ingin dicapai

        PETUNJUK KONSOLIDASI:
        - Gabungkan informasi dari semua dokumen
        - Hindari duplikasi (jika sama, masukkan sekali saja)
        - Prioritaskan informasi dari dokumen resmi (SOTK, Renstra, Perpres, Permen)
        - Gunakan terminologi pemerintahan Indonesia yang benar
        - Jika ada konflik informasi, ambil yang paling terbaru/lengkap

        Format output JSON:
        {{
            "tugas_pokok": ["tugas 1", "tugas 2"],
            "fungsi": ["fungsi 1", "fungsi 2"],
            "program": ["program 1", "program 2"],
            "kegiatan": ["kegiatan 1", "kegiatan 2"],
            "anggaran": "ringkasan informasi anggaran",
            "target_sasaran": ["sasaran 1", "sasaran 2"]
        }}
        
        Pastikan ekstraksi akurat dan komprehensif dari SEMUA dokumen.
        Jika informasi tidak ditemukan, gunakan array kosong.
        """
        
        try:
            response = self.model.generate_content(prompt)
            json_str = response.text.strip()
            if json_str.startswith('```json'):
                json_str = json_str[7:-3]
            elif json_str.startswith('```'):
                json_str = json_str[3:-3]
            
            data = json.loads(json_str)
            
            return InstansiData(
                nama=nama_instansi,
                tugas_pokok=data.get('tugas_pokok', []),
                fungsi=data.get('fungsi', []),
                program=data.get('program', []),
                kegiatan=data.get('kegiatan', []),
                anggaran=data.get('anggaran', ''),
                target_sasaran=data.get('target_sasaran', []),
                dokumen_sumber=file_names
            )
        except Exception as e:
            st.error(f"Error parsing data untuk {nama_instansi}: {e}")
            return InstansiData(nama_instansi, [], [], [], [], '', [], file_names)
    
    def _smart_text_limiting(self, text: str, max_chars: int = 6000) -> str:
        """Smart limiting: ambil bagian penting dari teks panjang"""
        if len(text) <= max_chars:
            return text
        
        # Split berdasarkan dokumen
        documents = text.split("="*50)
        
        limited_text = ""
        remaining_chars = max_chars
        
        for doc in documents:
            if remaining_chars <= 0:
                break
                
            # Ambil bagian awal dari setiap dokumen
            doc_portion = doc[:min(len(doc), remaining_chars // max(1, len(documents) - documents.index(doc)))]
            limited_text += doc_portion
            remaining_chars -= len(doc_portion)
        
        return limited_text
    
    def analyze_overlaps(self, instansi_list: List[InstansiData]) -> Dict[str, Any]:
        """Analisis tumpang tindih antar instansi dengan konteks Indonesia"""
        
        # Prepare data untuk analisis
        instansi_summary = ""
        for i, instansi in enumerate(instansi_list):
            instansi_summary += f"""
            
INSTANSI {i+1}: {instansi.nama}
Dokumen Sumber: {', '.join(instansi.dokumen_sumber)}
Tugas Pokok: {'; '.join(instansi.tugas_pokok)}
Fungsi: {'; '.join(instansi.fungsi)}
Program: {'; '.join(instansi.program)}
Kegiatan: {'; '.join(instansi.kegiatan)}
Target Sasaran: {'; '.join(instansi.target_sasaran)}
            """
        
        prompt = f"""
        Analisis tumpang tindih tugas, fungsi, dan program antar instansi pemerintah Indonesia berikut:

        {instansi_summary}

        KONTEKS ANALISIS:
        - Sistem pemerintahan Indonesia dengan struktur kementerian/lembaga
        - Regulasi perundang-undangan Indonesia (UU, PP, Perpres, Permen)
        - Koordinasi antar K/L berdasarkan tugas dan fungsi masing-masing
        - Efisiensi anggaran APBN dan pencegahan duplikasi program
        - Best practices reformasi birokrasi Indonesia

        Berikan analisis komprehensif dalam format JSON dengan struktur:
        {{
            "ringkasan_eksekutif": "ringkasan singkat temuan utama dengan konteks Indonesia",
            "tumpang_tindih": [
                {{
                    "kategori": "tugas_pokok/fungsi/program/kegiatan",
                    "deskripsi": "deskripsi tumpang tindih dengan konteks regulasi Indonesia",
                    "instansi_terlibat": ["instansi 1", "instansi 2"],
                    "tingkat_overlap": "tinggi/sedang/rendah",
                    "dampak_potensial": "deskripsi dampak terhadap pelayanan publik/efisiensi",
                    "estimasi_pemborosan_anggaran": "persentase atau nilai rupiah jika memungkinkan",
                    "dokumen_sumber": ["dokumen yang menunjukkan overlap"],
                    "rekomendasi_koordinasi": "mekanisme koordinasi yang disarankan"
                }}
            ],
            "rekomendasi": [
                {{
                    "prioritas": "tinggi/sedang/rendah",
                    "aksi": "deskripsi aksi sesuai sistem pemerintahan Indonesia",
                    "instansi_pelaksana": "instansi yang sebaiknya menjalankan (lead agency)",
                    "instansi_pendukung": ["instansi pendukung"],
                    "timeline": "estimasi waktu implementasi",
                    "benefit_estimasi": "manfaat untuk pelayanan publik dan efisiensi",
                    "dasar_hukum": "rujukan regulasi yang mendukung",
                    "mekanisme_koordinasi": "forum/mekanisme koordinasi yang disarankan"
                }}
            ],
            "metrik_overlap": {{
                "total_overlap_ditemukan": 0,
                "overlap_tinggi": 0,
                "overlap_sedang": 0,
                "overlap_rendah": 0,
                "efisiensi_potensial": "persentase efisiensi anggaran yang dapat dicapai"
            }}
        }}

        Fokus pada:
        1. Identifikasi duplikasi tugas berdasarkan regulasi masing-masing K/L
        2. Program dengan target sasaran dan output yang sama
        3. Potensi konflik kewenangan regulasi
        4. Peluang sinergi dan kolaborasi antar K/L
        5. Optimasi alokasi anggaran APBN
        6. Perbaikan koordinasi sesuai sistem pemerintahan Indonesia

        Berikan rekomendasi yang praktis, dapat diimplementasikan, dan sesuai dengan sistem pemerintahan Indonesia.
        """
        
        try:
            response = self.model.generate_content(prompt)
            json_str = response.text.strip()
            if json_str.startswith('```json'):
                json_str = json_str[7:-3]
            elif json_str.startswith('```'):
                json_str = json_str[3:-3]
            
            return json.loads(json_str)
        except Exception as e:
            st.error(f"Error analisis overlap: {e}")
            return {"error": str(e)}

def check_api_configuration():
    """Check API configuration and display status"""
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key:
        st.markdown("""
        <div class="config-error">
            <h4>❌ Konfigurasi API Tidak Ditemukan</h4>
            <p><strong>API Key Gemini belum dikonfigurasi!</strong></p>
            <p>Silakan ikuti langkah berikut:</p>
            <ol>
                <li>Buat file <code>.env</code> di root directory</li>
                <li>Tambahkan: <code>GEMINI_API_KEY=your_api_key_here</code></li>
                <li>Dapatkan API key dari <a href="https://makersuite.google.com/app/apikey" target="_blank">Google AI Studio</a></li>
                <li>Restart aplikasi</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
        return False
    
    # Validate API key format
    if len(api_key) < 20:
        st.markdown("""
        <div class="config-error">
            <h4>⚠️ API Key Tidak Valid</h4>
            <p>Format API key tampaknya tidak benar. Pastikan Anda menggunakan API key yang valid dari Google AI Studio.</p>
        </div>
        """, unsafe_allow_html=True)
        return False
    
    return True

def display_model_info(selected_model):
    """Display information about selected model"""
    model_info = AVAILABLE_MODELS.get(selected_model, {})
    
    if model_info:
        css_class = "model-recommended" if model_info.get('recommended') else "model-card"
        recommended_badge = "⭐ RECOMMENDED" if model_info.get('recommended') else ""
        
        st.markdown(f"""
        <div class="{css_class}">
            <h4>{model_info['name']} {recommended_badge}</h4>
            <p><strong>Deskripsi:</strong> {model_info['description']}</p>
            <p><strong>Biaya:</strong> {model_info['cost']} | <strong>Kecepatan:</strong> {model_info['speed']}</p>
        </div>
        """, unsafe_allow_html=True)

def search_instansi(search_term: str, instansi_list: List[str]) -> List[str]:
    """Search instansi based on search term"""
    if not search_term:
        return instansi_list
    
    search_term = search_term.lower()
    filtered = [instansi for instansi in instansi_list if search_term in instansi.lower()]
    return filtered

def main():
    # Header
    st.markdown(f"""
    <div class="main-header">
        <h1>🏛️ SIHATI (Sistem Harmonisasi Kebijakan Terpadu Instansi)</h1>
        <p>Identifikasi Otomatis Duplikasi Tugas, Fungsi, dan Program Antar Instansi Pemerintah Indonesia</p>
        <p><small>✨ Multiple Files | 🤖 Multi-Model AI | 🔍 Smart Instansi Search</small></p>
        <p><small>📊 <a href="https://www.canva.com/design/DAGuYKmWoYY/1AGbdEog3NWoS_fa3dfeQQ/view" target="_blank">Slide Presentasi</a> | 🎯 <a href="https://drive.google.com/file/d/1bEeBMeFqlpvHc5ep8kjXzBhF2w0E5bWV/view" target="_blank">Demo Prototype</a> | 📁 <a href="https://drive.google.com/drive/folders/1bLa7nBdNSu1krA346kt2J-oqoue5R8Pd" target="_blank">Sampel Dokumen Instansi</a></small></p>
        <p><small>👤 User: sihatiuser | 📅 {time.strftime('%Y-%m-%d %H:%M:%S UTC')}</small></p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check API configuration
    if not check_api_configuration():
        st.stop()
    
    # Get API key from environment
    api_key = os.getenv('GEMINI_API_KEY')
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Konfigurasi Sistem")
        
        # Model Selection
        st.subheader("🤖 Pilihan Model AI")
        
        model_options = list(AVAILABLE_MODELS.keys())
        model_labels = [AVAILABLE_MODELS[model]['name'] for model in model_options]
        
        selected_model = st.selectbox(
            "Pilih Model AI",
            options=model_options,
            format_func=lambda x: AVAILABLE_MODELS[x]['name'],
            index=0,
            help="Pilih model AI yang akan digunakan untuk analisis"
        )
        
        # Display model info
        display_model_info(selected_model)
        
        st.markdown("---")
        
        # Jumlah instansi
        st.subheader("📊 Pengaturan Analisis")
        num_instansi = st.selectbox(
            "Jumlah Instansi yang Dibandingkan",
            options=[2, 3, 4, 5, 6],
            index=0
        )
        
        st.info(f"📊 Akan menganalisis {num_instansi} instansi dengan model **{AVAILABLE_MODELS[selected_model]['name']}**")
        
        # System status
        with st.expander("🔧 System Status"):
            st.markdown("### Model Information")
            st.json({
                "selected_model": selected_model,
                "model_name": AVAILABLE_MODELS[selected_model]['name'],
                "cost_level": AVAILABLE_MODELS[selected_model]['cost'],
                "speed_level": AVAILABLE_MODELS[selected_model]['speed']
            })
            
            st.markdown("### Available Models")
            for model_id, model_info in AVAILABLE_MODELS.items():
                status = "✅" if model_id == selected_model else "⚪"
                st.write(f"{status} {model_info['name']} - {model_info['cost']} cost, {model_info['speed']} speed")
        
        # Help section
        with st.expander("📋 Jenis Dokumen yang Didukung"):
            st.markdown("""
            **Per Instansi dapat upload multiple files:**
            - 📄 SOTK (Susunan Organisasi dan Tata Kerja)
            - 📊 Renstra (Rencana Strategis)
            - 📅 Renja (Rencana Kerja)
            - 🏛️ RKPD (Rencana Kerja Pemerintah Daerah)
            - 💰 DIPA (Daftar Isian Pelaksanaan Anggaran)
            - 📋 Peraturan Menteri/Presiden
            - 📋 Dokumen Tupoksi lainnya
            
            **Format:** PDF (digital atau scan)
            **Ukuran Max:** 50MB per file
            """)
        
        # Instansi info
        with st.expander("🏢 Database Instansi"):
            st.markdown(f"""
            **Total Instansi dalam Database:** {len(KEMENTERIAN_LEMBAGA_INDONESIA)}
            
            **Kategori:**
            - Kementerian Koordinator: 4
            - Kementerian: 30+
            - LPNK: 20+
            - TNI/Polri: 5
            - Lembaga Tinggi Negara: 12
            - Pemda: 20+ (sample)
            
            **Fitur:**
            - 🔍 Search & Filter
            - ➕ Tambah Instansi Baru
            - 📝 Auto-complete
            """)
    
    # Initialize processors dengan model yang dipilih
    doc_processor = DocumentProcessor()
    analyzer = GeminiAnalyzer(api_key, selected_model)
    
    # Main content
    st.header("📄 Upload Dokumen Instansi")
    st.info("💡 **Tip:** Setiap instansi dapat mengupload beberapa dokumen sekaligus untuk analisis yang lebih komprehensif")
    
    # Create upload sections for each instansi
    uploaded_files_data = {}
    
    # Use tabs for better organization when many instansi
    if num_instansi <= 3:
        # Use columns for 2-3 instansi
        cols = st.columns(num_instansi)
        for i in range(num_instansi):
            with cols[i]:
                instansi_data = create_instansi_upload_section(i)
                if instansi_data:
                    uploaded_files_data[i] = instansi_data
    else:
        # Use tabs for 4+ instansi
        tabs = st.tabs([f"Instansi {i+1}" for i in range(num_instansi)])
        for i, tab in enumerate(tabs):
            with tab:
                instansi_data = create_instansi_upload_section(i)
                if instansi_data:
                    uploaded_files_data[i] = instansi_data
    
    # Summary section
    if uploaded_files_data:
        st.markdown("---")
        st.subheader("📋 Ringkasan Upload")
        
        summary_cols = st.columns(len(uploaded_files_data))
        for idx, (i, data) in enumerate(uploaded_files_data.items()):
            with summary_cols[idx]:
                st.markdown(f"""
                <div class="metric-card">
                    <h4>🏢 {data['nama']}</h4>
                    <p><strong>Jumlah Dokumen:</strong> {len(data['files'])}</p>
                    <p><strong>File:</strong></p>
                    <ul style="font-size: 0.9em; margin: 0;">
                """, unsafe_allow_html=True)
                
                for file_name in data['file_names']:
                    st.markdown(f"<li>{file_name}</li>", unsafe_allow_html=True)
                
                st.markdown("</ul></div>", unsafe_allow_html=True)
    
    # Tombol Analisis
    if len(uploaded_files_data) >= 2:
        st.markdown("---")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            total_files = sum(len(data['files']) for data in uploaded_files_data.values())
            st.info(f"📊 Total {len(uploaded_files_data)} instansi, {total_files} dokumen siap dianalisis dengan **{AVAILABLE_MODELS[selected_model]['name']}**")
            
            if st.button("🔍 Mulai Analisis Tumpang Tindih", use_container_width=True):
                analyze_documents(uploaded_files_data, doc_processor, analyzer)

def create_instansi_upload_section(index: int):
    """Create upload section for one instansi with smart instansi selection"""
    
    st.markdown(f"""
    <div class="file-upload-section">
        <h3>🏢 Instansi {index + 1}</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Search dan pilih instansi
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Search box
        search_term = st.text_input(
            f"🔍 Cari Instansi {index + 1}",
            key=f"search_{index}",
            placeholder="Ketik nama kementerian/lembaga...",
            help="Cari instansi dari database atau ketik nama baru"
        )
        
        # Filter instansi berdasarkan pencarian
        if search_term:
            filtered_instansi = search_instansi(search_term, KEMENTERIAN_LEMBAGA_INDONESIA)
            if filtered_instansi:
                st.markdown(f"<div class='instansi-info'>✅ Ditemukan {len(filtered_instansi)} instansi yang cocok</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='instansi-info'>ℹ️ Tidak ada instansi yang cocok. Anda dapat menambahkan '{search_term}' sebagai instansi baru.</div>", unsafe_allow_html=True)
                filtered_instansi = [search_term]
        else:
            filtered_instansi = KEMENTERIAN_LEMBAGA_INDONESIA
    
    with col2:
        # Opsi mode input
        input_mode = st.radio(
            f"Mode Input {index + 1}",
            ["Pilih dari Database", "Input Manual"],
            key=f"mode_{index}"
        )
    
    # Pilihan instansi
    if input_mode == "Pilih dari Database":
        if search_term and len(filtered_instansi) <= 10:
            # Jika hasil pencarian sedikit, tampilkan sebagai radio button
            nama_instansi = st.radio(
                f"Pilih Instansi {index + 1}",
                options=filtered_instansi,
                key=f"instansi_radio_{index}"
            )
        else:
            # Gunakan selectbox untuk list yang panjang
            nama_instansi = st.selectbox(
                f"Pilih Instansi {index + 1}",
                options=filtered_instansi,
                key=f"instansi_select_{index}",
                help=f"Dipilih dari {len(filtered_instansi)} instansi"
            )
    else:
        # Input manual
        nama_instansi = st.text_input(
            f"Nama Instansi {index + 1}",
            key=f"nama_manual_{index}",
            placeholder="Contoh: Kementerian XYZ",
            help="Masukkan nama lengkap instansi"
        )
    
    # Info instansi yang dipilih
    if nama_instansi:
        if nama_instansi in KEMENTERIAN_LEMBAGA_INDONESIA:
            st.markdown(f"<div class='instansi-info'>✅ Instansi resmi: <strong>{nama_instansi}</strong></div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='instansi-info'>➕ Instansi baru: <strong>{nama_instansi}</strong></div>", unsafe_allow_html=True)
    
    # Multiple file uploader
    uploaded_files = st.file_uploader(
        f"Upload Dokumen Instansi {index + 1}",
        type=['pdf'],
        accept_multiple_files=True,
        key=f"files_{index}",
        help="Upload satu atau lebih dokumen PDF (SOTK, Renstra, Renja, RKPD, DIPA, dll)"
    )
    
    if uploaded_files and nama_instansi:
        # Check file sizes
        max_size = int(os.getenv('MAX_FILE_SIZE_MB', '50')) * 1024 * 1024
        oversized_files = [f for f in uploaded_files if f.size > max_size]
        
        if oversized_files:
            st.error(f"❌ File terlalu besar (max {max_size//1024//1024}MB): {', '.join([f.name for f in oversized_files])}")
            return None
        
        # Display uploaded files
        st.success(f"✅ {len(uploaded_files)} dokumen berhasil diupload:")
        
        file_names = []
        total_size = 0
        for i, file in enumerate(uploaded_files):
            file_names.append(file.name)
            total_size += file.size
            st.markdown(f"""
            <div class="uploaded-file-item">
                📄 {i+1}. {file.name} ({file.size // 1024} KB)
            </div>
            """, unsafe_allow_html=True)
        
        st.info(f"📊 Total ukuran: {total_size // 1024} KB")
        
        return {
            'nama': nama_instansi,
            'files': uploaded_files,
            'file_names': file_names
        }
    
    elif uploaded_files and not nama_instansi:
        st.warning("⚠️ Pilih atau masukkan nama instansi terlebih dahulu")
    
    return None

def analyze_documents(uploaded_files_data, doc_processor, analyzer):
    """Fungsi untuk menganalisis dokumen dengan multiple files support"""
    
    # Progress tracking
    total_instansi = len(uploaded_files_data)
    total_files = sum(len(data['files']) for data in uploaded_files_data.values())
    
    st.markdown(f"""
    <div class="metric-card">
        <h3>🔄 Memulai Analisis</h3>
        <p>📊 <strong>Total Instansi:</strong> {total_instansi}</p>
        <p>📄 <strong>Total Dokumen:</strong> {total_files}</p>
        <p>🤖 <strong>Model AI:</strong> {analyzer.model_name}</p>
        <p>👤 <strong>User:</strong> sihatiuser</p>
        <p>📅 <strong>Waktu:</strong> {time.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Progress bars
    overall_progress = st.progress(0)
    status_text = st.empty()
    detail_text = st.empty()
    
    instansi_list = []
    
    # Step 1: Extract data from each instansi (with multiple files)
    for idx, (i, instansi_data) in enumerate(uploaded_files_data.items()):
        overall_progress.progress((idx + 1) / (total_instansi + 1))
        status_text.text(f"🏢 Menganalisis {instansi_data['nama']} ({idx + 1}/{total_instansi})")
        
        # Process multiple files for this instansi
        detail_text.text(f"📄 Memproses {len(instansi_data['files'])} dokumen...")
        
        # Extract text from all files
        combined_text = doc_processor.process_multiple_files(
            instansi_data['files'], 
            instansi_data['file_names']
        )
        
        if combined_text and not combined_text.startswith("Error:"):
            detail_text.text(f"🤖 Menganalisis dengan {analyzer.model_name}...")
            
            # Analyze with Gemini
            extracted_data = analyzer.extract_instansi_data(
                combined_text, 
                instansi_data['nama'],
                instansi_data['file_names']
            )
            instansi_list.append(extracted_data)
            
            st.success(f"✅ {instansi_data['nama']}: {len(instansi_data['files'])} dokumen berhasil dianalisis")
        else:
            st.error(f"❌ Gagal mengekstrak teks dari dokumen {instansi_data['nama']}")
    
    # Step 2: Analyze overlaps
    if len(instansi_list) >= 2:
        overall_progress.progress(1.0)
        status_text.text("🔍 Menganalisis tumpang tindih antar instansi...")
        detail_text.text(f"🤖 AI sedang membandingkan semua data dengan {analyzer.model_name}...")
        
        overlap_analysis = analyzer.analyze_overlaps(instansi_list)
        
        overall_progress.empty()
        status_text.empty()
        detail_text.empty()
        
        # Display results
        display_results(instansi_list, overlap_analysis, analyzer.model_name)
    else:
        st.error("❌ Minimal 2 instansi diperlukan untuk analisis")

def display_results(instansi_list, overlap_analysis, model_name):
    """Tampilkan hasil analisis dengan info model"""
    
    st.markdown("---")
    st.header("📊 Hasil Analisis")
    
    # Analysis info
    st.markdown(f"""
    <div class="config-info">
        <h4>ℹ️ Informasi Analisis</h4>
        <p><strong>Model AI:</strong> {model_name}</p>
        <p><strong>Jumlah Instansi:</strong> {len(instansi_list)}</p>
        <p><strong>Total Dokumen:</strong> {sum(len(inst.dokumen_sumber) for inst in instansi_list)}</p>
        <p><strong>Waktu Analisis:</strong> {time.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        <p><strong>User:</strong> sihatiuser</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Ringkasan Eksekutif
    if 'ringkasan_eksekutif' in overlap_analysis:
        st.subheader("📋 Ringkasan Eksekutif")
        st.info(overlap_analysis['ringkasan_eksekutif'])
    
    # Metrik Overview
    if 'metrik_overlap' in overlap_analysis:
        st.subheader("📈 Metrik Tumpang Tindih")
        
        col1, col2, col3, col4 = st.columns(4)
        metrik = overlap_analysis['metrik_overlap']
        
        with col1:
            st.metric(
                "Total Tumpang Tindih",
                metrik.get('total_overlap_ditemukan', 0)
            )
        
        with col2:
            st.metric(
                "Overlap Tinggi",
                metrik.get('overlap_tinggi', 0),
                delta=f"-{metrik.get('overlap_tinggi', 0)} prioritas"
            )
        
        with col3:
            st.metric(
                "Overlap Sedang",
                metrik.get('overlap_sedang', 0)
            )
        
        with col4:
            st.metric(
                "Efisiensi Potensial",
                metrik.get('efisiensi_potensial', '0%')
            )
    
    # Visualisasi Tumpang Tindih
    if 'tumpang_tindih' in overlap_analysis:
        st.subheader("🔍 Detail Tumpang Tindih")
        
        overlaps = overlap_analysis['tumpang_tindih']
        
        # Chart
        if overlaps:
            df_overlap = pd.DataFrame(overlaps)
            
            # Pie chart tingkat overlap
            tingkat_counts = df_overlap['tingkat_overlap'].value_counts()
            
            fig_pie = px.pie(
                values=tingkat_counts.values,
                names=tingkat_counts.index,
                title="Distribusi Tingkat Tumpang Tindih",
                color_discrete_map={
                    'tinggi': '#f44336',
                    'sedang': '#ff9800', 
                    'rendah': '#4caf50'
                }
            )
            st.plotly_chart(fig_pie, use_container_width=True)
            
            # Detail cards with document sources
            for i, overlap in enumerate(overlaps):
                css_class = f"overlap-{overlap['tingkat_overlap']}"
                
                # Document sources if available
                doc_sources = ""
                if 'dokumen_sumber' in overlap and overlap['dokumen_sumber']:
                    doc_sources = f"<p><strong>Dokumen Sumber:</strong> {', '.join(overlap['dokumen_sumber'])}</p>"
                
                # Coordination recommendation if available
                coord_rec = ""
                if overlap.get('rekomendasi_koordinasi'):
                    coord_rec = f"<p><strong>Rekomendasi Koordinasi:</strong> {overlap['rekomendasi_koordinasi']}</p>"
                
                st.markdown(f"""
                <div class="metric-card {css_class}">
                    <h4>🔄 {overlap['kategori'].replace('_', ' ').title()}</h4>
                    <p><strong>Deskripsi:</strong> {overlap['deskripsi']}</p>
                    <p><strong>Instansi Terlibat:</strong> {', '.join(overlap['instansi_terlibat'])}</p>
                    <p><strong>Tingkat:</strong> {overlap['tingkat_overlap'].upper()}</p>
                    <p><strong>Dampak:</strong> {overlap['dampak_potensial']}</p>
                    {doc_sources}
                    {coord_rec}
                    {f"<p><strong>Estimasi Pemborosan:</strong> {overlap['estimasi_pemborosan_anggaran']}</p>" if overlap.get('estimasi_pemborosan_anggaran') else ''}
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
    
    # Rekomendasi (Enhanced untuk Indonesia)
    if 'rekomendasi' in overlap_analysis:
        st.subheader("💡 Rekomendasi Strategis")
        
        rekomendasi = overlap_analysis['rekomendasi']
        
        for i, rec in enumerate(rekomendasi):
            priority_color = {
                'tinggi': '🔴',
                'sedang': '🟡', 
                'rendah': '🟢'
            }
            
            with st.expander(f"{priority_color.get(rec['prioritas'], '⚪')} Rekomendasi {i+1} - Prioritas {rec['prioritas'].title()}"):
                st.write(f"**Aksi:** {rec['aksi']}")
                st.write(f"**Instansi Pelaksana (Lead Agency):** {rec['instansi_pelaksana']}")
                
                if rec.get('instansi_pendukung'):
                    st.write(f"**Instansi Pendukung:** {', '.join(rec['instansi_pendukung'])}")
                
                st.write(f"**Timeline:** {rec['timeline']}")
                st.write(f"**Benefit Estimasi:** {rec['benefit_estimasi']}")
                
                if rec.get('dasar_hukum'):
                    st.write(f"**Dasar Hukum:** {rec['dasar_hukum']}")
                
                if rec.get('mekanisme_koordinasi'):
                    st.write(f"**Mekanisme Koordinasi:** {rec['mekanisme_koordinasi']}")
    
    # Data Instansi (Enhanced with document sources)
    with st.expander("📋 Detail Data Instansi"):
        for instansi in instansi_list:
            st.subheader(f"🏢 {instansi.nama}")
            
            # Show document sources
            st.markdown(f"**📄 Dokumen Sumber:** {', '.join(instansi.dokumen_sumber)}")
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Tugas Pokok:**")
                for tugas in instansi.tugas_pokok:
                    st.write(f"• {tugas}")
                
                st.write("**Program:**")
                for program in instansi.program:
                    st.write(f"• {program}")
            
            with col2:
                st.write("**Fungsi:**")
                for fungsi in instansi.fungsi:
                    st.write(f"• {fungsi}")
                
                st.write("**Target Sasaran:**")  
                for target in instansi.target_sasaran:
                    st.write(f"• {target}")
            
            if instansi.anggaran:
                st.write(f"**Anggaran:** {instansi.anggaran}")
            
            st.markdown("---")
    
    # Export hasil
    st.subheader("📤 Export Hasil")
    st.info("💡 Laporan akan mencakup semua data analisis, metrik, dan rekomendasi dalam format yang rapi")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Excel Report")
        st.write("Laporan lengkap dengan multiple sheets:")
        st.write("• 📋 Ringkasan Eksekutif")
        st.write("• 🏢 Data Instansi")  
        st.write("• 🔍 Analisis Tumpang Tindih")
        st.write("• 💡 Rekomendasi")
        
        if st.button("📊 Generate Excel Report", use_container_width=True):
            with st.spinner("🔄 Membuat Excel report..."):
                create_excel_report(instansi_list, overlap_analysis)
    
    with col2:
        st.markdown("### 📄 PDF Report")
        st.write("Laporan profesional siap cetak:")
        st.write("• 🎯 Executive Summary")
        st.write("• 📊 Data Visualization")
        st.write("• 🔍 Detailed Analysis")
        st.write("• 💡 Strategic Recommendations")
        
        if st.button("📄 Generate PDF Report", use_container_width=True):
            with st.spinner("🔄 Membuat PDF report..."):
                create_pdf_report(instansi_list, overlap_analysis)
    
    # Quick stats
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📊 Total Instansi", len(instansi_list))
    
    with col2:
        total_docs = sum(len(inst.dokumen_sumber) for inst in instansi_list)
        st.metric("📄 Total Dokumen", total_docs)
    
    with col3:
        if 'metrik_overlap' in overlap_analysis:
            total_overlaps = overlap_analysis['metrik_overlap'].get('total_overlap_ditemukan', 0)
            st.metric("🔍 Total Overlaps", total_overlaps)
    
    with col4:
        st.metric("🤖 Model Used", model_name.replace('gemini-', '').replace('gemma-', '').upper())

if __name__ == "__main__":
    main()
