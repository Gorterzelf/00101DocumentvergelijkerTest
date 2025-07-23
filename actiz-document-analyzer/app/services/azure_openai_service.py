import os
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class AzureOpenAIService:
    """
    Service voor Azure OpenAI API calls
    """
    
    def __init__(self):
        self.endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        self.api_key = os.getenv('AZURE_OPENAI_KEY')
        self.api_version = os.getenv('AZURE_OPENAI_VERSION', '2024-02-15-preview')
        self.deployment = os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-4')

        # Debug: Log configuration (without showing actual keys)
        logger.info(f"Azure config - Endpoint: {self.endpoint}")
        logger.info(f"Azure config - API Key: {'***' if self.api_key else 'None'}")
        logger.info(f"Azure config - Version: {self.api_version}")
        logger.info(f"Azure config - Deployment: {self.deployment}")

        # Validate configuration
        if not self.endpoint or not self.api_key:
            logger.warning("Azure OpenAI not configured - using mock responses")
            self.configured = False
        else:
            try:
                # Correcte import voor OpenAI 1.3.0
                from openai import AzureOpenAI
                logger.info(f"OpenAI version: 1.3.0")
            
                # Initialize OpenAI client met correcte syntax
                self.client = AzureOpenAI(
                    api_key=self.api_key,
                    api_version=self.api_version,
                    azure_endpoint=self.endpoint
                )
            
                self.configured = True
                logger.info("✅ Azure OpenAI Service initialized successfully")
            
            except Exception as e:
                logger.error(f"❌ Azure OpenAI initialization failed: {e}")
                logger.error(f"Exception type: {type(e).__name__}")
                import traceback
                logger.error(f"Full traceback: {traceback.format_exc()}")
                self.configured = False

    def compare_documents(self, text1: str, text2: str, filename1: str, filename2: str) -> Dict:
        """
        Compare two documents and analyze differences - NIEUWE HOOFDFUNCTIE
        """
        logger.info(f"Comparing documents: {len(text1)} vs {len(text2)} characters")
        
        if not self.configured:
            return self._mock_comparison(text1, text2, filename1, filename2)
        
        try:
            prompt = self._build_comparison_prompt(text1, text2, filename1, filename2)
            
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": self._get_comparison_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,  # Lagere temperature voor consistente vergelijking
                max_tokens=2000   # Meer tokens voor uitgebreide vergelijking
            )
            
            result = response.choices[0].message.content
            logger.info(f"Azure OpenAI document comparison completed")
            
            return {
                'analysis_type': 'version_compare',
                'result': result,
                'word_count': len(text1.split()) + len(text2.split()),
                'char_count': len(text1) + len(text2),
                'demo_mode': False,
                'comparison_stats': {
                    'doc1_words': len(text1.split()),
                    'doc2_words': len(text2.split()),
                    'size_difference': len(text2.split()) - len(text1.split())
                }
            }
            
        except Exception as e:
            logger.error(f"Azure OpenAI comparison error: {str(e)}")
            # Fallback to mock if API fails
            return self._mock_comparison(text1, text2, filename1, filename2)
    
    def analyze_document(self, text: str, analysis_type: str) -> Dict:
        """
        Analyze document text based on analysis type - BESTAANDE FUNCTIE
        """
        logger.info(f"Analyzing document: {len(text)} chars, type: {analysis_type}")
    
        if not self.configured:
            return self._mock_analysis(text, analysis_type)
    
        try:
            prompt = self._build_prompt(text, analysis_type)
        
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": self._get_system_prompt(analysis_type)},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )
        
            result = response.choices[0].message.content
            logger.info(f"Azure OpenAI analysis completed for {analysis_type}")
        
            return {
                'analysis_type': analysis_type,
                'result': result,
                'word_count': len(text.split()),
                'char_count': len(text),
                'demo_mode': False
            }
        
        except Exception as e:
            logger.error(f"Azure OpenAI error: {str(e)}")
            # Fallback to mock if API fails
            return self._mock_analysis(text, analysis_type)
    
    def test_connection(self) -> bool:
        """
        Test Azure OpenAI connection
        """
        if not self.configured:
            logger.warning("Cannot test - Azure OpenAI not configured")
            return False
        
        try:
            # Simple test call
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "user", "content": "Test connectie - antwoord alleen 'OK'"}
                ],
                max_tokens=10,
                temperature=0
            )
            
            result = response.choices[0].message.content.strip()
            logger.info(f"✅ Azure OpenAI connection test successful: {result}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Azure OpenAI connection test failed: {e}")
            return False

    def _build_comparison_prompt(self, text1: str, text2: str, filename1: str, filename2: str) -> str:
        """
        Build specialized prompt for document comparison - NIEUWE FUNCTIE
        """
        # Limit text length for API efficiency
        max_chars = 2500  # Per document
        
        if len(text1) > max_chars:
            text1 = text1[:max_chars] + "... [afgesneden voor API limiet]"
        if len(text2) > max_chars:
            text2 = text2[:max_chars] + "... [afgesneden voor API limiet]"
        
        return f"""
Voer een grondige vergelijking uit tussen deze twee documentversies:

**DOCUMENT 1 ({filename1}):**
{text1}

**DOCUMENT 2 ({filename2}):**
{text2}

Analyseer de verschillen volgens deze structuur:

## 📊 Overzicht Wijzigingen
- Algemene indruk van de wijzigingen
- Omvang van de aanpassingen (klein/gemiddeld/groot)

## ➕ Nieuwe Toevoegingen
- Nieuwe secties, paragrafen of inhoud in document 2
- Nieuwe beleidsmaatregelen of regelingen

## ✏️ Wijzigingen in Bestaande Content
- Aangepaste teksten, definities of procedures
- Gewijzigde deadlines, bedragen of voorwaarden

## ➖ Verwijderde Content
- Weggelaten secties of bepalingen uit document 1
- Geschrapte regelingen of procedures

## 🎯 Impact Analyse voor ActiZ
- Relevantie voor ouderenzorg sector
- Gevolgen voor ActiZ leden
- Aandachtspunten en risico's

## 💡 Aanbevelingen
- Vervolgacties voor ActiZ
- Communicatie naar leden
- Monitoring van implementatie

Focus op concrete, identificeerbare verschillen en geef praktische inzichten voor de ouderenzorg sector.
"""

    def _get_comparison_system_prompt(self) -> str:
        """
        Specialized system prompt for document comparison - NIEUWE FUNCTIE
        """
        return """Je bent een expert documentanalist voor ActiZ, de branchevereniging voor ouderenzorg. 
Je specialisatie ligt in het vergelijken van beleidsdocumenten en het identificeren van relevante wijzigingen.

Bij het vergelijken van documenten:
- Wees specifiek en concreet over de verschillen
- Focus op wijzigingen die relevant zijn voor de ouderenzorg
- Gebruik duidelijke Nederlandse taal
- Structureer je analyse logisch met koppen en bullet points
- Geef praktische aanbevelingen voor ActiZ

Je doel is om beleidsmedewerkers snel inzicht te geven in wat er veranderd is en wat dit betekent voor de sector."""

    def _build_prompt(self, text: str, analysis_type: str) -> str:
        """Build prompt based on analysis type - BESTAANDE FUNCTIE"""
    
        # Limit text length for API efficiency
        max_chars = 3000
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
    
        prompts = {
            'version_compare': f"""
Analyseer dit beleidsdocument en geef een samenvatting van de belangrijkste punten:

DOCUMENT:
{text}

Geef een analyse in deze structuur:
1. Hoofdonderwerp
2. Belangrijkste beleidsmaatregelen  
3. Doelgroepen
4. Implementatie
5. Mogelijke impact
""",
        
            'position_analysis': f"""
Analyseer dit beleidsdocument vanuit ActiZ perspectief (branchevereniging ouderenzorg):

DOCUMENT:
{text}

Geef een analyse in deze structuur:
1. Relevantie voor ouderenzorg
2. Mogelijke gevolgen voor ActiZ leden
3. Kansen en bedreigingen
4. Aanbevelingen voor ActiZ positie
""",

            'external_analysis': f"""
Analyseer dit document op externe reacties en sentiment:

DOCUMENT:
{text}

Geef een analyse in deze structuur:
1. Algemeen sentiment
2. Belangrijkste bezwaren/zorgen
3. Positieve punten
4. Aanbevelingen voor reactie
""",

            'strategy_analysis': f"""
Analyseer dit document voor communicatiestrategie:

DOCUMENT:
{text}

Geef een analyse in deze structuur:
1. Communicatie doelen
2. Doelgroepen
3. Kernboodschappen
4. Communicatie kanalen
5. Risico's en mitigatie
"""
        }
    
        return prompts.get(analysis_type, prompts['version_compare'])

    def _get_system_prompt(self, analysis_type: str) -> str:
        """Get system prompt based on analysis type - BESTAANDE FUNCTIE"""
        return """Je bent een expert in Nederlands zorgbeleid en werkt voor ActiZ, 
de branchevereniging voor ouderenzorg. Je analyseert beleidsdocumenten en geeft 
heldere, praktische inzichten. Gebruik duidelijke Nederlandse taal en focus op 
concrete aanbevelingen."""

    def _mock_comparison(self, text1: str, text2: str, filename1: str, filename2: str) -> Dict:
        """
        Mock comparison for testing - NIEUWE FUNCTIE
        """
        word_diff = len(text2.split()) - len(text1.split())
        
        result = f"""
## 📊 Overzicht Wijzigingen

**Document Vergelijking:** {filename1} ↔ {filename2}
- **Document 1:** {len(text1.split())} woorden, {len(text1)} karakters
- **Document 2:** {len(text2.split())} woorden, {len(text2)} karakters  
- **Verschil:** {word_diff:+d} woorden

## 🧪 Demo Modus Actief

**Status:** Documenten succesvol verwerkt en klaar voor analyse
**Tekstextractie:** ✅ Beide documenten ingelezen
**AI Vergelijking:** ⏳ Configureer Azure OpenAI voor gedetailleerde vergelijking

## 💡 Volgende Stappen

1. **Azure OpenAI configureren** voor echte document vergelijking
2. **Beide documenten** worden dan geanalyseerd op:
   - Toegevoegde content
   - Gewijzigde passages  
   - Verwijderde secties
   - Impact voor ActiZ

---
*Demo modus - configureer Azure credentials voor echte AI vergelijking*
"""
        
        return {
            'analysis_type': 'version_compare',
            'result': result,
            'word_count': len(text1.split()) + len(text2.split()),
            'char_count': len(text1) + len(text2),
            'demo_mode': True,
            'comparison_stats': {
                'doc1_words': len(text1.split()),
                'doc2_words': len(text2.split()),
                'size_difference': word_diff
            }
        }
    
    def _mock_analysis(self, text: str, analysis_type: str) -> Dict:
        """
        Mock analysis for testing - BESTAANDE FUNCTIE
        """
        mock_results = {
            'version_compare': f"""
## Documentanalyse Resultaat

**📄 Bestand geanalyseerd:** ✅  
**📊 Statistieken:**
- Woorden: {len(text.split())}
- Karakters: {len(text)}
- Geschatte leestijd: {len(text.split()) // 200 + 1} minuten

**🔍 Hoofdpunten:**
- Document succesvol verwerkt
- Tekst extractie voltooid
- Ready voor Azure OpenAI analyse

**💡 Volgende stappen:**
- Configureer Azure OpenAI voor gedetailleerde analyse
- Test met verschillende document types

---
*Demo modus actief - configureer Azure credentials voor echte AI analyse*
""",
            'position_analysis': f"""
## ActiZ Positie Analyse

**🏥 Relevantie voor ouderenzorg:** Te bepalen  
**📋 Document details:**
- Lengte: {len(text.split())} woorden
- Status: Verwerkt en klaar voor analyse

**🎯 Aanbevelingen:**
- Configureer Azure OpenAI voor gedetailleerde beleidsanalyse
- Document is succesvol ingelezen

---
*Demo modus actief*
""",
            'external_analysis': f"""
## Externe Reactie Analyse

**📊 Document status:** Verwerkt  
**💬 Sentiment:** Ready voor analyse  
**📈 Statistieken:** {len(text.split())} woorden verwerkt

---
*Demo modus actief*
""",
            'strategy_analysis': f"""
## Communicatie Strategie Analyse

**📱 Document verwerkt:** ✅  
**🎯 Klaar voor:** Strategische analyse  
**📊 Omvang:** {len(text.split())} woorden

---
*Demo modus actief*
"""
        }
        
        result = mock_results.get(analysis_type, mock_results['version_compare'])
        
        return {
            'analysis_type': analysis_type,
            'result': result,
            'word_count': len(text.split()),
            'char_count': len(text),
            'demo_mode': True
        }