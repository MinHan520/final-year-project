import re
from .base import BaseAnalyzer, DiagnosticReport, Finding
import statistics

# ------------------------------------------------------------------
# EXPANDED DICTIONARIES: Tuned for modern LLM outputs (GPT-4, Claude 3)
# ------------------------------------------------------------------

AI_CLICHES = [
    # Classic AI Signatures
    r"\bdelve(?:s|d|ing)?\b(?:\s+into)?",
    r"\bdive(?:s|d|ing)?\b(?:\s+into)?",
    r"\btestament to\b",
    r"\btapestry of\b",
    r"\bbeacon of\b",
    r"\bmyriad of\b",
    r"\blandscape of\b",
    
    # The "Pseudo-Profound" AI Voice
    r"\bnavigating the\b",
    r"\bin today's rapidly evolving\b",
    r"\bin an ever-evolving\b",
    r"\bmultifaceted\b",
    r"\bholistic approach\b",
    r"\bparadigm shift\b",
    r"\bsymphony of\b",
    r"\bcatalyst for\b",
    r"\bunleash(?:ing)? the power of\b",
    
    # The "Helpful Assistant" Framing
    r"\bit is (?:important|crucial|imperative|worth) to note\b",
    r"\bit's worth noting\b",
    r"\bsheds light on\b",
    r"\bfoster(?:s|ing)? a sense of\b",
    r"\bresonate(?:s|d)? with\b",
    r"\bseamless(?:ly)? integrate(?:d)?\b",
    r"\bnot merely a\b",
    r"\bnot just a\b",
    
    # AI Conclusions
    r"\bin conclusion\b",
    r"\bto summarize\b",
    r"\bultimately\b",
    r"\ball things considered\b",
    r"\bserves as a reminder\b"
]

TRANSITION_PHRASES = [
    r"\bhowever\b",
    r"\bmoreover\b",
    r"\bfurthermore\b",
    r"\badditionally\b",
    r"\bin addition\b",
    r"\bon the other hand\b",
    r"\bconsequently\b",
    r"\bnevertheless\b",
    r"\bnonetheless\b",
    r"\bas a result\b",
    r"\bin contrast\b",
    r"\bconversely\b",
    r"\bin essence\b",
    r"\bto reiterate\b"
]

HEDGING_PHRASES = [
    r"\bgenerally\b",
    r"\btypically\b",
    r"\busually\b",
    r"\bin many cases\b",
    r"\boften\b",
    r"\bmany experts\b",
    r"\bstudies show\b",
    r"\bresearch suggests\b",
    r"\bit is widely\b",
    r"\bit is generally\b",
    r"\bcan be seen as\b",
    r"\bit could be argued\b",
    r"\bwhile opinions vary\b",
    r"\bthere is no one-size-fits-all\b",
    r"\ba complex issue\b"
]

class TextAnalyzer(BaseAnalyzer):
    """Analyzes text for common AI-generation patterns, burstiness, and RLHF traits."""

    def analyze(self, text: str) -> DiagnosticReport:
        report = DiagnosticReport(media_type="text")

        if len(text.strip()) < 50:
            report.findings.append(Finding(
                category="Note",
                description="Text is too short for reliable analysis. Please provide at least 150 words.",
                severity="low",
            ))
            return report

        report.findings.extend(self._check_cliches(text))
        report.findings.extend(self._check_structure(text))
        report.findings.extend(self._check_transitions(text))
        report.findings.extend(self._check_hedging(text))
        report.findings.extend(self._check_nuance(text))
        return report

    # ------------------------------------------------------------------
    # AI cliché detection
    # ------------------------------------------------------------------
    def _check_cliches(self, text: str) -> list[Finding]:
        findings = []
        matches = []

        for pattern in AI_CLICHES:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                matches.append(m.group().lower())

        if matches:
            phrase_counts = {phrase: matches.count(phrase) for phrase in set(matches)}
            top_phrases = sorted(phrase_counts.items(), key=lambda x: -x[1])[:5]
            phrase_list = ", ".join(f'"{p}" ({c}x)' if c > 1 else f'"{p}"' for p, c in top_phrases)

            # Sensitivity adjustment: AI text often has a high density of these
            severity = "high" if len(matches) >= 4 else ("medium" if len(matches) >= 2 else "low")
            findings.append(Finding(
                category="Linguistic Clichés (RLHF Artifacts)",
                description=(
                    f"Identified {len(matches)} instance(s) of highly characteristic AI phrasing: "
                    f"{phrase_list}. Large Language Models are heavily fine-tuned using Reinforcement "
                    f"Learning (RLHF), which causes them to over-rely on this specific, overly-polished "
                    f"'assistant' vocabulary compared to natural human writing."
                ),
                severity=severity,
            ))

        return findings

    # ------------------------------------------------------------------
    # Structural monotony (Lack of "Burstiness")
    # ------------------------------------------------------------------
    def _check_structure(self, text: str) -> list[Finding]:
        findings = []

        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        sentences = [s for s in sentences if len(s.split()) > 3] # Ignore tiny fragments

        if len(sentences) < 4:
            return findings

        lengths = [len(s.split()) for s in sentences]
        mean_len = statistics.mean(lengths)
        std_len = statistics.stdev(lengths) if len(lengths) > 1 else 0

        # Human text has high "burstiness" (mixing 5-word sentences with 30-word sentences).
        # AI text averages out around 15-20 words per sentence with very low variance.
        if std_len < 4.5 and mean_len > 10:
            findings.append(Finding(
                category="Structural Monotony (Low Burstiness)",
                description=(
                    f"The sentence structure exhibits abnormally low variance (Mean length: {mean_len:.1f} words, "
                    f"Standard Deviation: {std_len:.1f}). Human writers naturally display high 'burstiness'—mixing "
                    f"short, punchy sentences with long, complex ones. This uniform, rhythmic pacing is a "
                    f"strong algorithmic signature."
                ),
                severity="high",
            ))

        # Check for list/bullet overuse (AI's organizational crutch)
        list_items = re.findall(r'^\s*[-•*]\s', text, re.MULTILINE)
        numbered_items = re.findall(r'^\s*\d+[.)]\s', text, re.MULTILINE)
        total_list = len(list_items) + len(numbered_items)
        
        if total_list >= 3 and total_list / max(len(sentences), 1) > 0.2:
            findings.append(Finding(
                category="Formatting Artifacts",
                description=(
                    f"Detected heavy reliance on lists ({total_list} list items). Generative models "
                    f"frequently default to bulleted or numbered structures as an organizational crutch "
                    f"to fulfill prompts requiring detailed explanations."
                ),
                severity="medium",
            ))

        return findings

    # ------------------------------------------------------------------
    # Transition word overuse (Over-signaling)
    # ------------------------------------------------------------------
    def _check_transitions(self, text: str) -> list[Finding]:
        findings = []
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        sentences = [s for s in sentences if len(s.split()) > 3]

        if len(sentences) < 4:
            return findings

        found_transitions = []
        for pattern in TRANSITION_PHRASES:
            matches = re.findall(r'^' + pattern + r'|,?\s+' + pattern + r'\b', text, re.IGNORECASE | re.MULTILINE)
            if matches:
                found_transitions.extend([m.strip(', \n').lower() for m in matches])

        transition_count = len(found_transitions)
        ratio = transition_count / len(sentences)
        
        if ratio > 0.25:
            examples = ", ".join(f'"{t}"' for t in set(found_transitions[:4]))
            findings.append(Finding(
                category="Transitional Over-Signaling",
                description=(
                    f"Excessive use of mechanical transition words ({transition_count} instances in {len(sentences)} "
                    f"sentences). Examples found: {examples}. AI models use these connectives aggressively "
                    f"to create an illusion of logical flow, leading to text that feels rigidly engineered."
                ),
                severity="medium",
            ))

        return findings

    # ------------------------------------------------------------------
    # Hedging language detection
    # ------------------------------------------------------------------
    def _check_hedging(self, text: str) -> list[Finding]:
        findings = []
        matches = []

        for pattern in HEDGING_PHRASES:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                matches.append(m.group().lower())

        if len(matches) >= 3:
            phrase_counts = {phrase: matches.count(phrase) for phrase in set(matches)}
            top_phrases = sorted(phrase_counts.items(), key=lambda x: -x[1])[:5]
            phrase_list = ", ".join(f'"{p}" ({c}x)' if c > 1 else f'"{p}"' for p, c in top_phrases)

            severity = "high" if len(matches) >= 6 else ("medium" if len(matches) >= 3 else "low")
            findings.append(Finding(
                category="Hedging & Qualifier Overuse",
                description=(
                    f"Detected {len(matches)} hedging/qualifying phrase(s): {phrase_list}. "
                    f"AI models are trained via RLHF to avoid making definitive claims, resulting in "
                    f"an overabundance of cautious, non-committal language that rarely appears at this "
                    f"density in natural human writing."
                ),
                severity=severity,
            ))

        return findings

    # ------------------------------------------------------------------
    # Lack of genuine nuance / personality
    # ------------------------------------------------------------------
    def _check_nuance(self, text: str) -> list[Finding]:
        findings = []

        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        sentences = [s for s in sentences if len(s.split()) > 3]

        if len(sentences) < 4:
            return findings

        # Check for "both sides" equivocation pattern
        equivocation_patterns = [
            r"\bon one hand\b.*\bon the other hand\b",
            r"\bwhile .+ (?:is|are) .+, (?:it|they) also\b",
            r"\bhas (?:both|its) .+ and .+\b",
            r"\bpros and cons\b",
            r"\badvantages and disadvantages\b",
            r"\bbenefits and (?:drawbacks|challenges)\b",
        ]

        equivocation_count = 0
        for pattern in equivocation_patterns:
            equivocation_count += len(re.findall(pattern, text, re.IGNORECASE))

        if equivocation_count >= 2:
            findings.append(Finding(
                category="Formulaic Balance (False Nuance)",
                description=(
                    f"Detected {equivocation_count} instances of formulaic 'both sides' equivocation. "
                    f"AI models are fine-tuned to present balanced, non-controversial perspectives, "
                    f"often producing a mechanical 'on one hand / on the other hand' structure that "
                    f"substitutes genuine critical analysis with surface-level balance."
                ),
                severity="medium",
            ))

        # Check for lack of first-person experience / personal voice
        first_person = len(re.findall(r'\bI\b(?!\s+(?:think|believe|feel|would))', text))
        personal_anecdote = len(re.findall(
            r'\b(?:I remember|in my experience|I once|I personally|I noticed|I felt|I saw)\b',
            text, re.IGNORECASE
        ))

        opinion_markers = len(re.findall(
            r'\b(?:I think|I believe|I feel|in my opinion|from my perspective)\b',
            text, re.IGNORECASE
        ))

        total_personal = first_person + personal_anecdote + opinion_markers
        words = len(text.split())

        if words > 150 and total_personal == 0:
            findings.append(Finding(
                category="Absence of Personal Voice",
                description=(
                    f"In {words} words of text, no first-person experiences, personal anecdotes, "
                    f"or subjective opinion markers were detected. AI-generated text tends to adopt "
                    f"a detached, encyclopedic tone—presenting information as objective fact rather "
                    f"than through the lens of lived experience, which is a hallmark of human writing."
                ),
                severity="medium",
            ))

        return findings