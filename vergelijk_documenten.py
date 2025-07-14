# vergelijk_documenten.py
import os
import base64
from dotenv import load_dotenv
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
import difflib

load_dotenv()

def lees_document(pdf_pad, label="Document"):
    """Lees een PDF document volledig"""
    print(f"📖 {label} inlezen: {pdf_pad}")
    
    endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    api_key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
    
    client = DocumentIntelligenceClient(
        endpoint=endpoint, 
        credential=AzureKeyCredential(api_key)
    )
    
    try:
        with open(pdf_pad, "rb") as pdf_file:
            pdf_data = pdf_file.read()
        
        pdf_base64 = base64.b64encode(pdf_data).decode()
        
        print(f"  🔄 Azure analyse van {label}...")
        
        poller = client.begin_analyze_document(
            "prebuilt-layout",
            {"base64Source": pdf_base64}
        )
        
        result = poller.result()
        
        print(f"  ✅ {label} gelezen: {len(result.content)} karakters, {len(result.pages) if result.pages else 0} pagina's")
        
        return result.content
        
    except Exception as e:
        print(f"  ❌ Fout bij {label}: {e}")
        return None

def vergelijk_documenten(tekst1, tekst2, doc1_naam="Document 1", doc2_naam="Document 2"):
    """Vergelijk twee documenten en toon verschillen"""
    print(f"\n🔍 Documenten vergelijken...")
    
    # Split tekst in lijnen voor betere vergelijking
    lijnen1 = tekst1.splitlines()
    lijnen2 = tekst2.splitlines()
    
    # Gebruik Python's difflib voor vergelijking
    differ = difflib.unified_diff(
        lijnen1, 
        lijnen2, 
        fromfile=doc1_naam,
        tofile=doc2_naam,
        lineterm='',
        n=3  # Context lijnen
    )
    
    verschillen = list(differ)
    
    if not verschillen:
        print("✅ Documenten zijn identiek!")
        return verschillen
    
    print(f"📊 Gevonden verschillen: {len(verschillen)} regels")
    
    # Sla verschillen op in bestand
    with open("document_verschillen.txt", "w", encoding="utf-8") as f:
        f.write(f"VERGELIJKING: {doc1_naam} vs {doc2_naam}\n")
        f.write("="*60 + "\n\n")
        
        for lijn in verschillen:
            f.write(lijn + "\n")
    
    print("💾 Verschillen opgeslagen in: document_verschillen.txt")
    
    # Toon eerste paar verschillen
    print("\n📋 Eerste verschillen:")
    print("-" * 50)
    for i, lijn in enumerate(verschillen[:20]):  # Eerste 20 regels
        if lijn.startswith('---') or lijn.startswith('+++'):
            print(f"📄 {lijn}")
        elif lijn.startswith('-'):
            print(f"❌ {lijn}")
        elif lijn.startswith('+'):
            print(f"✅ {lijn}")
        elif lijn.startswith('@@'):
            print(f"📍 {lijn}")
    
    if len(verschillen) > 20:
        print(f"... en nog {len(verschillen) - 20} verschillen meer")
    
    return verschillen

def eenvoudige_statistieken(verschillen):
    """Bereken eenvoudige statistieken over verschillen"""
    if not verschillen:
        return
    
    toegevoegd = len([l for l in verschillen if l.startswith('+')])
    verwijderd = len([l for l in verschillen if l.startswith('-')])
    
    print(f"\n📈 Statistieken:")
    print(f"  ➕ Toegevoegde regels: {toegevoegd}")
    print(f"  ➖ Verwijderde regels: {verwijderd}")
    print(f"  📝 Totaal wijzigingen: {toegevoegd + verwijderd}")

if __name__ == "__main__":
    print("🔍 DOCUMENT VERGELIJKER")
    print("=" * 50)
    
    # Voor nu vergelijken we het document met zichzelf (test)
    doc1_pad = "data\\HLOCompleet.pdf"
    doc2_pad = "data\\HLOCompleet.pdf"  # Zelfde document voor test
    
    print("📁 Voer de paden in van de documenten die je wilt vergelijken:")
    print(f"Document 1 (Enter voor {doc1_pad}):")
    input1 = input().strip()
    if input1:
        doc1_pad = input1
    
    print(f"Document 2 (Enter voor {doc2_pad}):")
    input2 = input().strip()
    if input2:
        doc2_pad = input2
    
    # Lees beide documenten
    tekst1 = lees_document(doc1_pad, "Document 1")
    tekst2 = lees_document(doc2_pad, "Document 2")
    
    if not tekst1 or not tekst2:
        print("❌ Kan een of beide documenten niet lezen!")
        exit()
    
    # Vergelijk documenten
    verschillen = vergelijk_documenten(
        tekst1, tekst2, 
        os.path.basename(doc1_pad), 
        os.path.basename(doc2_pad)
    )
    
    # Toon statistieken
    eenvoudige_statistieken(verschillen)
    
    print(f"\n🎉 Vergelijking voltooid!")