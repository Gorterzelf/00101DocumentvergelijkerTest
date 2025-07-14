"""
Analysis Strategies - Strategy Pattern Implementation
Elke analyse heeft zijn eigen geïsoleerde implementatie
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import logging
import json
import difflib  # Voor moved blocks detectie
from diff_match_patch import diff_match_patch  # Bovenaan geïmporteerd voor efficiëntie

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
        
        basic_comparison = self._compare_texts(text1, text2)
        ai_analysis = self._analyze_changes_with_ai(text1, text2, basic_comparison)
        
        result = {
            'mode': 'version_comparison',
            'basic_comparison': basic_comparison,
            'ai_analysis': ai_analysis,
            'doc1_summary': self.generate_summary(text1),
            'doc2_summary': self.generate_summary(text2)
        }
        
        return result
    
    def _compare_texts(self, text1: str, text2: str) -> Dict:
        """Basic text comparison with enhanced difference detection using diff-match-patch"""
        
        logger.info(f"Comparing texts - Doc1: {len(text1)} chars, Doc2: {len(text2)} chars")
        logger.info(f"Doc1 preview: {text1[:200]}...")
        logger.info(f"Doc2 preview: {text2[:200]}...")
        
        dmp = diff_match_patch()
        diffs = dmp.diff_main(text1, text2, True)  # True voor timeout check
        dmp.diff_cleanupSemantic(diffs)  # Maak diffs semantisch beter (groepeer veranderingen)
        
        # Bouw differences list
        differences = []
        i = 0
        while i < len(diffs):
            op, data = diffs[i]
            if op == 0:  # Equal, skip
                i += 1
                continue
            if op == -1 and i + 1 < len(diffs) and diffs[i+1][0] == 1:
                # Replace: consecutive delete + insert
                del_data = data.strip()
                add_op, add_data = diffs[i+1]
                differences.append({
                    'type': 'replace',
                    'original': del_data,
                    'modified': add_data.strip(),
                    'section_context': 'Paragraaf'  # Kan verbeterd met betere context
                })
                i += 2
            elif op == -1:
                # Delete
                differences.append({
                    'type': 'delete',
                    'original': data.strip(),
                    'modified': None,
                    'section_context': 'Paragraaf'
                })
                i += 1
            elif op == 1:
                # Add
                differences.append({
                    'type': 'add',
                    'original': None,
                    'modified': data.strip(),
                    'section_context': 'Paragraaf'
                })
                i += 1
        
        # Bereken added/removed voor compatibiliteit
        added_lines = [d['modified'] for d in differences if d['type'] == 'add' and d['modified']]
        removed_lines = [d['original'] for d in differences if d['type'] == 'delete' and d['original']]
        
        # Similarity
        similarity_ratio = 1 - (dmp.diff_levenshtein(diffs) / max(len(text1), len(text2))) if max(len(text1), len(text2)) > 0 else 0
        
        # Detect moved blocks with dynamic thresholds
        min_block_size = max(50, min(len(text1), len(text2)) // 20)  # Dynamisch: min 50, of 5% van kleinste tekst
        min_move_distance = max(100, min(len(text1), len(text2)) // 10)  # Min 100, of 10%
        
        moved_blocks = []
        sequence_matcher = difflib.SequenceMatcher(None, text1, text2)
        for tag, i1, i2, j1, j2 in sequence_matcher.get_opcodes():
            if tag == 'equal' and (i2 - i1) > min_block_size:
                block_text = text1[i1:i2].strip()
                if abs((i1 + i2)/2 - (j1 + j2)/2) > min_move_distance:
                    moved_blocks.append({
                        'type': 'move',
                        'text': block_text[:100] + '...' if len(block_text) > 100 else block_text,
                        'from_position': i1,
                        'to_position': j1,
                        'section_context': 'Paragraaf'
                    })
        
        # Add moved to differences
        differences.extend(moved_blocks)
        
        # Genereer HTML voor inline diff
        html_diff = dmp.diff_prettyHtml(diffs)
        
        total_changes = len(differences)
        
        logger.info(f"Found {len(added_lines)} additions, {len(removed_lines)} removals, {len(moved_blocks)} moves")
        logger.info(f"Similarity: {similarity_ratio*100:.2f}%")
        
        return {
            'differences': differences,  # Nieuwe structured list voor template
            'similarity_percentage': round(similarity_ratio * 100, 2),
            'added_content': added_lines[:10],
            'removed_content': removed_lines[:10],
            'moved_blocks': moved_blocks[:5],
            'total_changes': total_changes,
            'html_diff': html_diff,
            'diffs_raw': diffs  # Voor AI
        }
    
    def _analyze_changes_with_ai(self, text1: str, text2: str, basic_comparison: Dict) -> Dict:
        """AI analysis of changes, with semantic evaluation"""
        # Extract replace pairs for semantic analysis
        replace_pairs = []
        for diff in basic_comparison['differences']:
            if diff['type'] == 'replace':
                replace_pairs.append(f"Original: {diff['original']}\nNew: {diff['modified']}")
        
        replace_str = '\n\n'.join(replace_pairs) if replace_pairs else 'Geen replaces gevonden.'
        
        prompt = f"""
        Analyseer de verschillen tussen deze twee versies van een document.
        
        Versie 1 (preview):
        {text1[:2000]}...
        
        Versie 2 (preview):
        {text2[:2000]}...
        
        Basis verschillen (van diff tool):
        - Similarity: {basic_comparison['similarity_percentage']}%
        - Toegevoegd: {', '.join(basic_comparison['added_content'][:5]) or 'Geen'}
        - Verwijderd: {', '.join(basic_comparison['removed_content'][:5]) or 'Geen'}
        - Verplaatst: {len(basic_comparison['moved_blocks'])} blocks
        
        Replace pairs voor semantische analyse:
        {replace_str}
        
        Geef een analyse van:
        1. Belangrijkste inhoudelijke wijzigingen
        2. Verplaatste tekstblokken
        3. Subtiele betekenisverschillen
        4. Impact van de wijzigingen
        
        Voor elke replace pair, geef een similarity score (1-10, waar 10 = identiek betekenis, 1 = totaal verschillend) en explanation of de betekenis veranderd is.
        
        Antwoord ALLEEN in JSON formaat:
        {{
            "samenvatting": ["punt1", "punt2", ...],
            "toegevoegd": ["toevoeging1", "toevoeging2", ...],
            "verwijderd": ["verwijdering1", "verwijdering2", ...],
            "impact": ["impact1", "impact2", ...],
            "semantische_wijzigingen": [
                {{"original": "orig text", "new": "new text", "score": 8, "explanation": "Bijna gelijk, alleen herformuleerd."}},
                ...
            ]
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "Je bent een expert in documentvergelijking. Antwoord ALLEEN in JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            content = response.choices[0].message.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            
            ai_result = json.loads(content)
            return ai_result
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return {
                'samenvatting': [],
                'toegevoegd': [],
                'verwijderd': [],
                'impact': [],
                'semantische_wijzigingen': []
            }
    
    def format_results(self, analysis_result: Dict) -> Dict:
        """Format results for display"""
        formatted = {
            'mode': 'version_comparison',
            'show_version_comparison': True,
            'basic_comparison': analysis_result.get('basic_comparison', {}),
            'ai_analysis': analysis_result.get('ai_analysis', {}),
            'doc1_summary': analysis_result.get('doc1_summary', ''),
            'doc2_summary': analysis_result.get('doc2_summary', ''),
            'html_diff': analysis_result.get('basic_comparison', {}).get('html_diff', '')
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
        6. Thema vergelijking tussen ActiZ-visie en beleid
        
        Antwoord ALLEEN in JSON formaat:
        {{
            "ondersteuning_score": 7,
            "steunpunten": ["punt1", "punt2", ...],
            "kritiekpunten": ["kritiek1", "kritiek2", ...],
            "verbeteringen": ["verbetering1", "verbetering2", ...],
            "impact_zorgsector": "beschrijving van de impact",
            "thema_vergelijking": [
                {{"thema": "Thema1", "actiz_visie": "beschrijving", "beleid": "beschrijving", "analyse": "Overeenkomend"}}
            ]
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
            
            return json.loads(content)
            
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
            
            return json.loads(content)
            
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
            
            return json.loads(content)
            
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