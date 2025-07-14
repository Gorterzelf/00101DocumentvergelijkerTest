"""
Analysis Strategies - Strategy Pattern Implementation
Elke analyse heeft zijn eigen geïsoleerde implementatie
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional
import logging
import json
import difflib

logger = logging.getLogger(__name__)


class AnalysisStrategy(ABC):
    """Abstract base class voor alle analyse strategieën"""
    
    def __init__(self, openai_client):
        self.client = openai_client
        self.deployment_name = "gpt-4"
    
    @abstractmethod
    def analyze(self, text1: str, text2: str, text3: Optional[str] = None) -> Dict:
        """Voer de specifieke analyse uit"""
        pass
    
    @abstractmethod
    def get_display_name(self) -> str:
        """Geef de display naam voor deze analyse"""
        pass
    
    @abstractmethod
    def get_required_documents(self) -> List[str]:
        """Geef lijst van vereiste documenten"""
        pass
    
    @abstractmethod
    def format_results(self, analysis_result: Dict) -> Dict:
        """Format de resultaten voor display"""
        pass
    
    def generate_summary(self, text: str, max_length: int = 300) -> str:
        """Genereer een samenvatting - gedeelde functionaliteit"""
        try:
            prompt = f"""
            Maak een beknopte samenvatting van het volgende document in maximaal {max_length} woorden.
            Focus op de hoofdpunten en belangrijkste conclusies.
            
            Document:
            {text[:4000]}...
            
            Samenvatting in het Nederlands:
            """
            
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "Je bent een expert in het samenvatten van documenten."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return "Samenvatting kon niet worden gegenereerd."


class VersionComparisonStrategy(AnalysisStrategy):
    """Strategie voor versie vergelijking"""
    
    def get_display_name(self) -> str:
        return "Versie Vergelijking"
    
    def get_required_documents(self) -> List[str]:
        return ["doc1", "doc2"]
    
    def analyze(self, text1: str, text2: str, text3: Optional[str] = None) -> Dict:
        """Analyseer verschillen tussen twee versies"""
        logger.info("Starting version comparison analysis")
        
        result = {
            'mode': 'version_comparison',
            'basic_comparison': self._compare_texts(text1, text2),
            'ai_analysis': self._analyze_changes_with_ai(text1, text2),
            'doc1_summary': self.generate_summary(text1),
            'doc2_summary': self.generate_summary(text2)
        }
        
        return result
    
    def _compare_texts(self, text1: str, text2: str) -> Dict:
        """Advanced text comparison with proper difference formatting"""
        logger.info(f"Comparing texts - Doc1: {len(text1)} chars, Doc2: {len(text2)} chars")
        logger.info(f"Doc1 preview: {text1[:200]}...")
        logger.info(f"Doc2 preview: {text2[:200]}...")
        
        # Split into paragraphs for better context
        paragraphs1 = [p.strip() for p in text1.split('\n\n') if p.strip()]
        paragraphs2 = [p.strip() for p in text2.split('\n\n') if p.strip()]
        
        # If no paragraphs found, split by single newline
        if not paragraphs1:
            paragraphs1 = [p.strip() for p in text1.split('\n') if p.strip()]
        if not paragraphs2:
            paragraphs2 = [p.strip() for p in text2.split('\n') if p.strip()]
            
        # If still no paragraphs, treat whole text as one paragraph
        if not paragraphs1:
            paragraphs1 = [text1.strip()] if text1.strip() else []
        if not paragraphs2:
            paragraphs2 = [text2.strip()] if text2.strip() else []
        
        logger.info(f"Found {len(paragraphs1)} paragraphs in doc1, {len(paragraphs2)} in doc2")
        
        # Use SequenceMatcher for paragraph-level comparison
        sequence_matcher = difflib.SequenceMatcher(None, paragraphs1, paragraphs2)
        
        differences = []
        added_count = 0
        removed_count = 0
        modified_count = 0
        moved_blocks = []
        
        # Process all operations
        for tag, i1, i2, j1, j2 in sequence_matcher.get_opcodes():
            if tag == 'delete':
                # Text was removed
                for i in range(i1, i2):
                    removed_count += 1
                    differences.append({
                        'type': 'verwijderd',
                        'original': paragraphs1[i],
                        'modified': '',
                        'section_context': f'Paragraaf {i+1}',
                        'inline_diff': f'<span class="diff-removed">{paragraphs1[i]}</span>'
                    })
                    
            elif tag == 'insert':
                # Text was added
                for j in range(j1, j2):
                    added_count += 1
                    differences.append({
                        'type': 'toegevoegd',
                        'original': '',
                        'modified': paragraphs2[j],
                        'section_context': f'Nieuwe paragraaf',
                        'inline_diff': f'<span class="diff-added">{paragraphs2[j]}</span>'
                    })
                    
            elif tag == 'replace':
                # Text was modified
                old_paras = paragraphs1[i1:i2]
                new_paras = paragraphs2[j1:j2]
                
                # Compare each pair
                for idx, (old, new) in enumerate(zip(old_paras, new_paras)):
                    para_matcher = difflib.SequenceMatcher(None, old, new)
                    similarity = para_matcher.ratio()
                    
                    if similarity > 0.3:  # Lower threshold for better detection
                        # Create inline diff
                        inline_diff = self._create_inline_diff(old, new)
                        modified_count += 1
                        differences.append({
                            'type': 'gewijzigd',
                            'original': old,
                            'modified': new,
                            'section_context': f'Paragraaf {i1+idx+1}',
                            'inline_diff': inline_diff,
                            'similarity': round(similarity * 100, 1)
                        })
                    else:
                        # Too different, show as remove + add
                        removed_count += 1
                        added_count += 1
                        differences.extend([
                            {
                                'type': 'verwijderd',
                                'original': old,
                                'modified': '',
                                'section_context': f'Paragraaf {i1+idx+1}',
                                'inline_diff': f'<span class="diff-removed">{old}</span>'
                            },
                            {
                                'type': 'toegevoegd',
                                'original': '',
                                'modified': new,
                                'section_context': f'Nieuwe paragraaf',
                                'inline_diff': f'<span class="diff-added">{new}</span>'
                            }
                        ])
        
        # Detect moved blocks
        for i, para1 in enumerate(paragraphs1):
            if len(para1) > 50:  # Only check substantial paragraphs
                for j, para2 in enumerate(paragraphs2):
                    if para1 == para2 and abs(i - j) > 2:  # Same text, different position
                        moved_blocks.append({
                            'text': para1[:200] + '...' if len(para1) > 200 else para1,
                            'from_position': i + 1,
                            'to_position': j + 1,
                            'from_context': f'Paragraaf {i+1}',
                            'to_context': f'Paragraaf {j+1}'
                        })
                        break
        
        # Calculate overall similarity
        overall_matcher = difflib.SequenceMatcher(None, text1, text2)
        similarity_ratio = overall_matcher.ratio()
        
        logger.info(f"Found {added_count} additions, {removed_count} removals, {modified_count} modifications, {len(moved_blocks)} moves")
        logger.info(f"Similarity: {similarity_ratio*100:.2f}%")
        
        # Ensure we always have at least the total count
        total_changes = len(differences)
        if total_changes == 0 and similarity_ratio < 0.95:
            # If no differences found but texts are different, force a comparison
            differences.append({
                'type': 'gewijzigd',
                'original': text1,
                'modified': text2,
                'section_context': 'Volledige document',
                'inline_diff': self._create_inline_diff(text1, text2),
                'similarity': round(similarity_ratio * 100, 1)
            })
            total_changes = 1
        
        return {
            'differences': differences,
            'similarity_percentage': round(similarity_ratio * 100, 2),
            'total_changes': total_changes,
            'added_count': added_count,
            'removed_count': removed_count,
            'modified_count': modified_count,
            'moved_blocks': moved_blocks,
            # Keep these for backward compatibility
            'added_content': [d['modified'] for d in differences if d['type'] == 'toegevoegd'][:10],
            'removed_content': [d['original'] for d in differences if d['type'] == 'verwijderd'][:10]
        }
    
    def _create_inline_diff(self, text1: str, text2: str) -> str:
        """Create an inline diff showing word-level changes"""
        words1 = text1.split()
        words2 = text2.split()
        
        matcher = difflib.SequenceMatcher(None, words1, words2)
        result = []
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                result.extend(words1[i1:i2])
            elif tag == 'delete':
                result.append(f'<span class="diff-removed">{" ".join(words1[i1:i2])}</span>')
            elif tag == 'insert':
                result.append(f'<span class="diff-added">{" ".join(words2[j1:j2])}</span>')
            elif tag == 'replace':
                result.append(f'<span class="diff-removed">{" ".join(words1[i1:i2])}</span>')
                result.append(f'<span class="diff-added">{" ".join(words2[j1:j2])}</span>')
        
        return ' '.join(result)
    
    def _analyze_changes_with_ai(self, text1: str, text2: str) -> Dict:
        """AI analysis of changes"""
        prompt = f"""
        Analyseer de verschillen tussen deze twee versies van een document.
        
        Versie 1:
        {text1[:2000]}...
        
        Versie 2:
        {text2[:2000]}...
        
        Geef een analyse van:
        1. Belangrijkste inhoudelijke wijzigingen
        2. Verplaatste tekstblokken
        3. Subtiele betekenisverschillen
        4. Impact van de wijzigingen
        
        Antwoord in het Nederlands.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "Je bent een expert in documentvergelijking."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            return {
                'ai_analysis': response.choices[0].message.content
            }
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return {'ai_analysis': "AI-analyse kon niet worden uitgevoerd."}
    
    def format_results(self, analysis_result: Dict) -> Dict:
        """Format results for display"""
        formatted = {
            'mode': 'version_comparison',
            'show_version_comparison': True,
            'basic_comparison': analysis_result.get('basic_comparison', {}),
            'ai_analysis': analysis_result.get('ai_analysis', {}),
            'doc1_summary': analysis_result.get('doc1_summary', ''),
            'doc2_summary': analysis_result.get('doc2_summary', '')
        }
        
        logger.info(f"Formatted results: {formatted.get('basic_comparison', {}).get('total_changes', 0)} changes found")
        return formatted


class ActiZPositionStrategy(AnalysisStrategy):
    """Strategie voor ActiZ positie analyse"""
    
    def get_display_name(self) -> str:
        return "ActiZ Positie Analyse"
    
    def get_required_documents(self) -> List[str]:
        return ["doc1", "doc2"]
    
    def analyze(self, text1: str, text2: str, text3: Optional[str] = None) -> Dict:
        """Analyseer ActiZ positie t.o.v. beleid"""
        logger.info("Starting ActiZ position analysis")
        
        result = {
            'mode': 'actiz_position',
            'position_analysis': self._analyze_position(text1, text2),
            'policy_summary': self.generate_summary(text1),
            'actiz_summary': self.generate_summary(text2)
        }
        
        return result
    
    def _analyze_position(self, policy_text: str, actiz_text: str) -> Dict:
        """Analyse ActiZ positie met AI"""
        prompt = f"""
        Je bent een beleidsanalist gespecialiseerd in de zorgsector. 
        Analyseer het ActiZ standpunt ten opzichte van het beleid.
        
        Beleid:
        {policy_text[:3000]}...
        
        ActiZ Standpunt:
        {actiz_text[:3000]}...
        
        Geef een analyse met:
        1. In hoeverre ondersteunt ActiZ het beleid? (schaal 1-10)
        2. Belangrijkste steunpunten
        3. Belangrijkste kritiekpunten
        4. Voorgestelde verbeteringen door ActiZ
        5. Impact op de zorgsector volgens ActiZ
        
        Antwoord ALLEEN in JSON formaat:
        {{
            "ondersteuning_score": 7,
            "steunpunten": ["punt1", "punt2", ...],
            "kritiekpunten": ["kritiek1", "kritiek2", ...],
            "verbeteringen": ["verbetering1", "verbetering2", ...],
            "impact_zorgsector": "beschrijving van de impact"
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "Je bent een expert in zorgbeleid. Antwoord ALLEEN in JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            content = response.choices[0].message.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            
            return json.loads(content.strip())
            
        except Exception as e:
            logger.error(f"Position analysis failed: {e}")
            return {
                "ondersteuning_score": 0,
                "steunpunten": ["Analyse kon niet worden uitgevoerd"],
                "kritiekpunten": [],
                "verbeteringen": [],
                "impact_zorgsector": "Onbekend"
            }
    
    def format_results(self, analysis_result: Dict) -> Dict:
        """Format results for display"""
        return {
            'show_actiz_position': True,
            'position_analysis': analysis_result.get('position_analysis', {}),
            'summaries': {
                'policy': analysis_result.get('policy_summary', ''),
                'actiz': analysis_result.get('actiz_summary', '')
            }
        }


class ExternalReactionStrategy(AnalysisStrategy):
    """Strategie voor externe reactie analyse"""
    
    def get_display_name(self) -> str:
        return "Externe Reactie Analyse"
    
    def get_required_documents(self) -> List[str]:
        return ["doc1", "doc2"]
    
    def analyze(self, text1: str, text2: str, text3: Optional[str] = None) -> Dict:
        """Analyseer externe reactie op beleid"""
        logger.info("Starting external reaction analysis")
        
        result = {
            'mode': 'external_reaction',
            'reaction_analysis': self._analyze_reaction(text1, text2),
            'policy_summary': self.generate_summary(text1),
            'reaction_summary': self.generate_summary(text2)
        }
        
        return result
    
    def _analyze_reaction(self, policy_text: str, reaction_text: str) -> Dict:
        """Analyse externe reactie met AI"""
        prompt = f"""
        Je bent een beleidsanalist. Analyseer de volgende reactie op het beleid.
        
        Beleid:
        {policy_text[:3000]}...
        
        Reactie:
        {reaction_text[:3000]}...
        
        Geef een gestructureerde analyse met:
        1. Hoofdpunten van de reactie (maximaal 5)
        2. Toon van de reactie (positief/neutraal/kritisch)
        3. Belangrijkste zorgen of complimenten
        4. Aanbevelingen voor beleidsaanpassing
        
        Antwoord ALLEEN in JSON formaat:
        {{
            "hoofdpunten": ["punt1", "punt2", ...],
            "toon": "positief/neutraal/kritisch",
            "zorgen": ["zorg1", "zorg2", ...],
            "complimenten": ["compliment1", "compliment2", ...],
            "aanbevelingen": ["aanbeveling1", "aanbeveling2", ...]
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "Je bent een beleidsanalist. Antwoord ALLEEN in JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            content = response.choices[0].message.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            
            return json.loads(content.strip())
            
        except Exception as e:
            logger.error(f"Reaction analysis failed: {e}")
            return {
                "hoofdpunten": ["Analyse kon niet worden uitgevoerd"],
                "toon": "onbekend",
                "zorgen": [],
                "complimenten": [],
                "aanbevelingen": []
            }
    
    def format_results(self, analysis_result: Dict) -> Dict:
        """Format results for display"""
        return {
            'show_external_reaction': True,
            'reaction_analysis': analysis_result.get('reaction_analysis', {}),
            'summaries': {
                'policy': analysis_result.get('policy_summary', ''),
                'reaction': analysis_result.get('reaction_summary', '')
            }
        }


class StrategicCommunicationStrategy(AnalysisStrategy):
    """Strategie voor strategische communicatie analyse"""
    
    def get_display_name(self) -> str:
        return "Strategische Communicatie"
    
    def get_required_documents(self) -> List[str]:
        return ["doc1", "doc2", "doc3"]
    
    def analyze(self, text1: str, text2: str, text3: Optional[str] = None) -> Dict:
        """Analyseer strategische communicatie alignment"""
        logger.info("Starting strategic communication analysis")
        
        result = {
            'mode': 'strategic_communication',
            'communication_analysis': self._analyze_communication(text1, text2, text3),
            'doc1_summary': self.generate_summary(text1),
            'doc2_summary': self.generate_summary(text2),
            'doc3_summary': self.generate_summary(text3) if text3 else ""
        }
        
        return result
    
    def _analyze_communication(self, doc1: str, doc2: str, doc3: str) -> Dict:
        """Analyse strategische communicatie met AI"""
        prompt = f"""
        Analyseer de coherentie en alignment tussen deze drie documenten voor strategische communicatie.
        
        Document 1 (Beleid):
        {doc1[:2000]}...
        
        Document 2 (Communicatieplan):
        {doc2[:2000]}...
        
        Document 3 (Stakeholder document):
        {doc3[:2000] if doc3 else "Niet aanwezig"}...
        
        Geef een analyse met:
        1. Gemeenschappelijke thema's
        2. Inconsistenties tussen documenten
        3. Belangrijkste boodschappen
        4. Communicatie gaps
        5. Strategische aanbevelingen
        
        Antwoord ALLEEN in JSON formaat:
        {{
            "gemeenschappelijke_themas": ["thema1", "thema2", ...],
            "inconsistenties": ["inconsistentie1", "inconsistentie2", ...],
            "hoofdboodschappen": ["boodschap1", "boodschap2", ...],
            "communicatie_gaps": ["gap1", "gap2", ...],
            "aanbevelingen": ["aanbeveling1", "aanbeveling2", ...]
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "Je bent een communicatie expert. Antwoord ALLEEN in JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            content = response.choices[0].message.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            
            return json.loads(content.strip())
            
        except Exception as e:
            logger.error(f"Communication analysis failed: {e}")
            return {
                "gemeenschappelijke_themas": ["Analyse kon niet worden uitgevoerd"],
                "inconsistenties": [],
                "hoofdboodschappen": [],
                "communicatie_gaps": [],
                "aanbevelingen": []
            }
    
    def format_results(self, analysis_result: Dict) -> Dict:
        """Format results for display"""
        return {
            'show_strategic_communication': True,
            'communication_analysis': analysis_result.get('communication_analysis', {}),
            'summaries': {
                'doc1': analysis_result.get('doc1_summary', ''),
                'doc2': analysis_result.get('doc2_summary', ''),
                'doc3': analysis_result.get('doc3_summary', '')
            }
        }


class AnalysisFactory:
    """Factory voor het aanmaken van de juiste analyse strategie"""
    
    @staticmethod
    def create_strategy(mode: str, openai_client) -> AnalysisStrategy:
        """Maak de juiste strategie op basis van mode"""
        strategies = {
            'version_comparison': VersionComparisonStrategy,
            'actiz_position': ActiZPositionStrategy,
            'external_reaction': ExternalReactionStrategy,
            'strategic_communication': StrategicCommunicationStrategy
        }
        
        strategy_class = strategies.get(mode)
        if not strategy_class:
            raise ValueError(f"Unknown analysis mode: {mode}")
        
        return strategy_class(openai_client)