import re
import unicodedata
from typing import List, Dict, Any
import pandas as pd

class TextProcessor:
    @staticmethod
    def clean_text(text: str) -> str:
        """Bersihkan dan normalisasi teks"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters tapi pertahankan yang penting
        text = re.sub(r'[^\w\s\-\.\,\(\)\:]', ' ', text)
        
        # Normalize unicode
        text = unicodedata.normalize('NFKD', text)
        
        return text.strip()
    
    @staticmethod
    def extract_key_terms(text: str) -> List[str]:
        """Ekstrak term kunci dari teks"""
        # Keywords umum dokumen pemerintah
        keywords = [
            'tugas pokok', 'fungsi', 'program', 'kegiatan', 
            'sasaran', 'target', 'indikator', 'anggaran',
            'kewenangan', 'tanggung jawab', 'koordinasi'
        ]
        
        found_terms = []
        text_lower = text.lower()
        
        for keyword in keywords:
            if keyword in text_lower:
                found_terms.append(keyword)
        
        return found_terms

class OverlapCalculator:
    @staticmethod
    def calculate_text_similarity(text1: str, text2: str) -> float:
        """Hitung similarity antara dua teks"""
        from difflib import SequenceMatcher
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    @staticmethod
    def calculate_list_overlap(list1: List[str], list2: List[str]) -> Dict[str, Any]:
        """Hitung overlap antara dua list"""
        set1 = set([item.lower().strip() for item in list1])
        set2 = set([item.lower().strip() for item in list2])
        
        intersection = set1.intersection(set2)
        union = set1.union(set2)
        
        jaccard_similarity = len(intersection) / len(union) if union else 0
        overlap_items = list(intersection)
        
        return {
            'similarity_score': jaccard_similarity,
            'overlap_items': overlap_items,
            'overlap_count': len(overlap_items)
        }

class ReportGenerator:
    @staticmethod
    def generate_summary_stats(overlap_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics"""
        if 'tumpang_tindih' not in overlap_analysis:
            return {}
        
        overlaps = overlap_analysis['tumpang_tindih']
        
        stats = {
            'total_overlaps': len(overlaps),
            'high_priority': len([o for o in overlaps if o.get('tingkat_overlap') == 'tinggi']),
            'medium_priority': len([o for o in overlaps if o.get('tingkat_overlap') == 'sedang']),
            'low_priority': len([o for o in overlaps if o.get('tingkat_overlap') == 'rendah']),
        }
        
        # Calculate average similarity
        similarities = [o.get('similarity_score', 0) for o in overlaps if 'similarity_score' in o]
        stats['avg_similarity'] = sum(similarities) / len(similarities) if similarities else 0
        
        return stats
    
    @staticmethod
    def create_recommendations_df(recommendations: List[Dict]) -> pd.DataFrame:
        """Convert recommendations to DataFrame"""
        if not recommendations:
            return pd.DataFrame()
        
        df_data = []
        for rec in recommendations:
            df_data.append({
                'Prioritas': rec.get('prioritas', ''),
                'Kategori': rec.get('kategori', ''),
                'Judul': rec.get('judul', ''),
                'Deskripsi': rec.get('deskripsi', ''),
                'Timeline': rec.get('timeline', ''),
                'Complexity': rec.get('complexity', ''),
                'Benefit': rec.get('benefit_estimasi', '')
            })
        
        return pd.DataFrame(df_data)

# Validation utilities
class ValidationUtils:
    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        """Validate Gemini API key format"""
        if not api_key:
            return False
        
        # Basic format check
        if len(api_key) < 20:
            return False
            
        return True
    
    @staticmethod
    def validate_pdf_file(file) -> Dict[str, Any]:
        """Validate uploaded PDF file"""
        if file is None:
            return {'valid': False, 'error': 'No file uploaded'}
        
        if not file.name.lower().endswith('.pdf'):
            return {'valid': False, 'error': 'File harus berformat PDF'}
        
        if file.size > 50 * 1024 * 1024:  # 50MB limit
            return {'valid': False, 'error': 'File terlalu besar (max 50MB)'}
        
        return {'valid': True}

# Indonesian government terms dictionary
INDONESIAN_GOV_TERMS = {
    'abbreviations': {
        'SOTK': 'Susunan Organisasi dan Tata Kerja',
        'RENSTRA': 'Rencana Strategis',
        'RENJA': 'Rencana Kerja',
        'RKPD': 'Rencana Kerja Pemerintah Daerah',
        'DIPA': 'Daftar Isian Pelaksanaan Anggaran',
        'TUPOKSI': 'Tugas Pokok dan Fungsi',
        'SOP': 'Standard Operating Procedure'
    },
    'common_functions': [
        'perumusan kebijakan',
        'pelaksanaan kebijakan', 
        'evaluasi dan pelaporan',
        'pembinaan teknis',
        'koordinasi',
        'supervisi',
        'monitoring',
        'fasilitasi'
    ],
    'document_types': [
        'peraturan menteri',
        'keputusan menteri', 
        'instruksi presiden',
        'peraturan pemerintah',
        'undang-undang'
    ]
}