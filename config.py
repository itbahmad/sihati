# Konfigurasi aplikasi
import os

class Config:
    # Gemini API
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    
    # OCR Settings
    # TESSERACT_CMD = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Windows
    TESSERACT_CMD = '/usr/bin/tesseract'  # Linux
    
    # File Upload Settings
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = ['pdf']
    
    # Processing Settings
    MAX_TEXT_LENGTH = 10000  # Batasi untuk efisiensi API
    BATCH_SIZE = 5  # Jumlah dokumen per batch
    
    # Model Settings
    GEMINI_MODEL = 'gemini-2.5-pro'
    TEMPERATURE = 0.1  # Lebih deterministik
    MAX_OUTPUT_TOKENS = 4096

# Prompt templates
EXTRACTION_PROMPT_TEMPLATE = """
Analisis dokumen pemerintah Indonesia berikut dan ekstrak informasi terstruktur:

KONTEKS: Dokumen ini adalah {doc_type} dari {instansi_name}

DOKUMEN:
{document_text}

INSTRUKSI EKSTRAKSI:
1. TUGAS POKOK: Identifikasi tugas utama/misi utama instansi
2. FUNGSI: Fungsi-fungsi spesifik yang dijalankan
3. PROGRAM: Program kerja strategis 
4. KEGIATAN: Kegiatan operasional spesifik
5. TARGET SASARAN: Sasaran/target yang ingin dicapai
6. INDIKATOR: KPI atau indikator kinerja
7. ANGGARAN: Informasi alokasi anggaran

FORMAT OUTPUT JSON:
{{
    "tugas_pokok": ["tugas1", "tugas2"],
    "fungsi": ["fungsi1", "fungsi2"], 
    "program": ["program1", "program2"],
    "kegiatan": ["kegiatan1", "kegiatan2"],
    "target_sasaran": ["target1", "target2"],
    "indikator": ["indikator1", "indikator2"],
    "anggaran": "informasi anggaran"
}}

CATATAN:
- Fokus pada substansi, bukan format dokumen
- Gunakan terminologi asli dokumen
- Jika tidak ditemukan, gunakan array kosong []
"""

OVERLAP_ANALYSIS_PROMPT = """
ANALISIS TUMPANG TINDIH TUGAS ANTAR INSTANSI PEMERINTAH

DATA INSTANSI:
{instansi_data}

FRAMEWORK ANALISIS:
1. OVERLAP TUGAS: Identifikasi tugas yang sama/mirip
2. OVERLAP FUNGSI: Fungsi yang tumpang tindih
3. OVERLAP PROGRAM: Program dengan tujuan serupa
4. OVERLAP SASARAN: Target sasaran yang sama
5. KONFLIK KEWENANGAN: Potensi konflik regulasi

KRITERIA TINGKAT OVERLAP:
- TINGGI: >70% kesamaan tujuan/target/output
- SEDANG: 40-70% kesamaan 
- RENDAH: 20-40% kesamaan

OUTPUT FORMAT JSON:
{{
    "ringkasan_eksekutif": "ringkasan temuan utama max 200 kata",
    "statistik": {{
        "total_overlap": 0,
        "overlap_tinggi": 0,
        "overlap_sedang": 0, 
        "overlap_rendah": 0,
        "efisiensi_potensial_persen": 0
    }},
    "tumpang_tindih": [
        {{
            "id": "unique_id",
            "kategori": "tugas_pokok|fungsi|program|kegiatan",
            "judul": "judul singkat overlap",
            "deskripsi": "deskripsi detail",
            "instansi_terlibat": ["instansi1", "instansi2"],
            "tingkat_overlap": "tinggi|sedang|rendah",
            "similarity_score": 0.85,
            "dampak_potensial": "deskripsi dampak",
            "estimasi_pemborosan": "10-15% anggaran terkait",
            "root_cause": "akar penyebab overlap"
        }}
    ],
    "rekomendasi": [
        {{
            "prioritas": "tinggi|sedang|rendah",
            "kategori": "konsolidasi|koordinasi|eliminasi|redistribusi",
            "judul": "judul rekomendasi",
            "deskripsi": "deskripsi detail aksi",
            "instansi_lead": "instansi yang memimpin",
            "instansi_support": ["instansi pendukung"],
            "timeline": "estimasi waktu implementasi",
            "complexity": "rendah|sedang|tinggi",
            "benefit_estimasi": "manfaat kuantitatif dan kualitatif",
            "risiko": "risiko implementasi",
            "quick_wins": ["aksi cepat yang bisa dilakukan"]
        }}
    ],
    "sinergi_potensial": [
        {{
            "area": "area kolaborasi",
            "instansi": ["instansi1", "instansi2"],
            "deskripsi": "peluang sinergi",
            "benefit": "manfaat kolaborasi"
        }}
    ]
}}

FOKUS ANALISIS:
- Duplikasi yang dapat dieliminasi
- Koordinasi yang dapat diperkuat  
- Sinergi yang dapat dioptimalkan
- Redistribusi tugas yang lebih efisien
"""

# Update V4
# Daftar model yang tersedia
AVAILABLE_MODELS = {
    "gemini-2.5-pro": {
        "name": "Gemini 2.5 Pro",
        "description": "Model terbaru dengan akurasi tinggi, cocok untuk analisis kompleks",
        "cost": "Tinggi",
        "speed": "Sedang",
        "recommended": True
    },
    "gemini-2.5-flash": {
        "name": "Gemini 2.5 Flash", 
        "description": "Model cepat dengan performa baik, cocok untuk analisis standar",
        "cost": "Sedang",
        "speed": "Cepat",
        "recommended": False
    },
    "gemma-3n-e2b-it": {
        "name": "Gemma 3N E2B IT",
        "description": "Model khusus untuk teks Indonesia, optimized untuk dokumen pemerintah",
        "cost": "Rendah", 
        "speed": "Cepat",
        "recommended": False
    }
}

# Daftar Kementerian/Lembaga Indonesia (berdasarkan struktur terbaru)
KEMENTERIAN_LEMBAGA_INDONESIA = [
    # Kementerian Koordinator
    "Kementerian Koordinator Bidang Kemaritiman dan Investasi",
    "Kementerian Koordinator Bidang Perekonomian", 
    "Kementerian Koordinator Bidang Pembangunan Manusia dan Kebudayaan",
    "Kementerian Koordinator Bidang Politik, Hukum, dan Keamanan",
    
    # Kementerian
    "Kementerian Dalam Negeri",
    "Kementerian Luar Negeri",
    "Kementerian Pertahanan",
    "Kementerian Hukum dan Hak Asasi Manusia",
    "Kementerian Keuangan",
    "Kementerian Energi dan Sumber Daya Mineral",
    "Kementerian Perindustrian",
    "Kementerian Perdagangan",
    "Kementerian Pertanian",
    "Kementerian Kehutanan",
    "Kementerian Perhubungan",
    "Kementerian Kelautan dan Perikanan",
    "Kementerian Tenaga Kerja",
    "Kementerian Transmigasi",
    "Kementerian Lingkungan Hidup dan Kehutanan",
    "Kementerian Desa, Pembangunan Daerah Tertinggal dan Transmigrasi",
    "Kementerian Pekerjaan Umum dan Perumahan Rakyat",
    "Kementerian Kesehatan",
    "Kementerian Pendidikan, Kebudayaan, Riset, dan Teknologi",
    "Kementerian Agama",
    "Kementerian Sosial",
    "Kementerian Pariwisata dan Ekonomi Kreatif",
    "Kementerian Komunikasi dan Digital",
    "Kementerian Koperasi dan Usaha Kecil dan Menengah",
    "Kementerian Pemberdayaan Perempuan dan Perlindungan Anak",
    "Kementerian Pemuda dan Olahraga",
    "Kementerian Perencanaan Pembangunan Nasional/Badan Perencanaan Pembangunan Nasional",
    "Kementerian Badan Usaha Milik Negara",
    "Kementerian Pendayagunaan Aparatur Negara dan Reformasi Birokrasi",
    "Kementerian Riset dan Teknologi",
    "Kementerian Investasi/Badan Koordinasi Penanaman Modal",
    
    # Lembaga Pemerintah Non-Kementerian (LPNK)
    "Badan Intelijen Negara",
    "Badan Koordinasi Keamanan Laut",
    "Badan Koordinasi Penanaman Modal",
    "Badan Kepegawaian Negara",
    "Badan Keuangan dan Fiskal",
    "Badan Meteorologi, Klimatologi, dan Geofisika",
    "Badan Narkotika Nasional",
    "Badan Nasional Penanggulangan Bencana", 
    "Badan Nasional Penanggulangan Terorisme",
    "Badan Pengawas Obat dan Makanan",
    "Badan Pengawasan Keuangan dan Pembangunan",
    "Badan Perencanaan Pembangunan Nasional",
    "Badan Pertanahan Nasional",
    "Badan Pusat Statistik",
    "Badan Restorasi Gambut",
    "Badan Riset dan Inovasi Nasional",
    "Badan Siber dan Sandi Negara",
    "Badan Standardisasi Nasional",
    "Badan Tenaga Nuklir Nasional",
    "Lembaga Administrasi Negara",
    "Lembaga Ilmu Pengetahuan Indonesia",
    "Lembaga Kebijakan Pengadaan Barang/Jasa Pemerintah",
    "Lembaga Penerbangan dan Antariksa Nasional",
    "Lembaga Sandi Negara",
    "Perpustakaan Nasional",
    "Arsip Nasional Republik Indonesia",
    
    # Kepolisian dan TNI
    "Kepolisian Negara Republik Indonesia",
    "Tentara Nasional Indonesia",
    "TNI Angkatan Darat",
    "TNI Angkatan Laut", 
    "TNI Angkatan Udara",
    
    # Lembaga Tinggi Negara
    "Mahkamah Agung",
    "Mahkamah Konstitusi",
    "Komisi Yudisial",
    "Kejaksaan Agung",
    "Badan Pemeriksa Keuangan",
    "Komisi Pemberantasan Korupsi",
    "Komisi Nasional Hak Asasi Manusia",
    "Komisi Ombudsman Nasional",
    "Komisi Pemilihan Umum",
    "Badan Pengawas Pemilihan Umum",
    "Dewan Kehormatan Penyelenggara Pemilihan Umum",
    
    # Pemerintah Daerah (contoh)
    "Pemerintah Provinsi DKI Jakarta",
    "Pemerintah Provinsi Jawa Barat",
    "Pemerintah Provinsi Jawa Tengah",
    "Pemerintah Provinsi Jawa Timur",
    "Pemerintah Provinsi Sumatera Utara",
    "Pemerintah Provinsi Sumatera Barat",
    "Pemerintah Provinsi Sumatera Selatan",
    "Pemerintah Provinsi Kalimantan Timur",
    "Pemerintah Provinsi Kalimantan Selatan",
    "Pemerintah Provinsi Sulawesi Selatan",
    "Pemerintah Provinsi Bali",
    "Pemerintah Provinsi Papua",
    "Pemerintah Kota Jakarta Pusat",
    "Pemerintah Kota Surabaya",
    "Pemerintah Kota Bandung",
    "Pemerintah Kota Medan",
    "Pemerintah Kota Semarang",
    "Pemerintah Kota Makassar",
    "Pemerintah Kota Palembang",
    "Pemerintah Kota Denpasar"
]

# Default model
DEFAULT_MODEL = "gemini-2.5-pro"
