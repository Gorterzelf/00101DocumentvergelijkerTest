"""
ActiZ Document Analyzer - Document Structure Analysis Service
V2.0 - KRITIEKE FIXES voor content verwijderingen en verplaatsingen
"""

import hashlib
import logging
import re
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any, Dict, List, Set, Tuple

logger = logging.getLogger(__name__)


class DocumentStructureAnalyzer:
    """
    Detecteert ALLE structurele wijzigingen: verwijderingen, verplaatsingen, herstructureringen
    KRITIEK voor beleidsadviseur gebruik
    """

    def __init__(self):
        # Patterns voor Nederlandse document structuren
        self.section_patterns = [
            r"^(?:\d+\.?\s+|[A-Z]+\.?\s+)([A-Z][^.\n]{10,100})",  # Hoofdstukken: "1. Titel" of "A. Titel"
            r"^(?:Artikel\s+\d+|Art\.\s*\d+)([^.\n]+)",  # Artikelen
            r"^(?:Paragraaf|§)\s*\d+\.?\d*\s*([^.\n]+)",  # Paragrafen
            r"^(?:Bijlage|Appendix|Annex)\s*[A-Z0-9]*\s*[:-]?\s*([^.\n]+)",  # Bijlagen
            r"^([A-Z][A-Z\s]{5,50})\s*$",  # ALL CAPS hoofdstuktitels
            r"^\*{1,3}\s*([A-Z][^*\n]{10,80})\s*\*{0,3}",  # Markdown headers met sterretjes
            r"^#{1,6}\s+([A-Z][^#\n]{5,80})",  # Markdown headers
            r"^([A-Z][a-z][^.\n]{15,80})(?:\s*:|\s*\n)",  # Titled secties met dubbele punt
        ]

        # Herkenning van belangrijke content types
        self.content_types = {
            "wetgeving": [r"artikel\s+\d+", r"wet\s+", r"regelgeving", r"verordening"],
            "beleid": [r"beleid", r"strategie", r"visie", r"missie", r"doelstelling"],
            "procedure": [r"procedure", r"proces", r"werkwijze", r"handleiding"],
            "financieel": [
                r"budget",
                r"kosten",
                r"tarief",
                r"euro",
                r"€",
                r"financiën",
            ],
            "compliance": [
                r"compliance",
                r"toezicht",
                r"igj",
                r"kwaliteit",
                r"certificering",
            ],
            "organisatie": [
                r"organisatie",
                r"structuur",
                r"rollen",
                r"verantwoordelijk",
            ],
        }

    def analyze_structure_changes(
        self, text1: str, text2: str, filename1: str, filename2: str
    ) -> Dict[str, Any]:
        """
        HOOFDFUNCTIE: Detecteer ALLE structurele wijzigingen
        """
        try:
            # 1. Basic document statistics
            stats = self._analyze_document_statistics(text1, text2)

            # 2. Extract document structures
            structure1 = self._extract_document_structure(text1, filename1)
            structure2 = self._extract_document_structure(text2, filename2)

            # 3. Detect content changes
            content_changes = self._detect_content_changes(structure1, structure2)

            # 4. Detect movements/relocations
            movements = self._detect_section_movements(structure1, structure2)

            # 5. Detect major deletions/additions
            major_changes = self._detect_major_structural_changes(
                structure1, structure2, stats
            )

            # 6. Create integrity assessment
            integrity_assessment = self._assess_document_integrity(
                stats, content_changes, movements, major_changes
            )

            # 7. Generate change summary
            change_summary = self._create_change_summary(
                content_changes, movements, major_changes, stats
            )

            return {
                "document_statistics": stats,
                "structure1": structure1,
                "structure2": structure2,
                "content_changes": content_changes,
                "movements": movements,
                "major_changes": major_changes,
                "integrity_assessment": integrity_assessment,
                "change_summary": change_summary,
                "critical_issues": self._identify_critical_issues(
                    stats, content_changes, major_changes
                ),
                "analysis_timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Structure analysis error: {str(e)}")
            return {"error": str(e), "analysis_timestamp": datetime.now().isoformat()}

    def _analyze_document_statistics(self, text1: str, text2: str) -> Dict[str, Any]:
        """
        Basis statistieken met RED FLAGS voor grote verschillen
        """
        stats1 = {
            "characters": len(text1),
            "words": len(text1.split()),
            "lines": len(text1.split("\n")),
            "paragraphs": len([p for p in text1.split("\n\n") if p.strip()]),
        }

        stats2 = {
            "characters": len(text2),
            "words": len(text2.split()),
            "lines": len(text2.split("\n")),
            "paragraphs": len([p for p in text2.split("\n\n") if p.strip()]),
        }

        # Calculate size differences
        char_diff_pct = (
            ((stats2["characters"] - stats1["characters"]) / stats1["characters"] * 100)
            if stats1["characters"] > 0
            else 0
        )
        word_diff_pct = (
            ((stats2["words"] - stats1["words"]) / stats1["words"] * 100)
            if stats1["words"] > 0
            else 0
        )

        # RED FLAGS voor grote wijzigingen
        red_flags = []
        if abs(char_diff_pct) > 50:
            red_flags.append(
                f"KRITIEK: {abs(char_diff_pct):.1f}% grootte wijziging - document substantieel gewijzigd"
            )
        if abs(word_diff_pct) > 40:
            red_flags.append(
                f"WAARSCHUWING: {abs(word_diff_pct):.1f}% woorden wijziging - mogelijke content verwijdering"
            )
        if stats2["words"] < stats1["words"] * 0.7:
            red_flags.append(f"KRITIEK: 30%+ content verwijdering gedetecteerd")

        return {
            "document1": stats1,
            "document2": stats2,
            "differences": {
                "characters": stats2["characters"] - stats1["characters"],
                "words": stats2["words"] - stats1["words"],
                "character_percentage": char_diff_pct,
                "word_percentage": word_diff_pct,
            },
            "red_flags": red_flags,
            "size_category": self._categorize_size_change(char_diff_pct, word_diff_pct),
        }

    def _extract_document_structure(self, text: str, filename: str) -> Dict[str, Any]:
        """
        Extract alle structurele elementen uit document
        """
        lines = text.split("\n")

        sections = []
        content_blocks = []
        current_section = None
        current_content = []

        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue

            # Check if line is a section header
            section_match = self._identify_section_header(line_stripped)
            if section_match:
                # Save previous section
                if current_section:
                    sections.append(
                        {
                            "title": current_section,
                            "start_line": current_section_start,
                            "end_line": i,
                            "content": "\n".join(current_content),
                            "content_hash": hashlib.md5(
                                "\n".join(current_content).encode()
                            ).hexdigest()[:8],
                            "word_count": len(" ".join(current_content).split()),
                        }
                    )

                # Start new section
                current_section = section_match
                current_section_start = i
                current_content = []
            else:
                current_content.append(line_stripped)

        # Add final section
        if current_section:
            sections.append(
                {
                    "title": current_section,
                    "start_line": current_section_start,
                    "end_line": len(lines),
                    "content": "\n".join(current_content),
                    "content_hash": hashlib.md5(
                        "\n".join(current_content).encode()
                    ).hexdigest()[:8],
                    "word_count": len(" ".join(current_content).split()),
                }
            )

        # Analyze content types
        content_analysis = self._analyze_content_types(text)

        return {
            "filename": filename,
            "total_sections": len(sections),
            "sections": sections,
            "content_analysis": content_analysis,
            "extraction_timestamp": datetime.now().isoformat(),
        }

    def _identify_section_header(self, line: str) -> str:
        """
        Identificeer of een regel een sectie header is
        """
        for pattern in self.section_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return match.group(1).strip() if match.lastindex else line.strip()

        # Check voor andere header indicatoren
        if len(line) < 100 and (
            line.isupper() or re.match(r"^[A-Z][^.]*[^.]$", line) or line.count(" ") < 8
        ):
            return line.strip()

        return None

    def _detect_content_changes(
        self, structure1: Dict, structure2: Dict
    ) -> Dict[str, Any]:
        """
        Detecteer toevoegingen, verwijderingen en wijzigingen in content
        """
        sections1 = {sec["title"]: sec for sec in structure1["sections"]}
        sections2 = {sec["title"]: sec for sec in structure2["sections"]}

        added_sections = []
        removed_sections = []
        modified_sections = []
        unchanged_sections = []

        # Check voor nieuwe secties
        for title, section in sections2.items():
            if title not in sections1:
                added_sections.append(section)
            else:
                # Check voor wijzigingen in bestaande secties
                old_section = sections1[title]
                if old_section["content_hash"] != section["content_hash"]:
                    similarity = SequenceMatcher(
                        None, old_section["content"], section["content"]
                    ).ratio()
                    modified_sections.append(
                        {
                            "title": title,
                            "old_section": old_section,
                            "new_section": section,
                            "similarity": similarity,
                            "word_change": section["word_count"]
                            - old_section["word_count"],
                        }
                    )
                else:
                    unchanged_sections.append(title)

        # Check voor verwijderde secties
        for title, section in sections1.items():
            if title not in sections2:
                removed_sections.append(section)

        return {
            "added_sections": added_sections,
            "removed_sections": removed_sections,
            "modified_sections": modified_sections,
            "unchanged_sections": unchanged_sections,
            "summary": {
                "additions": len(added_sections),
                "deletions": len(removed_sections),
                "modifications": len(modified_sections),
                "unchanged": len(unchanged_sections),
            },
        }

    def _detect_section_movements(
        self, structure1: Dict, structure2: Dict
    ) -> List[Dict]:
        """
        KRITIEK: Detecteer verplaatsingen van secties
        """
        movements = []

        sections1_by_hash = {sec["content_hash"]: sec for sec in structure1["sections"]}
        sections2_by_hash = {sec["content_hash"]: sec for sec in structure2["sections"]}

        # Find content that exists in both but at different positions
        for content_hash, sec2 in sections2_by_hash.items():
            if content_hash in sections1_by_hash:
                sec1 = sections1_by_hash[content_hash]

                # Find positions in their respective documents
                pos1 = next(
                    i
                    for i, s in enumerate(structure1["sections"])
                    if s["content_hash"] == content_hash
                )
                pos2 = next(
                    i
                    for i, s in enumerate(structure2["sections"])
                    if s["content_hash"] == content_hash
                )

                if pos1 != pos2:
                    movements.append(
                        {
                            "section_title": sec1["title"],
                            "content_hash": content_hash,
                            "old_position": pos1 + 1,  # 1-based for user display
                            "new_position": pos2 + 1,
                            "position_change": pos2 - pos1,
                            "movement_type": "moved_up"
                            if pos2 < pos1
                            else "moved_down",
                            "impact": "hoog" if abs(pos2 - pos1) > 3 else "gemiddeld",
                        }
                    )

        return sorted(movements, key=lambda x: abs(x["position_change"]), reverse=True)

    def _detect_major_structural_changes(
        self, structure1: Dict, structure2: Dict, stats: Dict
    ) -> Dict[str, Any]:
        """
        Detecteer grote structurele wijzigingen die problematisch kunnen zijn
        """
        major_changes = {
            "document_restructuring": False,
            "massive_content_loss": False,
            "section_count_change": False,
            "details": [],
        }

        # Check voor massive content loss (zoals jouw 85% reductie)
        if stats["differences"]["word_percentage"] < -50:
            major_changes["massive_content_loss"] = True
            major_changes["details"].append(
                {
                    "type": "massive_deletion",
                    "description": f"KRITIEK: {abs(stats['differences']['word_percentage']):.1f}% content verwijdering",
                    "severity": "hoog",
                    "recommendation": "Controleer of dit de juiste documenten zijn - mogelijk verkeerde versies geüpload",
                }
            )

        # Check voor section count changes
        section_diff = structure2["total_sections"] - structure1["total_sections"]
        if abs(section_diff) > 3:
            major_changes["section_count_change"] = True
            major_changes["details"].append(
                {
                    "type": "section_count_change",
                    "description": f"{'Toevoeging' if section_diff > 0 else 'Verwijdering'} van {abs(section_diff)} secties",
                    "severity": "hoog" if abs(section_diff) > 5 else "gemiddeld",
                    "recommendation": "Controleer document structuur wijzigingen",
                }
            )

        # Check voor document restructuring (veel verplaatsingen)
        if len(structure1["sections"]) > 0:
            content_hashes_1 = {sec["content_hash"] for sec in structure1["sections"]}
            content_hashes_2 = {sec["content_hash"] for sec in structure2["sections"]}
            preserved_content = len(content_hashes_1.intersection(content_hashes_2))
            preservation_ratio = (
                preserved_content / len(content_hashes_1)
                if len(content_hashes_1) > 0
                else 0
            )

            if preservation_ratio < 0.7:
                major_changes["document_restructuring"] = True
                major_changes["details"].append(
                    {
                        "type": "major_restructuring",
                        "description": f"Minder dan {preservation_ratio:.0%} content behouden - grote herstructurering",
                        "severity": "hoog",
                        "recommendation": "Document is substantieel geherstructureerd - handmatige review aanbevolen",
                    }
                )

        return major_changes

    def _assess_document_integrity(
        self, stats: Dict, content_changes: Dict, movements: List, major_changes: Dict
    ) -> Dict[str, Any]:
        """
        Beoordeel document integriteit en betrouwbaarheid van analyse
        """
        integrity_score = 100
        warnings = []

        # Size discrepancy penalty
        if abs(stats["differences"]["word_percentage"]) > 30:
            integrity_score -= 30
            warnings.append(
                f"Grote grootte discrepantie: {stats['differences']['word_percentage']:.1f}%"
            )

        # Major changes penalty
        if major_changes["massive_content_loss"]:
            integrity_score -= 40
            warnings.append("Massive content verwijdering gedetecteerd")

        if major_changes["document_restructuring"]:
            integrity_score -= 20
            warnings.append("Grote document herstructurering")

        # Movement complexity penalty
        if len(movements) > 5:
            integrity_score -= 15
            warnings.append(f"Veel verplaatsingen gedetecteerd: {len(movements)}")

        # Content changes penalty
        if content_changes["summary"]["deletions"] > 3:
            integrity_score -= 10
            warnings.append(
                f"Veel verwijderde secties: {content_changes['summary']['deletions']}"
            )

        integrity_level = (
            "hoog"
            if integrity_score >= 80
            else "gemiddeld"
            if integrity_score >= 60
            else "laag"
        )

        return {
            "integrity_score": max(0, integrity_score),
            "integrity_level": integrity_level,
            "warnings": warnings,
            "recommendation": self._get_integrity_recommendation(
                integrity_score, warnings
            ),
        }

    def _create_change_summary(
        self, content_changes: Dict, movements: List, major_changes: Dict, stats: Dict
    ) -> str:
        """
        Creëer een duidelijke samenvatting van alle wijzigingen
        """
        summary_parts = []

        # Basic statistics
        summary_parts.append(
            f"**Document grootte wijziging:** {stats['differences']['word_percentage']:+.1f}% woorden"
        )

        # Content changes
        if content_changes["summary"]["additions"] > 0:
            summary_parts.append(
                f"**{content_changes['summary']['additions']} secties toegevoegd**"
            )

        if content_changes["summary"]["deletions"] > 0:
            summary_parts.append(
                f"**{content_changes['summary']['deletions']} secties verwijderd**"
            )

        if content_changes["summary"]["modifications"] > 0:
            summary_parts.append(
                f"**{content_changes['summary']['modifications']} secties gewijzigd**"
            )

        # Movements
        if len(movements) > 0:
            summary_parts.append(f"**{len(movements)} secties verplaatst**")

        # Major issues
        if major_changes["massive_content_loss"]:
            summary_parts.append("**⚠️ KRITIEK: Massive content verwijdering**")

        if major_changes["document_restructuring"]:
            summary_parts.append("**⚠️ WAARSCHUWING: Grote document herstructurering**")

        return (
            "\n".join(summary_parts)
            if summary_parts
            else "Geen significante structurele wijzigingen gedetecteerd"
        )

    def _identify_critical_issues(
        self, stats: Dict, content_changes: Dict, major_changes: Dict
    ) -> List[Dict]:
        """
        Identificeer kritieke issues die directe aandacht nodig hebben
        """
        critical_issues = []

        # Red flags from statistics
        for flag in stats.get("red_flags", []):
            critical_issues.append(
                {
                    "type": "size_discrepancy",
                    "severity": "kritiek",
                    "message": flag,
                    "action_required": "Verificeer document versies",
                }
            )

        # Major content loss
        if major_changes.get("massive_content_loss"):
            critical_issues.append(
                {
                    "type": "content_loss",
                    "severity": "kritiek",
                    "message": "Massive content verwijdering kan wijzen op verkeerde document versies",
                    "action_required": "Handmatige verificatie vereist",
                }
            )

        # Many deletions
        if content_changes["summary"]["deletions"] > 5:
            critical_issues.append(
                {
                    "type": "many_deletions",
                    "severity": "hoog",
                    "message": f"{content_changes['summary']['deletions']} secties verwijderd - compliance impact mogelijk",
                    "action_required": "Review verwijderde content voor compliance impact",
                }
            )

        return critical_issues

    def _categorize_size_change(
        self, char_diff_pct: float, word_diff_pct: float
    ) -> str:
        """Categoriseer de grootte van wijzigingen"""
        avg_diff = abs((char_diff_pct + word_diff_pct) / 2)

        if avg_diff < 5:
            return "minimaal"
        elif avg_diff < 15:
            return "klein"
        elif avg_diff < 35:
            return "gemiddeld"
        elif avg_diff < 60:
            return "groot"
        else:
            return "extreem"

    def _analyze_content_types(self, text: str) -> Dict[str, int]:
        """Analyseer content types in document"""
        content_counts = {}

        for content_type, patterns in self.content_types.items():
            count = 0
            for pattern in patterns:
                count += len(re.findall(pattern, text, re.IGNORECASE))
            content_counts[content_type] = count

        return content_counts

    def _get_integrity_recommendation(self, score: int, warnings: List[str]) -> str:
        """Get recommendation based on integrity assessment"""
        if score >= 80:
            return "Document vergelijking betrouwbaar - normale analyse kan worden uitgevoerd"
        elif score >= 60:
            return "Waarschuwing: Document wijzigingen complex - extra aandacht bij interpretatie"
        else:
            return "KRITIEK: Document integriteit laag - handmatige verificatie sterk aanbevolen"
