# ai_analyse_verschillen.py - AANGEPASTE VERSIE
import os
import json
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

class DocumentAIAnalyzer:
    def __init__(self):
        self.client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),  # Aangepast
            api_version=os.getenv("OPENAI_API_VERSION")  # Aangepast
        )
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "001-01-documentvergelijker-test-gpt-4o")
    
    def analyseer_verschillen(self, verschillen_tekst, context="beleidsdocument"):
        """AI analyse van document verschillen"""
        
        print("🤖 AI analyse starten...")
        
        prompt = self._maak_analyse_prompt(verschillen_tekst, context)
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {
                        "role": "system", 
                        "content": "Je bent een expert in beleidsanalyse en document vergelijking. Je analyseert wijzigingen in overheidsdocumenten en legt uit wat deze betekenen."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            analyse = response.choices[0].message.content
            
            print("✅ AI analyse voltooid!")
            return analyse
            
        except Exception as e:
            print(f"❌ AI analyse fout: {e}")
            return None
    
    def _maak_analyse_prompt(self, verschillen_tekst, context):
        """Maak een gestructureerde prompt voor AI analyse"""
        
        return f"""
TAAK: Analyseer de wijzigingen in dit {context} en leg uit wat ze betekenen.

DOCUMENT VERSCHILLEN:
{verschillen_tekst[:3000]}

ANALYSEER DE VOLGENDE ASPECTEN:

1. 📊 SAMENVATTING
   - Wat zijn de belangrijkste wijzigingen?
   - Hoeveel wijzigingen zijn er in totaal?

2. 🏛️ BELEIDSIMPACT  
   - Welke beleidswijzigingen zijn er?
   - Wat betekenen deze voor de praktijk?

3. 💰 FINANCIËLE WIJZIGINGEN
   - Zijn er budget/bedrag wijzigingen?
   - Wat is de financiële impact?

4. 📅 TIJDLIJN WIJZIGINGEN
   - Zijn er datum/deadline wijzigingen?
   - Wat betekent dit voor planning?

5. 🎯 STAKEHOLDER IMPACT
   - Wie wordt geraakt door deze wijzigingen?
   - Wat moeten zij weten/doen?

6. ⚠️ RISICO'S & AANDACHTSPUNTEN
   - Wat zijn mogelijke risico's?
   - Waar moet extra aandacht naar uit?

GEEF JE ANTWOORD IN DEZE STRUCTUUR met duidelijke headers (##).
"""

def test_ai_installatie():
    """Test of AI configuratie werkt"""
    
    print("🔧 Test AI configuratie...")
    
    # Check environment variables
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    key = os.getenv("AZURE_OPENAI_API_KEY")  # Aangepast
    api_version = os.getenv("OPENAI_API_VERSION")  # Aangepast
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "001-01-documentvergelijker-test-gpt-4o")
    
    print(f"  - Endpoint: {'✓' if endpoint else '❌'} {endpoint}")
    print(f"  - API Key: {'✓' if key else '❌'} {key[:10] + '...' if key else 'None'}")
    print(f"  - API Version: {'✓' if api_version else '❌'} {api_version}")
    print(f"  - Deployment: {'✓' if deployment else '❌'} {deployment}")
    
    if not all([endpoint, key, api_version]):
        print("❌ Ontbrekende configuratie!")
        return False
    
    # Test verbinding
    try:
        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=key,
            api_version=api_version
        )
        
        response = client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": "Test: zeg 'AI werkt!'"}],
            max_tokens=10
        )
        
        result = response.choices[0].message.content
        print(f"✅ AI test succesvol: {result}")
        return True
        
    except Exception as e:
        print(f"❌ AI test mislukt: {e}")
        return False

def analyseer_verschillen_bestand(verschillen_bestand="test_verschillen.txt"):
    """Analyseer verschillen uit een bestand"""
    
    if not os.path.exists(verschillen_bestand):
        print(f"❌ Verschillen bestand niet gevonden: {verschillen_bestand}")
        print("Run eerst 'python test_echte_verschillen.py'")
        return
    
    # Lees verschillen
    with open(verschillen_bestand, "r", encoding="utf-8") as f:
        verschillen_tekst = f.read()
    
    print(f"📖 Verschillen gelezen: {len(verschillen_tekst)} karakters")
    
    # AI analyse
    analyzer = DocumentAIAnalyzer()
    analyse = analyzer.analyseer_verschillen(verschillen_tekst, "Hoofdlijnenakkoord Ouderenzorg")
    
    if analyse:
        # Sla analyse op
        with open("ai_analyse_rapport.txt", "w", encoding="utf-8") as f:
            f.write("🤖 AI ANALYSE VAN DOCUMENT VERSCHILLEN\n")
            f.write("="*60 + "\n\n")
            f.write(analyse)
        
        print("💾 AI analyse opgeslagen in: ai_analyse_rapport.txt")
        
        # Toon eerste deel
        print("\n" + "="*60)
        print("🤖 AI ANALYSE PREVIEW:")
        print("="*60)
        print(analyse[:800] + "..." if len(analyse) > 800 else analyse)
        print("="*60)
        
        return analyse
    
    return None

if __name__ == "__main__":
    print("🤖 DOCUMENT AI ANALYZER")
    print("="*50)
    
    # Test eerst configuratie
    if not test_ai_installatie():
        print("\n🔧 Fix eerst de AI configuratie!")
        exit()
    
    # Analyseer verschillen
    analyse = analyseer_verschillen_bestand()
    
    if analyse:
        print("\n🎉 AI analyse voltooid!")
        print("📄 Bekijk 'ai_analyse_rapport.txt' voor het volledige rapport")
    else:
        print("\n❌ AI analyse mislukt")