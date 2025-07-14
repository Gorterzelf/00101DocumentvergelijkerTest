# document_processor.py - Updated for multi-mode analysis with Azure OpenAI support
import os
import logging
import difflib
import re
from typing import Dict, List, Optional, Union, Any
from dotenv import load_dotenv

# PDF/DOCX processing
try:
    import PyPDF2
    from docx import Document
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    logging.warning("PDF/DOCX support not available. Install PyPDF2 and python-docx for full functionality.")

# Load environment
load_dotenv()

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Enhanced document processor with multi-mode analysis capabilities and Azure OpenAI support."""
    
    def __init__(self):
        self.openai_client = None
        self.is_azure = False
        self._initialize_openai()
    
    def _initialize_openai(self):
        """Initialize OpenAI client for both regular OpenAI and Azure OpenAI."""
        # Try Azure OpenAI first
        azure_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        azure_api_key = os.getenv('AZURE_OPENAI_API_KEY') 
        azure_api_version = os.getenv('OPENAI_API_VERSION', '2024-02-15-preview')
        
        if azure_endpoint and azure_api_key:
            try:
                from openai import AzureOpenAI
                self.openai_client = AzureOpenAI(
                    api_key=azure_api_key,
                    api_version=azure_api_version,
                    azure_endpoint=azure_endpoint
                )
                self.is_azure = True
                logger.info(f"Azure OpenAI client initialized successfully - Endpoint: {azure_endpoint}")
                return
            except Exception as e:
                logger.error(f"Failed to initialize Azure OpenAI: {e}")
        
        # Fallback to regular OpenAI
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=api_key)
                self.is_azure = False
                logger.info("OpenAI client initialized successfully")
                return
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI: {e}")
        
        logger.warning("No OpenAI API key found. AI analysis will be disabled.")
        self.openai_client = None
        self.is_azure = False
    
    def extract_text_from_file(self, filepath: str) -> Optional[str]:
        """Extract text from uploaded file based on extension."""
        try:
            if not os.path.exists(filepath):
                logger.error(f"File not found: {filepath}")
                return None
            
            file_ext = os.path.splitext(filepath)[1].lower()
            
            if file_ext == '.txt':
                return self._extract_from_txt(filepath)
            elif file_ext == '.pdf' and PDF_SUPPORT:
                return self._extract_from_pdf(filepath)
            elif file_ext == '.docx' and PDF_SUPPORT:
                return self._extract_from_docx(filepath)
            else:
                logger.error(f"Unsupported file type: {file_ext}")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting text from {filepath}: {e}")
            return None
    
    def _extract_from_txt(self, filepath: str) -> str:
        """Extract text from TXT file."""
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    
    def _extract_from_pdf(self, filepath: str) -> str:
        """Extract text from PDF file."""
        text = ""
        try:
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            logger.error(f"PDF extraction error: {e}")
        return text
    
    def _extract_from_docx(self, filepath: str) -> str:
        """Extract text from DOCX file."""
        try:
            doc = Document(filepath)
            return "\n".join([paragraph.text for paragraph in doc.paragraphs])
        except Exception as e:
            logger.error(f"DOCX extraction error: {e}")
            return ""
    
    def analyze_by_mode(self, mode: str, doc1: str, doc2: str, doc3: str = "") -> Dict[str, Any]:
        """Perform analysis based on the selected mode."""
        try:
            if mode == 'version_comparison':
                return self.analyze_version_comparison(doc1, doc2)
            elif mode == 'actiz_position':
                return self.analyze_actiz_position(doc1, doc2)
            elif mode == 'external_reaction':
                return self.analyze_external_reaction(doc1, doc2)
            elif mode == 'strategic_communication':
                return self.analyze_strategic_communication(doc1, doc2, doc3)
            else:
                logger.error(f"Unknown analysis mode: {mode}")
                return {
                    'error': f'Onbekende analyse mode: {mode}',
                    'basic_comparison': None,
                    'ai_analysis': None
                }
        except Exception as e:
            logger.error(f"Analysis error in mode {mode}: {e}")
            return {
                'error': f'Analyse fout: {e}',
                'basic_comparison': None,
                'ai_analysis': None
            }
    
    def analyze_version_comparison(self, doc1: str, doc2: str) -> Dict[str, Any]:
        """Analyze two versions of the same document."""
        logger.info("Starting version comparison analysis")
        
        # Basic comparison (same as original)
        basic_comparison = self.compare_documents_basic(doc1, doc2)
        
        # AI analysis
        ai_analysis = None
        if self.openai_client and basic_comparison and basic_comparison.get('differences'):
            ai_analysis = self._analyze_version_changes_with_ai(doc1, doc2, basic_comparison['differences'])
        
        return {
            'basic_comparison': basic_comparison,
            'ai_analysis': ai_analysis,
            'stats': {
                'doc1_length': len(doc1),
                'doc2_length': len(doc2),
                'differences_count': len(basic_comparison.get('differences', [])) if basic_comparison else 0
            }
        }
    
    def analyze_actiz_position(self, external_doc: str, actiz_doc: str) -> Dict[str, Any]:
        """Analyze external document against ActiZ position."""
        logger.info("Starting ActiZ position analysis")
        
        # Basic comparison - ALWAYS run this
        basic_comparison = self.compare_documents_basic(external_doc, actiz_doc)
        
        # AI analysis for position alignment
        ai_analysis = None
        if self.openai_client:
            ai_analysis = self._analyze_position_alignment_with_ai(external_doc, actiz_doc)
        else:
            # Fallback analysis without AI
            ai_analysis = self._analyze_position_alignment_fallback(external_doc, actiz_doc, basic_comparison)
        
        return {
            'basic_comparison': basic_comparison,
            'ai_analysis': ai_analysis,
            'analysis_type': 'position_alignment',
            'stats': {
                'external_doc_length': len(external_doc),
                'actiz_doc_length': len(actiz_doc),
                'alignment_score': ai_analysis.get('alignment_score', 0) if ai_analysis else 0,
                'differences_count': len(basic_comparison.get('differences', [])) if basic_comparison else 0
            }
        }
    
    def analyze_external_reaction(self, policy_doc: str, reaction_doc: str) -> Dict[str, Any]:
        """Analyze external reactions to policy documents."""
        logger.info("Starting external reaction analysis")
        
        # Basic comparison
        basic_comparison = self.compare_documents_basic(policy_doc, reaction_doc)
        
        # AI analysis for reaction sentiment and points
        ai_analysis = None
        if self.openai_client:
            ai_analysis = self._analyze_external_reaction_with_ai(policy_doc, reaction_doc)
        
        return {
            'basic_comparison': basic_comparison,
            'ai_analysis': ai_analysis,
            'analysis_type': 'external_reaction',
            'stats': {
                'policy_doc_length': len(policy_doc),
                'reaction_doc_length': len(reaction_doc),
                'reaction_sentiment': ai_analysis.get('sentiment', 'neutral') if ai_analysis else 'neutral'
            }
        }
    
    def analyze_strategic_communication(self, doc1: str, doc2: str, doc3: str) -> Dict[str, Any]:
        """Analyze three documents for strategic communication insights."""
        logger.info("Starting strategic communication analysis")
        
        # Multi-document analysis
        docs = [doc1, doc2, doc3]
        
        # Pairwise comparisons
        comparisons = []
        comparisons.append(('doc1_vs_doc2', self.compare_documents_basic(doc1, doc2)))
        comparisons.append(('doc1_vs_doc3', self.compare_documents_basic(doc1, doc3)))
        comparisons.append(('doc2_vs_doc3', self.compare_documents_basic(doc2, doc3)))
        
        # AI analysis for strategic insights
        ai_analysis = None
        if self.openai_client:
            ai_analysis = self._analyze_strategic_communication_with_ai(doc1, doc2, doc3)
        
        return {
            'comparisons': comparisons,
            'ai_analysis': ai_analysis,
            'analysis_type': 'strategic_communication',
            'stats': {
                'total_documents': 3,
                'doc_lengths': [len(doc) for doc in docs],
                'total_content': sum(len(doc) for doc in docs),
                'strategic_themes': len(ai_analysis.get('themes', [])) if ai_analysis else 0
            }
        }
    
    def compare_documents_basic(self, text1: str, text2: str) -> Dict[str, Any]:
        """Perform basic document comparison using difflib."""
        try:
            # Normalize texts
            lines1 = self._normalize_text(text1).splitlines(keepends=True)
            lines2 = self._normalize_text(text2).splitlines(keepends=True)
            
            # Generate differences
            differences = []
            differ = difflib.unified_diff(
                lines1, lines2,
                fromfile='document1', tofile='document2',
                lineterm='', n=3
            )
            
            current_section = "Begin document"
            diff_counter = 0
            
            for line in differ:
                if line.startswith('@@'):
                    # Extract line context from diff header
                    match = re.search(r'@@\s*-(\d+),?(\d*)\s*\+(\d+),?(\d*)\s*@@\s*(.*)', line)
                    if match and match.group(5):
                        current_section = match.group(5).strip()[:50]
                elif line.startswith('-') and not line.startswith('---'):
                    # Removed line
                    content = line[1:].strip()
                    if content and len(content) > 5:  # Filter out empty/minimal changes
                        differences.append({
                            'type': 'verwijderd',
                            'original': content,
                            'modified': '',
                            'section_context': current_section,
                            'inline_diff': f'<span class="diff-removed">{content}</span>'
                        })
                        diff_counter += 1
                elif line.startswith('+') and not line.startswith('+++'):
                    # Added line
                    content = line[1:].strip()
                    if content and len(content) > 5:  # Filter out empty/minimal changes
                        differences.append({
                            'type': 'toegevoegd',
                            'original': '',
                            'modified': content,
                            'section_context': current_section,
                            'inline_diff': f'<span class="diff-added">{content}</span>'
                        })
                        diff_counter += 1
                
                # Limit differences to prevent performance issues
                if diff_counter >= 100:
                    differences.append({
                        'type': 'info',
                        'original': '',
                        'modified': f'... en {diff_counter - 100} meer wijzigingen',
                        'section_context': 'Limiet bereikt',
                        'inline_diff': '<em>Te veel wijzigingen om weer te geven</em>'
                    })
                    break
            
            # Enhanced inline diff for better visualization
            differences = self._enhance_inline_diffs(differences, text1, text2)
            
            return {
                'differences': differences,
                'total_changes': len(differences),
                'similarity_ratio': difflib.SequenceMatcher(None, text1, text2).ratio()
            }
            
        except Exception as e:
            logger.error(f"Basic comparison error: {e}")
            return {
                'differences': [],
                'total_changes': 0,
                'similarity_ratio': 0.0,
                'error': str(e)
            }
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove empty lines
        text = re.sub(r'\n\s*\n', '\n', text)
        return text.strip()
    
    def _enhance_inline_diffs(self, differences: List[Dict], text1: str, text2: str) -> List[Dict]:
        """Enhance differences with better inline visualization."""
        try:
            # For now, keep the simple inline diff
            # This can be enhanced later with more sophisticated diff visualization
            return differences
        except Exception as e:
            logger.warning(f"Inline diff enhancement failed: {e}")
            return differences
    
    def _analyze_version_changes_with_ai(self, doc1: str, doc2: str, differences: List[Dict]) -> Optional[Dict]:
        """Use AI to analyze version changes for insights."""
        try:
            # Prepare difference summary for AI
            diff_summary = []
            for diff in differences[:20]:  # Limit to first 20 differences
                diff_summary.append(f"Type: {diff['type']}, Context: {diff['section_context']}, "
                                  f"Original: {diff['original'][:100]}, Modified: {diff['modified'][:100]}")
            
            prompt = f"""
Analyseer de volgende documentwijzigingen en geef specifieke inzichten voor ActiZ:

WIJZIGINGEN SAMENVATTING:
{chr(10).join(diff_summary)}

DOCUMENT 1 (eerste 1000 karakters):
{doc1[:1000]}

DOCUMENT 2 (eerste 1000 karakters):
{doc2[:1000]}

Geef een analyse in JSON formaat met:
1. "summary": lijst van kernpunten van de wijzigingen (max 5 items)
2. "added": lijst van nieuwe onderwerpen/concepten (max 5 items)  
3. "removed": lijst van weggevallen/gewijzigde onderdelen (max 5 items)
4. "impact": lijst van beleidsmatige gevolgen voor ActiZ (max 7 items)

Focus op:
- Beleidsrelevantie voor zorgaanbieders
- Impact op gemeenten en financiering
- Nieuwe verplichtingen of kansen
- Strategische implicaties

Respond alleen met geldig JSON.
"""
            
            response = self._call_openai_api(prompt, max_tokens=1000)
            
            import json
            result = json.loads(response)
            return result
            
        except Exception as e:
            logger.error(f"AI version analysis failed: {e}")
            return None
    
    def _analyze_position_alignment_with_ai(self, external_doc: str, actiz_doc: str) -> Optional[Dict]:
        """Analyze alignment between external document and ActiZ position."""
        try:
            prompt = f"""
Analyseer de afstemming tussen een extern beleidsdocument en ActiZ standpunten:

EXTERN DOCUMENT (eerste 1500 karakters):
{external_doc[:1500]}

ACTIZ STANDPUNT (eerste 1500 karakters):
{actiz_doc[:1500]}

Geef een analyse in JSON formaat met:
1. "alignment_score": score 0-100 voor mate van afstemming
2. "aligned_points": lijst van onderwerpen waar documenten overeenkomen (max 5)
3. "conflicting_points": lijst van conflictpunten (max 5)
4. "opportunities": lijst van kansen voor ActiZ (max 5)
5. "risks": lijst van risico's of bedreigingen (max 5)
6. "recommendations": aanbevelingen voor ActiZ strategie (max 5)

Focus op zorgbeleid, financiering, innovatie en gemeentelijke samenwerking.

Respond alleen met geldig JSON.
"""
            
            response = self._call_openai_api(prompt, max_tokens=1200)
            
            import json
            result = json.loads(response)
            return result
            
        except Exception as e:
            logger.error(f"AI position analysis failed: {e}")
            return None
    
    def _analyze_external_reaction_with_ai(self, policy_doc: str, reaction_doc: str) -> Optional[Dict]:
        """Analyze external reactions to policy documents."""
        try:
            prompt = f"""
Analyseer externe reactie op beleidsdocument:

BELEIDSDOCUMENT (eerste 1500 karakters):
{policy_doc[:1500]}

EXTERNE REACTIE (eerste 1500 karakters):
{reaction_doc[:1500]}

Geef een analyse in JSON formaat met:
1. "sentiment": overall sentiment van reactie (positief/neutraal/negatief)
2. "key_concerns": hoofdpunten van kritiek of zorgen (max 5)
3. "support_points": punten van steun of goedkeuring (max 5)
4. "suggestions": voorstellen voor verbetering (max 5)
5. "stakeholder_impact": impact op verschillende belanghebbenden (max 5)
6. "response_strategy": aanbevelingen voor reactie vanuit ActiZ (max 5)

Focus op praktische gevolgen voor zorgverlening en beleidsimplementatie.

Respond alleen met geldig JSON.
"""
            
            response = self._call_openai_api(prompt, max_tokens=1200)
            
            import json
            result = json.loads(response)
            return result
            
        except Exception as e:
            logger.error(f"AI reaction analysis failed: {e}")
            return None
    
    def _analyze_strategic_communication_with_ai(self, doc1: str, doc2: str, doc3: str) -> Optional[Dict]:
        """Analyze three documents for strategic communication insights."""
        try:
            prompt = f"""
Analyseer drie documenten voor strategische communicatie-inzichten:

DOCUMENT 1 (eerste 1000 karakters):
{doc1[:1000]}

DOCUMENT 2 (eerste 1000 karakters):
{doc2[:1000]}

DOCUMENT 3 (eerste 1000 karakters):
{doc3[:1000]}

Geef een analyse in JSON formaat met:
1. "themes": gemeenschappelijke thema's over alle documenten (max 6)
2. "inconsistencies": inconsistenties tussen documenten (max 5)
3. "key_messages": belangrijkste boodschappen per document (max 4 per doc)
4. "stakeholder_mapping": relevantie per doelgroep (max 6)
5. "communication_gaps": ontbrekende elementen in communicatie (max 5)
6. "strategic_recommendations": aanbevelingen voor geïntegreerde communicatie (max 6)

Focus op beleidscoherentie en effectieve stakeholder communicatie.

Respond alleen met geldig JSON.
"""
            
            response = self._call_openai_api(prompt, max_tokens=1500)
            
            import json
            result = json.loads(response)
            return result
            
        except Exception as e:
            logger.error(f"AI strategic communication analysis failed: {e}")
            return None
    
    def _analyze_position_alignment_fallback(self, external_doc: str, actiz_doc: str, basic_comparison: Dict) -> Dict:
        """Fallback analysis without AI for position alignment."""
        logger.info("Using fallback position alignment analysis (no AI)")
        
        # Simple text-based analysis
        external_words = set(external_doc.lower().split())
        actiz_words = set(actiz_doc.lower().split())
        
        # Calculate basic alignment score
        common_words = external_words.intersection(actiz_words)
        total_words = external_words.union(actiz_words)
        alignment_score = int((len(common_words) / len(total_words)) * 100) if total_words else 0
        
        # Basic keyword analysis
        policy_keywords = ['beleid', 'strategie', 'doelstelling', 'actie', 'maatregel', 'uitvoering']
        care_keywords = ['zorg', 'patiënt', 'cliënt', 'behandeling', 'kwaliteit', 'veiligheid']
        
        external_lower = external_doc.lower()
        actiz_lower = actiz_doc.lower()
        
        policy_in_external = sum(1 for word in policy_keywords if word in external_lower)
        policy_in_actiz = sum(1 for word in policy_keywords if word in actiz_lower)
        care_in_external = sum(1 for word in care_keywords if word in external_lower)
        care_in_actiz = sum(1 for word in care_keywords if word in actiz_lower)
        
        return {
            'alignment_score': alignment_score,
            'aligned_points': [
                f"Beide documenten bevatten {len(common_words)} gemeenschappelijke termen",
                f"Beleidsfocus: Extern document ({policy_in_external} termen) vs ActiZ document ({policy_in_actiz} termen)",
                f"Zorgfocus: Extern document ({care_in_external} termen) vs ActiZ document ({care_in_actiz} termen)"
            ],
            'conflicting_points': [
                f"Unieke termen in extern document: {len(external_words - actiz_words)}",
                f"Unieke termen in ActiZ document: {len(actiz_words - external_words)}"
            ],
            'opportunities': [
                "Mogelijke afstemming op gemeenschappelijke terminologie",
                "Kansen voor gezamenlijke beleidsvorming waar overlap bestaat",
                "Potentieel voor strategische samenwerking"
            ],
            'risks': [
                "Verschillende terminologie kan tot verwarring leiden",
                "Mogelijk verschillende prioriteiten tussen documenten",
                "Risico op miscommunicatie zonder verdere afstemming"
            ],
            'recommendations': [
                f"Verhoog afstemming - huidige score: {alignment_score}%",
                "Organiseer overleg over terminologie en doelstellingen",
                "Ontwikkel gemeenschappelijke woordenlijst voor betere communicatie",
                "Evalueer verschillen in prioriteiten en zoek naar compromissen"
            ]
        }
    
    def _call_openai_api(self, prompt: str, max_tokens: int = 1000) -> str:
        """Make API call to OpenAI (regular or Azure) using new v1.0+ syntax."""
        try:
            if self.is_azure:
                # Azure OpenAI API call with new syntax
                deployment_name = os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-4')
                response = self.openai_client.chat.completions.create(
                    model=deployment_name,  # For Azure, this is the deployment name
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=0.3
                )
            else:
                # Regular OpenAI API call with new syntax
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=0.3
                )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise

# End of DocumentProcessor class