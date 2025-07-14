# web_app.py
import os
import uuid
import time
import atexit
import logging
from threading import Timer
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import base64
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI
import difflib
import re
import traceback
from datetime import datetime

# Laad environment variabelen uit .env bestand
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialiseer de Flask applicatie
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'actiz-dev-key-2024-test')  # Better security

# --- Constants ---
LOREM_INDICATORS = ['lorem ipsum', 'dolor sit amet', 'consectetur adipiscing', 'sed do eiusmod']
LOREM_THRESHOLD = 3
MAX_DIFFERENCES_DISPLAY = 50
MAX_DIFF_SUMMARY_ITEMS = 30
FILE_CLEANUP_INTERVAL = 3600  # 1 hour in seconds
FILE_MAX_AGE = 3600  # 1 hour in seconds

# --- Configuratie ---
UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'
ALLOWED_EXTENSIONS = {'pdf', 'txt', 'docx', 'doc'}  # Word documenten toegevoegd

# Maak de benodigde mappen aan als ze niet bestaan
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload

# --- File Cleanup Functions ---
def cleanup_old_files():
    """Remove files older than FILE_MAX_AGE seconds"""
    try:
        cutoff = time.time() - FILE_MAX_AGE
        files_removed = 0
        
        for folder in [UPLOAD_FOLDER, RESULTS_FOLDER]:
            if not os.path.exists(folder):
                continue
                
            for filename in os.listdir(folder):
                filepath = os.path.join(folder, filename)
                try:
                    if os.path.isfile(filepath) and os.path.getctime(filepath) < cutoff:
                        os.remove(filepath)
                        files_removed += 1
                        logger.info(f"Cleaned up old file: {filename}")
                except OSError as e:
                    logger.warning(f"Could not remove file {filename}: {e}")
        
        if files_removed > 0:
            logger.info(f"Cleanup completed: {files_removed} files removed")
            
    except Exception as e:
        logger.error(f"Error during file cleanup: {e}")

def schedule_cleanup():
    """Schedule the next cleanup"""
    cleanup_old_files()
    Timer(FILE_CLEANUP_INTERVAL, schedule_cleanup).start()

# Start cleanup scheduler
schedule_cleanup()
atexit.register(cleanup_old_files)

# --- Validation Functions ---
def validate_upload_request(request):
    """Validate upload request and return error message if invalid"""
    if 'file1' not in request.files or 'file2' not in request.files:
        return 'Beide documenten zijn vereist!'
    
    file1, file2 = request.files['file1'], request.files['file2']
    
    if file1.filename == '' or file2.filename == '':
        return 'Selecteer beide bestanden!'
    
    if not (allowed_file(file1.filename) and allowed_file(file2.filename)):
        return 'Bestandstype niet ondersteund. Gebruik PDF, TXT of Word.'
    
    # Check file sizes
    for file_obj, name in [(file1, 'file1'), (file2, 'file2')]:
        file_obj.seek(0, 2)  # Seek to end
        size = file_obj.tell()
        file_obj.seek(0)  # Reset to beginning
        
        if size > app.config['MAX_CONTENT_LENGTH']:
            return f'Bestand {file_obj.filename} is te groot (max 50MB)'
        
# AANGEPAST: Lege bestanden zijn toegestaan, maar geven een waarschuwing
        if size == 0:
            logger.warning(f'Bestand {file_obj.filename} is leeg - wordt geaccepteerd maar kan geen tekst bevatten')
    
    return None

def allowed_file(filename):
    """Controleert of het bestandstype is toegestaan."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Document Processor Class ---
# Dit is het 'brein' van de applicatie

class DocumentProcessor:
    def __init__(self):
        """Initialiseer de clients voor externe AI-diensten."""
        try:
            # Document Intelligence voor OCR
            self.doc_client = DocumentIntelligenceClient(
                endpoint=os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"),
                credential=AzureKeyCredential(os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY"))
            )
            
            # OpenAI voor analyse
            self.ai_client = AzureOpenAI(
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                api_version=os.getenv("OPENAI_API_VERSION")
            )
            self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
            logger.info("DocumentProcessor initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing DocumentProcessor: {e}")
            raise
    
    def extract_text_from_file(self, file_path):
        """Extract tekst uit PDF, TXT of Word bestand."""
        try:
            logger.info(f"Extracting text from: {os.path.basename(file_path)}")
            
            if file_path.lower().endswith('.txt'):
                with open(file_path, 'r', encoding='utf-8') as txt_file:
                    text = txt_file.read()
                    logger.info(f"Extracted {len(text)} characters from TXT file")
                    return text
            
            elif file_path.lower().endswith(('.docx', '.doc')):
                try:
                    import docx
                    doc = docx.Document(file_path)
                    text = '\n'.join([p.text for p in doc.paragraphs])
                    logger.info(f"Extracted {len(text)} characters from Word file")
                    return text
                except ImportError:
                    logger.error("Bibliotheek 'python-docx' is niet geïnstalleerd. Installeer met: pip install python-docx")
                    return None
            
            elif file_path.lower().endswith('.pdf'):
                with open(file_path, "rb") as pdf_file:
                    pdf_data = pdf_file.read()
                
                pdf_base64 = base64.b64encode(pdf_data).decode()
                
                poller = self.doc_client.begin_analyze_document(
                    "prebuilt-layout",
                    {"base64Source": pdf_base64}
                )
                
                result = poller.result()
                logger.info(f"Extracted {len(result.content)} characters from PDF file")
                return result.content
                
        except Exception as e:
            logger.error(f"Fout bij bestandsverwerking: {e}")
            return None
    
    def compare_documents(self, text1, text2):
        """Vergelijk twee documenten op paragraafniveau."""
        logger.info("Starting document comparison")
        
        # Speciale behandeling voor lege documenten
        if not text1 and not text2: return {'differences': [], 'unchanged': []}
        if not text1: return {'differences': [{'type': 'toegevoegd', 'original': None, 'modified': text2, 'inline_diff': f'<span class="diff-added">{text2}</span>', 'section_context': 'Volledig document'}], 'unchanged': []}
        if not text2: return {'differences': [{'type': 'verwijderd', 'original': text1, 'modified': None, 'inline_diff': f'<span class="diff-removed">{text1}</span>', 'section_context': 'Volledig document'}], 'unchanged': []}

        structured_diffs = []
        current_section = "Begin document"
        
        # Gebruik een robuuste methode om op paragrafen te splitsen
        paragraphs1 = [p.strip() for p in re.split(r'\n\s*\n', text1) if p.strip()]
        paragraphs2 = [p.strip() for p in re.split(r'\n\s*\n', text2) if p.strip()]

        logger.info(f"Document 1: {len(paragraphs1)} paragraphs, Document 2: {len(paragraphs2)} paragraphs")

        # Zoek onveranderde blokken voor context
        unchanged_blocks = self._find_unchanged_content(text1, text2)

        matcher = difflib.SequenceMatcher(None, paragraphs1, paragraphs2, autojunk=False)
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                continue
            
            # Update current_section based on context - NIEUWE LOGICA
            if tag != 'equal':
                # Kijk naar de context van de wijziging
                context_para = None
                if j1 < len(paragraphs2):
                    context_para = paragraphs2[j1]
                elif i1 < len(paragraphs1):
                    context_para = paragraphs1[i1]
                
                if context_para:
                    detected_section = self._detect_section_from_text(context_para)
                    if detected_section != "Begin document":
                        current_section = detected_section
            
            if tag == 'delete':
                for para in paragraphs1[i1:i2]:
                    structured_diffs.append({
                        'type': 'verwijderd', 
                        'original': para, 
                        'modified': None, 
                        'inline_diff': f'<span class="diff-removed">{para}</span>', 
                        'section_context': current_section
                    })

            elif tag == 'insert':
                for para in paragraphs2[j1:j2]:
                    structured_diffs.append({
                        'type': 'toegevoegd', 
                        'original': None, 
                        'modified': para, 
                        'inline_diff': f'<span class="diff-added">{para}</span>', 
                        'section_context': current_section
                    })

            elif tag == 'replace':
                # Voor nu behandelen we een ongelijke vervanging (bv. 1 para wordt 2) als losse verwijderingen en toevoegingen
                # Een 1-op-1 vervanging wordt geanalyseerd op nuance
                if (i2 - i1) == (j2 - j1):
                    for old_para, new_para in zip(paragraphs1[i1:i2], paragraphs2[j1:j2]):
                        changes = self._analyze_replacement_details(old_para, new_para)
                        structured_diffs.append({
                            'type': 'vervangen',
                            'original': old_para,
                            'modified': new_para,
                            'inline_diff': self.create_inline_diff(old_para, new_para),
                            'section_context': current_section,
                            'replacement_info': changes
                        })
                else: # Ongelijke vervanging
                    for para in paragraphs1[i1:i2]:
                         structured_diffs.append({'type': 'verwijderd', 'original': para, 'modified': None, 'inline_diff': f'<span class="diff-removed">{para}</span>', 'section_context': current_section})
                    for para in paragraphs2[j1:j2]:
                         structured_diffs.append({'type': 'toegevoegd', 'original': None, 'modified': para, 'inline_diff': f'<span class="diff-added">{para}</span>', 'section_context': current_section})

        logger.info(f"Found {len(structured_diffs)} differences")
        return {
            'differences': structured_diffs,
            'unchanged': unchanged_blocks
        }

    def _find_unchanged_content(self, text1, text2):
        """Vindt content die in beide documenten voorkomt (onveranderd)."""
        if not text1 or not text2:
            return []
        
        blocks1 = [b.strip() for b in re.split(r'\n\s*\n', text1) if b.strip() and len(b.strip()) > 50]
        blocks2 = set([b.strip() for b in re.split(r'\n\s*\n', text2) if b.strip() and len(b.strip()) > 50])
        
        unchanged_blocks = []
        for block1 in blocks1:
            if block1 in blocks2:
                unchanged_blocks.append({'content': block1})
        return unchanged_blocks

    def _detect_section_from_text(self, text):
        """Detecteer sectienaam uit tekst met betere herkenning."""
        if not text:
            return "Begin document"
        
        # Zoek naar genummerde secties (bijv. "3.4.", "1.2.3", "A.1")
        section_patterns = [
            r'(\d+\.?\d*\.?\d*\.?\s*[A-Za-z][^.]{0,50})',  # 3.4. Mantelzorgbeleid
            r'([A-Z]\.\d+\.?\s*[A-Za-z][^.]{0,50})',       # A.1. Sectie
            r'(Artikel\s+\d+[a-z]?\.?)',                   # Artikel 5
            r'(Hoofdstuk\s+\d+\.?)',                       # Hoofdstuk 3
            r'(Paragraaf\s+\d+\.?\d*\.?)',                 # Paragraaf 2.1
        ]
        
        # Probeer elk patroon
        for pattern in section_patterns:
            section_match = re.search(pattern, text[:150], re.IGNORECASE)
            if section_match:
                section_text = section_match.group(1).strip()
                # Beperk lengte en clean up
                if len(section_text) > 60:
                    section_text = section_text[:60] + "..."
                return section_text
        
        # Fallback: eerste zinsdeel tot eerste punt
        first_sentence = text.split('.')[0]
        if len(first_sentence) > 80:
            first_sentence = first_sentence[:80] + "..."
        
        return first_sentence.strip() if first_sentence.strip() else "Begin document"

    def _analyze_replacement_details(self, old_para, new_para):
        """Analyseert de details van een paragraafvervanging (toon, juridische status)."""
        changes = {'key_changes': [], 'tone_shift': None, 'legal_escalation': False}

        # Detecteer toonverschuiving
        if 'stimuleren we' in old_para and 'groter beroep gedaan op' in new_para:
            changes['tone_shift'] = "Van stimulerend ('stimuleren') naar meer dwingend ('groter beroep doen op')."
        
        # Detecteer juridische escalatie
        if 'mantelzorgvoucher' in old_para and 'wettelijk verplichte' in new_para:
            changes['legal_escalation'] = True
            changes['key_changes'].append("De 'mantelzorgvoucher' (financiële prikkel) is vervangen door een 'wettelijk verplichte vrijstelling' (juridische plicht).")

        return changes

    def create_inline_diff(self, original, modified):
        """Maakt een inline diff met doorgestreepte en onderstreepte tekst."""
        if not original and modified: return f'<span class="diff-added">{modified}</span>'
        if original and not modified: return f'<span class="diff-removed">{original}</span>'
        if not original and not modified: return ''

        words1 = original.split()
        words2 = modified.split()
        matcher = difflib.SequenceMatcher(None, words1, words2)
        result = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                result.append(' '.join(words1[i1:i2]))
            elif tag == 'delete':
                result.append(f'<span class="diff-removed">{" ".join(words1[i1:i2])}</span>')
            elif tag == 'insert':
                result.append(f'<span class="diff-added">{" ".join(words2[j1:j2])}</span>')
            elif tag == 'replace':
                result.append(f'<span class="diff-removed">{" ".join(words1[i1:i2])}</span> <span class="diff-added">{" ".join(words2[j1:j2])}</span>')
        return ' '.join(result)
        
    def _detect_placeholder_text(self, text):
        """Detecteert of tekst placeholder/Lorem Ipsum bevat."""
        if not text: return False
        text_lower = text.lower()
        lorem_count = sum(1 for indicator in LOREM_INDICATORS if indicator in text_lower)
        return lorem_count >= LOREM_THRESHOLD

    def ai_analyze_differences(self, structured_diffs, unchanged_info=None):
        """AI analyse van gestructureerde verschillen."""
        if not structured_diffs:
            logger.info("No differences found for AI analysis")
            return {'raw': "Geen verschillen gevonden.", 'summary': [], 'added': [], 'removed': [], 'impact': []}

        logger.info(f"Starting AI analysis of {len(structured_diffs)} differences")
        diff_summary = self._create_diff_summary(structured_diffs, unchanged_info)
        
        prompt = f"""
Analyseer deze documentwijzigingen in het Nederlands. Geef een gestructureerde analyse:

{diff_summary}

BELANGRIJK: 
- Wees VOORZICHTIG en GENUANCEERD in je conclusies.
- Gebruik woorden zoals "mogelijk", "lijkt", "suggereert".

Formatteer je antwoord EXACT als volgt:

## SAMENVATTING
- [Beschrijf de hoofdlijnen van wat er is gebeurd]

## TOEGEVOEGD
- [ALLEEN echt nieuwe content]

## VERWIJDERD
- [Content die is verdwenen]

## VERVANGEN
- [Paragrafen die zijn vervangen, inclusief de gedetecteerde toon- en juridische analyse]

## IMPACT
- [Mogelijke impact - gebruik "zou kunnen", "mogelijk"]
"""
        try:
            response = self.ai_client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": "Je bent een voorzichtige en genuanceerde beleidsanalist voor de zorgsector. Gebruik ALTIJD genuanceerde taal (mogelijk, lijkt, suggereert). Analyseer de input en geef een gestructureerd antwoord terug in het gevraagde format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1500
            )
            logger.info("AI analysis completed successfully")
            return self._parse_ai_response(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"AI analyse mislukt: {e}")
            return {'raw': f"AI analyse mislukt: {e}", 'summary': [], 'added': [], 'removed': [], 'impact': []}

    def _create_diff_summary(self, structured_diffs, unchanged_info=None):
        """Maakt een leesbare samenvatting van verschillen voor de AI."""
        summary = []
        if unchanged_info:
            summary.append(f"INFO: Er zijn {len(unchanged_info)} tekstblokken ONVERANDERD gebleven.")
        
        for diff in structured_diffs[:MAX_DIFF_SUMMARY_ITEMS]:  # Limiteer voor token-limiet
            if diff['type'] == 'verwijderd':
                summary.append(f"VERWIJDERD: {diff['original']}")
            elif diff['type'] == 'toegevoegd':
                summary.append(f"TOEGEVOEGD: {diff['modified']}")
            elif diff['type'] == 'vervangen':
                replacement_info = diff.get('replacement_info', {})
                summary.append(f"VERVANGEN:\nOUD: {diff['original']}\nNIEUW: {diff['modified']}")
                if replacement_info.get('tone_shift'):
                    summary.append(f"  - Analyse Toonverschuiving: {replacement_info['tone_shift']}")
                if replacement_info.get('legal_escalation'):
                    summary.append(f"  - Analyse Juridische Status: Van vrijwillige prikkel naar wettelijke plicht.")
            elif diff['type'] == 'verplaatst':
                summary.append(f"VERPLAATST: Een blok tekst is verplaatst.")
        return '\n'.join(summary)

    def _parse_ai_response(self, response_text):
        """Parset de AI response in gestructureerde secties."""
        sections = {'raw': response_text, 'summary': [], 'added': [], 'removed': [], 'impact': [], 'unchanged': [], 'replaced': []}
        current_section = None
        for line in response_text.split('\n'):
            line = line.strip()
            if '## SAMENVATTING' in line: current_section = 'summary'
            elif '## TOEGEVOEGD' in line: current_section = 'added'
            elif '## VERWIJDERD' in line: current_section = 'removed'
            elif '## VERVANGEN' in line: current_section = 'replaced'
            elif '## IMPACT' in line: current_section = 'impact'
            elif '## ONVERANDERD' in line: current_section = 'unchanged'
            elif line.startswith('- ') and current_section:
                sections[current_section].append(line[2:])
        return sections

    def analyze_by_mode(self, mode, doc1, doc2=None, doc3=None):
        """Router functie voor verschillende analyse modes."""
        logger.info(f"Starting analysis for mode: {mode}")
        
        if mode == 'version_comparison':
            return self.compare_versions(doc1, doc2)
        elif mode == 'actiz_position':
            return self.analyze_actiz_position(doc1, doc2)
        elif mode == 'external_reaction':
            return self.analyze_external_reaction(doc1, doc2)
        elif mode == 'strategic_communication':
            return self.strategic_communication_advice(doc1, doc2, doc3)
        else:
            logger.error(f"Unknown mode: {mode}")
            return {'error': f'Onbekende analyse mode: {mode}'}

    def compare_versions(self, doc1, doc2):
        """Vergelijkt 2 beleidsversies (uitgebreide versie van bestaande functie)."""
        logger.info("Starting version comparison analysis")
        
        # Gebruik bestaande compare_documents functie
        basic_comparison = self.compare_documents(doc1, doc2)
        
        # Voeg version-specifieke AI analyse toe
        ai_prompt = f"""
        Analyseer deze beleidswijzigingen tussen twee versies van hetzelfde document.
        
        Focus op:
        - Belangrijkste wijzigingen en hun impact
        - Verschuivingen in beleidstoon (zachter/harder)
        - Nieuwe verplichtingen of rechten
        - Implementatie-consequenties voor zorgaanbieders
        - Financiële gevolgen
        
        {self._create_diff_summary(basic_comparison['differences'])}
        
        Geef een analyse in het Nederlands met:
        ## BELANGRIJKSTE WIJZIGINGEN
        ## BELEIDSTOON VERSCHUIVINGEN  
        ## IMPLEMENTATIE IMPACT
        ## FINANCIËLE GEVOLGEN
        """
        
        try:
            ai_response = self.ai_client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": "Je bent een expert beleidsanalist voor de zorgsector. Analyseer documentwijzigingen met focus op praktische gevolgen voor zorgaanbieders."},
                    {"role": "user", "content": ai_prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            version_analysis = self._parse_ai_response(ai_response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"AI analysis failed for version comparison: {e}")
            version_analysis = {'raw': f"AI analyse mislukt: {e}", 'summary': [], 'impact': []}
        
        return {
            'type': 'version_comparison',
            'basic_comparison': basic_comparison,
            'version_analysis': version_analysis,
            'stats': {
                'differences_count': len(basic_comparison['differences']),
                'unchanged_blocks': len(basic_comparison.get('unchanged', []))
            }
        }

    def analyze_actiz_position(self, policy_doc, actiz_vision):
        """Analyseert afstemming tussen beleidsdocument en ActiZ visie."""
        logger.info("Starting ActiZ position analysis")
        
        # Basis vergelijking
        basic_comparison = self.compare_documents(policy_doc, actiz_vision)
        
        # ActiZ-specifieke AI analyse
        ai_prompt = f"""
        Analyseer hoe dit beleidsdocument aansluit bij de ActiZ visie en standpunten.
        
        Focus op:
        - Punten van overeenstemming tussen beleid en ActiZ visie
        - Conflicten of tegenstellingen
        - Kansen voor ActiZ om invloed uit te oefenen
        - Risico's voor de sector als dit beleid wordt geïmplementeerd
        - Aanbevelingen voor ActiZ positionering
        
        BELEIDSDOCUMENT:
        {policy_doc[:3000]}...
        
        ACTIZ VISIE:
        {actiz_vision[:3000]}...
        
        Geef een analyse in het Nederlands met:
        ## OVEREENSTEMMING
        ## CONFLICTPUNTEN
        ## KANSEN VOOR ACTIZ
        ## RISICO'S VOOR DE SECTOR
        ## POSITIONERING ADVIES
        """
        
        try:
            ai_response = self.ai_client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": "Je bent een strategisch adviseur voor ActiZ. Analyseer beleidsafstemming met focus op belangenbehartiging voor zorgaanbieders."},
                    {"role": "user", "content": ai_prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            position_analysis = self._parse_ai_response(ai_response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"AI analysis failed for ActiZ position: {e}")
            position_analysis = {'raw': f"AI analyse mislukt: {e}", 'summary': [], 'impact': []}
        
        return {
            'type': 'actiz_position',
            'basic_comparison': basic_comparison,
            'position_analysis': position_analysis,
            'alignment_score': self._calculate_alignment_score(policy_doc, actiz_vision),
            'stats': {
                'policy_chars': len(policy_doc),
                'vision_chars': len(actiz_vision),
                'differences_count': len(basic_comparison['differences'])
            }
        }

    def analyze_external_reaction(self, policy_doc, external_reaction):
        """Analyseert externe reacties op beleidsdocumenten."""
        logger.info("Starting external reaction analysis")
        
        # Basis vergelijking
        basic_comparison = self.compare_documents(policy_doc, external_reaction)
        
        # Externe reactie AI analyse
        ai_prompt = f"""
        Analyseer deze externe reactie op het beleidsdocument.
        
        Focus op:
        - Hoofdpunten van kritiek of steun
        - Alternatieve voorstellen van externe partij
        - Impact op ActiZ belangen en leden
        - Strategische gevolgen voor ActiZ positionering
        - Mogelijkheden voor samenwerking of tegenreactie
        
        BELEIDSDOCUMENT:
        {policy_doc[:3000]}...
        
        EXTERNE REACTIE:
        {external_reaction[:3000]}...
        
        Geef een analyse in het Nederlands met:
        ## HOOFDPUNTEN EXTERNE PARTIJ
        ## IMPACT OP ACTIZ BELANGEN
        ## STRATEGISCHE GEVOLGEN
        ## AANBEVELINGEN VOOR ACTIZ
        """
        
        try:
            ai_response = self.ai_client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": "Je bent een stakeholder analist voor ActiZ. Analyseer externe reacties met focus op strategische gevolgen voor zorgaanbieders."},
                    {"role": "user", "content": ai_prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            external_analysis = self._parse_ai_response(ai_response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"AI analysis failed for external reaction: {e}")
            external_analysis = {'raw': f"AI analyse mislukt: {e}", 'summary': [], 'impact': []}
        
        return {
            'type': 'external_reaction',
            'basic_comparison': basic_comparison,
            'external_analysis': external_analysis,
            'stakeholder_impact': self._analyze_stakeholder_impact(policy_doc, external_reaction),
            'stats': {
                'policy_chars': len(policy_doc),
                'reaction_chars': len(external_reaction),
                'differences_count': len(basic_comparison['differences'])
            }
        }

    def strategic_communication_advice(self, doc1, doc2, vision_doc):
        """Geeft strategisch communicatie-advies op basis van alle 3 documenten."""
        logger.info("Starting strategic communication analysis")
        
        # Analyseer versieverschillen
        version_changes = self.compare_documents(doc1, doc2)
        
        # Analyseer afstemming nieuwste versie met visie
        alignment = self.compare_documents(doc2, vision_doc)
        
        # Strategische communicatie AI analyse
        ai_prompt = f"""
        Geef strategisch communicatie-advies voor ActiZ op basis van deze beleidswijzigingen en onze visie.
        
        CONTEXT:
        - Document is gewijzigd van versie 1 naar versie 2
        - ActiZ heeft een eigen visie/standpunt hierover
        - ActiZ moet bepalen hoe te reageren en communiceren
        
        VERSIEWIJZIGINGEN:
        {self._create_diff_summary(version_changes['differences'])}
        
        AFSTEMMING MET ACTIZ VISIE:
        {self._create_diff_summary(alignment['differences'])}
        
        Geef communicatie-advies in het Nederlands met:
        ## KERNBOODSCHAPPEN
        ## DOELGROEP STRATEGIE
        ## RISICO COMMUNICATIE
        ## TIMING ADVIES
        ## PRAKTISCHE ACTIES
        """
        
        try:
            ai_response = self.ai_client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": "Je bent een strategisch communicatie-adviseur voor ActiZ. Geef praktische communicatie-adviezen voor belangenbehartiging."},
                    {"role": "user", "content": ai_prompt}
                ],
                temperature=0.1,
                max_tokens=2500
            )
            
            communication_analysis = self._parse_ai_response(ai_response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"AI analysis failed for strategic communication: {e}")
            communication_analysis = {'raw': f"AI analyse mislukt: {e}", 'summary': [], 'impact': []}
        
        return {
            'type': 'strategic_communication',
            'version_changes': version_changes,
            'vision_alignment': alignment,
            'communication_analysis': communication_analysis,
            'key_messages': self._extract_key_messages(version_changes, alignment),
            'stats': {
                'version_differences': len(version_changes['differences']),
                'alignment_differences': len(alignment['differences']),
                'total_docs_analyzed': 3
            }
        }

    def _calculate_alignment_score(self, policy_doc, vision_doc):
        """Berekent een simpele alignment score tussen twee documenten."""
        if not policy_doc or not vision_doc:
            return 0
        
        # Simpele overlap berekening op basis van gemeenschappelijke woorden
        policy_words = set(policy_doc.lower().split())
        vision_words = set(vision_doc.lower().split())
        
        intersection = policy_words.intersection(vision_words)
        union = policy_words.union(vision_words)
        
        if len(union) == 0:
            return 0
        
        return round((len(intersection) / len(union)) * 100, 1)

    def _analyze_stakeholder_impact(self, policy_doc, external_reaction):
        """Analyseert impact op verschillende stakeholders."""
        # Simpele keyword-based analyse
        stakeholders = {
            'zorgaanbieders': ['zorgaanbieder', 'zorginstelling', 'thuiszorg', 'verpleeghu'],
            'gemeenten': ['gemeente', 'lokaal', 'decentraal'],
            'cliënten': ['cliënt', 'patiënt', 'zorgvrager'],
            'verzekeraars': ['verzekeraar', 'zorgverzekeraar']
        }
        
        impact = {}
        combined_text = (policy_doc + ' ' + external_reaction).lower()
        
        for stakeholder, keywords in stakeholders.items():
            mentions = sum(combined_text.count(keyword) for keyword in keywords)
            impact[stakeholder] = mentions
        
        return impact

    def _extract_key_messages(self, version_changes, alignment):
        """Extraheert kernboodschappen uit analyses."""
        messages = []
        
        # Gebaseerd op aantal verschillen
        if len(version_changes['differences']) > 5:
            messages.append("Significante wijzigingen in het beleid")
        elif len(version_changes['differences']) > 0:
            messages.append("Gerichte aanpassingen in het beleid")
        else:
            messages.append("Minimale wijzigingen in het beleid")
        
        # Gebaseerd op alignment
        if len(alignment['differences']) > 10:
            messages.append("Aanzienlijke verschillen met ActiZ visie")
        elif len(alignment['differences']) > 5:
            messages.append("Enkele verschillen met ActiZ visie")
        else:
            messages.append("Goede afstemming met ActiZ visie")
        
        return messages

def analyze_by_mode(self, mode, doc1, doc2=None, doc3=None):
        """Router functie voor verschillende analyse modes."""
        logger.info(f"Starting analysis for mode: {mode}")
        
        if mode == 'version_comparison':
            return self.compare_versions(doc1, doc2)
        elif mode == 'actiz_position':
            return self.analyze_actiz_position(doc1, doc2)
        elif mode == 'external_reaction':
            return self.analyze_external_reaction(doc1, doc2)
        elif mode == 'strategic_communication':
            return self.strategic_communication_advice(doc1, doc2, doc3)
        else:
            logger.error(f"Unknown mode: {mode}")
            return {'error': f'Onbekende analyse mode: {mode}'}

  

# --- Flask Routes ---
# Dit deel beheert de webpaginas

processor = DocumentProcessor()

@app.route('/test-direct')
def test_direct():
    """Direct HTML test zonder templates"""
    return """
    <h1>Direct HTML Test</h1>
    <p>Als je dit ziet, werkt Flask!</p>
    <p>Het probleem zit in de templates.</p>
    """

@app.route('/docs')
def documentation():
    """Toont de technische documentatie."""
    logger.info("Documentation page accessed")
    return send_file('docs/index.html')

@app.route('/debug')
def debug():
    """Debug route om te testen of Flask werkt."""
    return "<h1>Flask Debug Test</h1><p>Als je dit ziet, werkt Flask!</p>"

@app.route('/')
def index():
    """Toont de hoofdpagina."""
    logger.info("Index page accessed")
    try:
        result = render_template('index.html')
        logger.info(f"Template rendered successfully, length: {len(result)}")
        return result
    except Exception as e:
        logger.error(f"Error rendering index.html: {e}")
        return f"<h1>Template Error</h1><p>{e}</p><pre>{traceback.format_exc()}</pre>"

@app.route('/upload', methods=['POST'])
def upload_files():
    """Verwerkt het uploaden van de bestanden."""
    logger.info("File upload started")
    
    # Validate the request
    error = validate_upload_request(request)
    if error:
        logger.warning(f"Upload validation failed: {error}")
        flash(error, 'error')
        return redirect(url_for('index'))
    
    file1 = request.files['file1']
    file2 = request.files['file2']
    
    try:
        comparison_id = str(uuid.uuid4())
        filename1 = secure_filename(f"{comparison_id}_doc1_{file1.filename}")
        filename2 = secure_filename(f"{comparison_id}_doc2_{file2.filename}")
        
        filepath1 = os.path.join(app.config['UPLOAD_FOLDER'], filename1)
        filepath2 = os.path.join(app.config['UPLOAD_FOLDER'], filename2)
        
        file1.save(filepath1)
        file2.save(filepath2)
        
        logger.info(f"Files uploaded successfully: {filename1}, {filename2}")
        flash('Documenten geüpload! Analyse gestart...', 'info')
        return redirect(url_for('process_documents', comparison_id=comparison_id))
        
    except Exception as e:
        logger.error(f'Upload fout: {e}')
        flash(f'Upload fout: {e}', 'error')
        return redirect(url_for('index'))

@app.route('/process/<comparison_id>')
def process_documents(comparison_id):
    """Verwerkt de documenten en toont de resultaten."""
    logger.info(f"Starting document processing for comparison_id: {comparison_id}")
    
    try:
        doc1_file, doc2_file = None, None
        for filename in os.listdir(UPLOAD_FOLDER):
            if filename.startswith(f"{comparison_id}_doc1_"):
                doc1_file = os.path.join(UPLOAD_FOLDER, filename)
            elif filename.startswith(f"{comparison_id}_doc2_"):
                doc2_file = os.path.join(UPLOAD_FOLDER, filename)
        
        if not doc1_file or not doc2_file:
            logger.error(f'Documenten niet gevonden voor comparison_id: {comparison_id}')
            flash('Documenten niet gevonden voor verwerking!', 'error')
            return redirect(url_for('index'))
        
        text1 = processor.extract_text_from_file(doc1_file) or ""
        text2 = processor.extract_text_from_file(doc2_file) or ""
        
        # NIEUWE CONTROLE VOOR LEGE BESTANDEN
        if text1 is None:
            text1 = ""
            logger.warning(f"Could not extract text from {doc1_file}, treating as empty")
        if text2 is None:
            text2 = ""
            logger.warning(f"Could not extract text from {doc2_file}, treating as empty")
        
        if not text1 and not text2:
            logger.warning("Both documents are empty or could not be read")
            flash('Beide documenten zijn leeg of konden niet worden gelezen.', 'warning')
            # Maak een lege results structuur voor de template
            results = {
                'comparison_id': comparison_id,
                'differences_count': 0,
                'ai_analysis': {'raw': "Beide documenten zijn leeg.", 'summary': ['Beide documenten bevatten geen tekst.'], 'added': [], 'removed': [], 'impact': []},
                'structured_differences': [],
                'filenames': {'doc1': os.path.basename(doc1_file), 'doc2': os.path.basename(doc2_file)},
                'stats': {
                    'differences_count': 0,
                    'doc1_chars_k': "0.0k",
                    'doc2_chars_k': "0.0k", 
                    'change_intensity': "0.0%"
                },
                'lorem_ipsum_detected': False
            }
            return render_template('results.html', results=results)
        
        comparison_result = processor.compare_documents(text1, text2)
        structured_differences = comparison_result['differences']
        unchanged_info = comparison_result.get('unchanged', [])
        
        ai_analysis = processor.ai_analyze_differences(structured_differences, unchanged_info)
        
        # Bereken statistieken - VERBETERDE VERSIE
        doc1_chars = len(text1) if text1 else 0
        doc2_chars = len(text2) if text2 else 0
        
        # Veilige berekening van changed_chars
        changed_chars = 0
        if structured_differences:
            for d in structured_differences:
                if d['type'] != 'verplaatst':
                    original_len = len(d.get('original', '')) if d.get('original') else 0
                    modified_len = len(d.get('modified', '')) if d.get('modified') else 0
                    changed_chars += original_len + modified_len
        
        total_chars = doc1_chars + doc2_chars
        change_intensity = (changed_chars / total_chars * 100) if total_chars > 0 else 0

        # Fix voor structured_differences - zorg dat alle velden bestaan
        for diff in structured_differences:
            if 'type' not in diff or not diff['type']:
                diff['type'] = 'vervangen'  # fallback
            if 'section_context' not in diff or not diff['section_context']:
                diff['section_context'] = 'Begin document'  # fallback

        # DEBUG: Print wat er naar de template wordt gestuurd
        print(f"=== DEBUG TEMPLATE DATA ===")
        print(f"differences_count: {len(structured_differences)}")
        print(f"structured_differences length: {len(structured_differences)}")

        if structured_differences:
            first_diff = structured_differences[0]
            print(f"First difference data:")
            for key, value in first_diff.items():
                print(f"  {key}: {repr(value)}")
        print(f"=== END DEBUG ===")

        results = {
            'comparison_id': comparison_id,
            'differences_count': len(structured_differences),
            'ai_analysis': ai_analysis,
            'structured_differences': structured_differences[:MAX_DIFFERENCES_DISPLAY],
            'filenames': {'doc1': os.path.basename(doc1_file), 'doc2': os.path.basename(doc2_file)},
            'stats': {
                'differences_count': len(structured_differences),  # Ook hier voor template
                'doc1_chars_k': f"{doc1_chars/1000:.1f}k",
                'doc2_chars_k': f"{doc2_chars/1000:.1f}k", 
                'change_intensity': f"{min(change_intensity, 100):.1f}%"
            },
            'lorem_ipsum_detected': processor._detect_placeholder_text(text1) or processor._detect_placeholder_text(text2)
        }
        
        logger.info(f"Document processing completed successfully for {comparison_id}")
        return render_template('results.html', results=results)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error in process_documents: {e}\n{error_details}")
        flash(f'Verwerkingsfout: {e}', 'error')
        return redirect(url_for('index'))

@app.route('/download_report/<comparison_id>')
def download_report(comparison_id):
    """Genereert en downloadt een PDF rapport (vereist 'pip install reportlab')."""
    logger.info(f"Report download requested for comparison_id: {comparison_id}")
    
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        import io

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = [Paragraph("ActiZ Document Vergelijking Rapport", styles['h1'])]
        # Hier kan meer logica worden toegevoegd om het rapport te vullen
        doc.build(story)
        buffer.seek(0)
        
        logger.info(f"PDF report generated successfully for {comparison_id}")
        return send_file(buffer, as_attachment=True, download_name=f'actiz_vergelijking_{comparison_id[:8]}.pdf', mimetype='application/pdf')
        
    except ImportError:
        logger.error("PDF generation failed: reportlab not installed")
        flash('PDF generatie vereist "reportlab". Installeer met: pip install reportlab', 'error')
        return redirect(url_for('process_documents', comparison_id=comparison_id))
    except Exception as e:
        logger.error(f'PDF generatie mislukt: {e}')
        flash(f'PDF generatie mislukt: {e}', 'error')
        return redirect(url_for('process_documents', comparison_id=comparison_id))

@app.route('/analyze-multiple')
def analyze_multiple():
    """Nieuwe hoofdpagina voor multi-document analyse."""
    logger.info("Multiple document analysis page accessed")
    return render_template('analyze_multiple.html')

@app.route('/upload-multiple', methods=['POST'])
def upload_multiple():
    """Verwerkt uploads voor multi-document analyse."""
    logger.info("Multiple document upload started")
    
    mode = request.form.get('mode')
    if not mode:
        flash('Selecteer een analyse type!', 'error')
        return redirect(url_for('analyze_multiple'))
    
    # Valideer bestanden per mode
    error = validate_multiple_upload_request(request, mode)
    if error:
        logger.warning(f"Multiple upload validation failed: {error}")
        flash(error, 'error')
        return redirect(url_for('analyze_multiple'))
    
    try:
        comparison_id = str(uuid.uuid4())
        uploaded_files = {}
        
        # Upload bestanden gebaseerd op mode
        if mode == 'version_comparison':
            files_to_upload = [('doc1', request.files['doc1']), ('doc2', request.files['doc2'])]
        elif mode in ['actiz_position', 'external_reaction']:
            files_to_upload = [('doc1', request.files['doc1']), ('doc2', request.files['doc2'])]
        elif mode == 'strategic_communication':
            files_to_upload = [('doc1', request.files['doc1']), ('doc2', request.files['doc2']), ('doc3', request.files['doc3'])]
        
        for doc_key, file_obj in files_to_upload:
            if file_obj and file_obj.filename:
                filename = secure_filename(f"{comparison_id}_{doc_key}_{file_obj.filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file_obj.save(filepath)
                uploaded_files[doc_key] = filepath
                logger.info(f"Uploaded {doc_key}: {filename}")
        
        # Sla mode op voor processing
        mode_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{comparison_id}_mode.txt")
        with open(mode_file, 'w') as f:
            f.write(mode)
        
        logger.info(f"Multiple files uploaded successfully for mode: {mode}")
        flash(f'Documenten geüpload! {get_mode_display_name(mode)} analyse gestart...', 'info')
        return redirect(url_for('process_multiple', comparison_id=comparison_id))
        
    except Exception as e:
        logger.error(f'Multiple upload fout: {e}')
        flash(f'Upload fout: {e}', 'error')
        return redirect(url_for('analyze_multiple'))

@app.route('/process-multiple/<comparison_id>')
def process_multiple(comparison_id):
    """Verwerkt documenten voor multi-document analyse."""
    logger.info(f"Starting multiple document processing for comparison_id: {comparison_id}")
    
    try:
        # Lees mode
        mode_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{comparison_id}_mode.txt")
        if not os.path.exists(mode_file):
            flash('Analyse mode niet gevonden!', 'error')
            return redirect(url_for('analyze_multiple'))
        
        with open(mode_file, 'r') as f:
            mode = f.read().strip()
        
        # Zoek geüploade bestanden
        uploaded_files = {}
        for filename in os.listdir(UPLOAD_FOLDER):
            if filename.startswith(f"{comparison_id}_doc"):
                if "_doc1_" in filename:
                    uploaded_files['doc1'] = os.path.join(UPLOAD_FOLDER, filename)
                elif "_doc2_" in filename:
                    uploaded_files['doc2'] = os.path.join(UPLOAD_FOLDER, filename)
                elif "_doc3_" in filename:
                    uploaded_files['doc3'] = os.path.join(UPLOAD_FOLDER, filename)
        
        # Valideer vereiste bestanden per mode
        required_docs = get_required_docs_for_mode(mode)
        for doc_key in required_docs:
            if doc_key not in uploaded_files:
                flash(f'Vereist document ontbreekt: {doc_key}', 'error')
                return redirect(url_for('analyze_multiple'))
        
        # Extract tekst uit bestanden
        texts = {}
        filenames = {}
        for doc_key, filepath in uploaded_files.items():
            text = processor.extract_text_from_file(filepath)
            if text is None:
                text = ""
                logger.warning(f"Could not extract text from {filepath}, treating as empty")
            texts[doc_key] = text
            filenames[doc_key] = os.path.basename(filepath)
        
        # Voer mode-specifieke analyse uit
        analysis_result = processor.analyze_by_mode(
            mode=mode,
            doc1=texts.get('doc1', ''),
            doc2=texts.get('doc2', ''),
            doc3=texts.get('doc3', '')
        )
        
        # Bereken statistieken
        total_chars = sum(len(text) for text in texts.values() if text)
        
        results = {
            'comparison_id': comparison_id,
            'mode': mode,
            'mode_display_name': get_mode_display_name(mode),
            'analysis_result': analysis_result,
            'filenames': filenames,
            'stats': {
                'total_docs': len(texts),
                'total_chars_k': f"{total_chars/1000:.1f}k",
                'mode_specific_stats': analysis_result.get('stats', {})
            }
        }
        
        logger.info(f"Multiple document processing completed successfully for {comparison_id}")
        return render_template('results_multiple.html', results=results)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error in process_multiple: {e}\n{error_details}")
        flash(f'Verwerkingsfout: {e}', 'error')
        return redirect(url_for('analyze_multiple'))

# Helper functies
    def validate_multiple_upload_request(request, mode):
    """Valideer upload request voor multi-document analyse."""
    required_docs = get_required_docs_for_mode(mode)
    
    for doc_key in required_docs:
        if doc_key not in request.files:
            return f'Document {doc_key} is vereist voor {get_mode_display_name(mode)}!'
        
        file_obj = request.files[doc_key]
        if file_obj.filename == '':
            return f'Selecteer een bestand voor {doc_key}!'
        
        if not allowed_file(file_obj.filename):
            return f'Bestandstype van {doc_key} niet ondersteund. Gebruik PDF, TXT of Word.'
        
        # Check file size
        file_obj.seek(0, 2)
        size = file_obj.tell()
        file_obj.seek(0)
        
        if size > app.config['MAX_CONTENT_LENGTH']:
            return f'Bestand {file_obj.filename} is te groot (max 50MB)'
        
        if size == 0:
            logger.warning(f'Bestand {file_obj.filename} is leeg')
    
    return None

    def get_required_docs_for_mode(mode):
    """Geef vereiste documenten per mode."""
    mode_requirements = {
        'version_comparison': ['doc1', 'doc2'],
        'actiz_position': ['doc1', 'doc2'],
        'external_reaction': ['doc1', 'doc2'],
        'strategic_communication': ['doc1', 'doc2', 'doc3']
    }
    return mode_requirements.get(mode, [])

    def get_mode_display_name(mode):
    """Geef leesbare naam voor mode."""
    display_names = {
        'version_comparison': 'Versie Vergelijking',
        'actiz_position': 'ActiZ Positie Check',
        'external_reaction': 'Externe Reactie Analyse',
        'strategic_communication': 'Strategische Communicatie'
    }
    return display_names.get(mode, mode)

if __name__ == '__main__':
    logger.info("Starting Flask application")
    app.run(debug=False, port=5000, host='127.0.0.1')