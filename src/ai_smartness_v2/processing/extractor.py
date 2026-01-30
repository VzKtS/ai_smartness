"""
LLM Extractor - Semantic extraction via LLM.

Extracts structured information from raw content using Claude API.
Different prompts per source type (prompt, read, write, task, fetch).
"""

import json
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional, Literal
from pathlib import Path


SourceType = Literal["prompt", "read", "write", "task", "fetch", "response"]


@dataclass
class Extraction:
    """Result of LLM extraction."""
    source_type: SourceType
    title: str  # Short subject title (3-5 words, NO action verbs)
    intent: str  # What the user/system intended
    summary: str  # Brief summary of the content (1-2 sentences)
    subjects: List[str]  # Main subjects/topics
    questions: List[str]  # Questions asked or implied
    decisions: List[str]  # Decisions made or proposed
    key_concepts: List[str]  # Important concepts/terms
    context_hints: List[str]  # Hints about broader context
    confidence: float = 0.8
    raw_response: str = ""

    def to_dict(self) -> dict:
        return {
            "source_type": self.source_type,
            "title": self.title,
            "intent": self.intent,
            "summary": self.summary,
            "subjects": self.subjects,
            "questions": self.questions,
            "decisions": self.decisions,
            "key_concepts": self.key_concepts,
            "context_hints": self.context_hints,
            "confidence": self.confidence
        }


# Extraction prompts per source type
# IMPORTANT: "title" must be the SUBJECT (noun), not an action (verb)
# BAD: "Analyser le protocole P2P" / GOOD: "Protocole P2P handshake"
EXTRACTION_PROMPTS = {
    "prompt": """Analyse ce message utilisateur et extrait les informations structurées.

MESSAGE:
{content}

IMPORTANT pour "title": donne le SUJET en 3-5 mots, PAS une action.
- MAUVAIS: "Analyser le fichier de config"
- BON: "Configuration système"

Réponds en JSON strict:
{{
  "title": "Sujet principal en 3-5 mots (nom, pas verbe)",
  "summary": "Résumé bref du contenu en 1-2 phrases",
  "intent": "L'intention principale de l'utilisateur (1 phrase)",
  "subjects": ["sujet1", "sujet2"],
  "questions": ["question posée ou implicite"],
  "decisions": [],
  "key_concepts": ["concept technique important"],
  "context_hints": ["indice sur le contexte plus large"]
}}

Sois concis. Pas de texte hors du JSON.""",

    "read": """Analyse ce contenu de fichier lu et extrait les informations structurées.

FICHIER: {file_path}
CONTENU (extrait):
{content}

IMPORTANT pour "title": donne le SUJET en 3-5 mots, PAS une action.
- MAUVAIS: "Lire le fichier de handshake"
- BON: "P2P Handshake Protocol"

Réponds en JSON strict:
{{
  "title": "Sujet principal du fichier en 3-5 mots",
  "summary": "Ce que fait ce fichier/module en 1-2 phrases",
  "intent": "Pourquoi ce fichier est probablement lu (1 phrase)",
  "subjects": ["sujet principal du fichier"],
  "questions": [],
  "decisions": [],
  "key_concepts": ["concept/fonction/classe importante"],
  "context_hints": ["rôle probable dans le projet"]
}}

Sois concis. Pas de texte hors du JSON.""",

    "write": """Analyse cette modification de fichier et extrait les informations structurées.

FICHIER: {file_path}
CHANGEMENTS:
{content}

IMPORTANT pour "title": donne le SUJET en 3-5 mots, PAS une action.
- MAUVAIS: "Modifier la gestion des erreurs"
- BON: "Error handling system"

Réponds en JSON strict:
{{
  "title": "Sujet de la modification en 3-5 mots",
  "summary": "Ce qui a été modifié et le résultat en 1-2 phrases",
  "intent": "Ce qui a été modifié et pourquoi (1 phrase)",
  "subjects": ["sujet de la modification"],
  "questions": [],
  "decisions": ["décision impliquée par cette modification"],
  "key_concepts": ["concept ajouté/modifié"],
  "context_hints": ["impact probable"]
}}

Sois concis. Pas de texte hors du JSON.""",

    "task": """Analyse ce résultat de sous-agent et extrait les informations structurées.

RÉSULTAT:
{content}

IMPORTANT pour "title": donne le SUJET en 3-5 mots, PAS une action.
- MAUVAIS: "Analyser l'architecture du projet"
- BON: "Architecture projet"

Réponds en JSON strict:
{{
  "title": "Sujet traité en 3-5 mots",
  "summary": "Ce que le sous-agent a accompli et découvert en 1-2 phrases",
  "intent": "Ce que le sous-agent a accompli (1 phrase)",
  "subjects": ["sujet traité"],
  "questions": ["question ouverte si applicable"],
  "decisions": ["décision prise par le sous-agent"],
  "key_concepts": ["découverte ou conclusion importante"],
  "context_hints": ["implication pour la suite"]
}}

Sois concis. Pas de texte hors du JSON.""",

    "fetch": """Analyse ce contenu web récupéré et extrait les informations structurées.

URL: {url}
CONTENU:
{content}

IMPORTANT pour "title": donne le SUJET en 3-5 mots, PAS une action.
- MAUVAIS: "Rechercher la documentation API"
- BON: "API Documentation"

Réponds en JSON strict:
{{
  "title": "Sujet de la page en 3-5 mots",
  "summary": "Informations clés trouvées sur la page en 1-2 phrases",
  "intent": "Information recherchée (1 phrase)",
  "subjects": ["sujet de la recherche"],
  "questions": [],
  "decisions": [],
  "key_concepts": ["information clé trouvée"],
  "context_hints": ["utilité pour le projet"]
}}

Sois concis. Pas de texte hors du JSON.""",

    "response": """Analyse cette réponse de l'assistant et extrait les informations structurées.

RÉPONSE:
{content}

IMPORTANT pour "title": donne le SUJET en 3-5 mots, PAS une action.
- MAUVAIS: "Proposer une solution de cache"
- BON: "Cache system design"

Réponds en JSON strict:
{{
  "title": "Sujet traité en 3-5 mots",
  "summary": "Ce que l'assistant a proposé/expliqué en 1-2 phrases",
  "intent": "Ce que l'assistant a fait/proposé (1 phrase)",
  "subjects": ["sujet traité"],
  "questions": ["question posée à l'utilisateur"],
  "decisions": ["décision prise ou proposée"],
  "key_concepts": ["concept clé mentionné"],
  "context_hints": ["prochaine étape probable"]
}}

Sois concis. Pas de texte hors du JSON."""
}


# Topic noise words to filter out
TOPIC_NOISE = {
    "message", "contenu", "analyse", "fichier", "code",
    "json", "response", "result", "data", "type", "value",
    "function", "class", "method", "variable", "parameter",
    "unknown", "extraction", "heuristique", "intent", "subjects",
    "questions", "decisions", "context", "hints", "concepts"
}

# Prefixes to strip from topics
TOPIC_PREFIXES_TO_STRIP = ["MESSAGE:", "CONTENU:", "FICHIER:", "RÉSULTAT:", "URL:"]


class LLMExtractor:
    """
    Extracts structured information from content using LLM.

    Uses Claude CLI with absolute path for reliable extraction.
    """

    def __init__(
        self,
        model: str = "claude-haiku-3-5-20250620",
        claude_cli_path: Optional[str] = None
    ):
        """
        Initialize extractor.

        Args:
            model: Claude model to use for extraction
            claude_cli_path: Absolute path to claude CLI (from config)
        """
        self.model = model
        self.claude_cli_path = claude_cli_path or "claude"  # Fallback to PATH lookup

    def extract(
        self,
        content: str,
        source_type: SourceType,
        file_path: Optional[str] = None,
        url: Optional[str] = None
    ) -> Extraction:
        """
        Extract structured information from content.

        Args:
            content: Raw content to analyze
            source_type: Type of source (prompt, read, write, etc.)
            file_path: Optional file path for read/write sources
            url: Optional URL for fetch sources

        Returns:
            Extraction with structured information
        """
        # Get appropriate prompt template
        prompt_template = EXTRACTION_PROMPTS.get(source_type, EXTRACTION_PROMPTS["prompt"])

        # Format prompt with content
        prompt = prompt_template.format(
            content=content[:3000],  # Limit content length
            file_path=file_path or "unknown",
            url=url or "unknown"
        )

        # Call LLM
        try:
            response = self._call_llm(prompt)
            return self._parse_response(response, source_type, content)
        except Exception as e:
            # Return minimal extraction on error
            return Extraction(
                source_type=source_type,
                title="Extraction error",
                summary="",
                intent=f"Extraction failed: {e}",
                subjects=[],
                questions=[],
                decisions=[],
                key_concepts=[],
                context_hints=[],
                confidence=0.0,
                raw_response=str(e)
            )

    def _call_llm(self, prompt: str) -> str:
        """
        Call Claude LLM with prompt.

        Uses subprocess to call claude CLI with absolute path.
        Falls back to default model if specified model not found.
        Falls back to heuristic extraction if CLI not available.
        """
        import logging
        logger = logging.getLogger(__name__)

        try:
            # Build command - include model if specified
            if self.model:
                cmd = [self.claude_cli_path, "--model", self.model, "--print", prompt]
            else:
                cmd = [self.claude_cli_path, "--print", prompt]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                return result.stdout.strip()

            # Check if it's a model not found error (404)
            if "not_found" in result.stderr or "404" in result.stderr:
                logger.warning(f"Model '{self.model}' not found, retrying with default model")
                # Retry without --model (use session default)
                result = subprocess.run(
                    [self.claude_cli_path, "--print", prompt],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    return result.stdout.strip()

            # CLI failed for other reason
            logger.warning(f"Claude CLI failed (code {result.returncode}): {result.stderr[:200]}")
            return self._fallback_extraction(prompt)

        except FileNotFoundError:
            logger.warning(f"Claude CLI not found at: {self.claude_cli_path}")
            return self._fallback_extraction(prompt)
        except subprocess.TimeoutExpired:
            return '{"error": "timeout"}'
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'

    def _fallback_extraction(self, prompt: str) -> str:
        """
        Fallback extraction when LLM not available.

        Uses basic heuristics to extract information.
        """
        # Extract what we can from the content in the prompt
        content_start = prompt.find("CONTENU:") or prompt.find("MESSAGE:") or prompt.find("RÉSULTAT:")
        if content_start == -1:
            content_start = 0

        content = prompt[content_start:content_start + 500]

        # Basic keyword extraction
        words = content.split()
        significant_words = [w for w in words if len(w) > 4 and w[0].isupper()][:5]

        # Build title from significant words (noun-based)
        title = ' '.join(significant_words[:3]) if significant_words else "Unknown topic"

        # Build summary from first sentence
        first_sentence = content.split('.')[0].strip() if '.' in content else content[:100]
        summary = first_sentence[:150] if first_sentence else ""

        return json.dumps({
            "title": title,
            "summary": summary,
            "intent": "Extraction heuristique (LLM non disponible)",
            "subjects": significant_words[:2] if significant_words else ["unknown"],
            "questions": [],
            "decisions": [],
            "key_concepts": significant_words[2:4] if len(significant_words) > 2 else [],
            "context_hints": []
        })

    def _clean_topics(self, topics: List[str]) -> List[str]:
        """
        Clean topics by removing noise.

        Args:
            topics: List of raw topics

        Returns:
            Cleaned list of topics
        """
        cleaned = []
        for topic in topics:
            if not topic or not isinstance(topic, str):
                continue

            # Strip prefixes
            for prefix in TOPIC_PREFIXES_TO_STRIP:
                if topic.upper().startswith(prefix):
                    topic = topic[len(prefix):].strip()

            # Normalize
            topic = topic.strip().lower()

            # Filter noise
            if topic in TOPIC_NOISE:
                continue
            if len(topic) < 3:
                continue
            if not any(c.isalpha() for c in topic):
                continue

            # Remove quotes
            topic = topic.strip('"\'')

            if topic and topic not in cleaned:
                cleaned.append(topic)

        return cleaned

    def _parse_response(self, response: str, source_type: SourceType, original_content: str = "") -> Extraction:
        """
        Parse LLM response into Extraction.

        Args:
            response: Raw LLM response
            source_type: Source type for the extraction
            original_content: Original content for fallback summary

        Returns:
            Parsed Extraction
        """
        try:
            # Try to find JSON in response
            # Sometimes LLM adds text before/after JSON
            json_start = response.find('{')
            json_end = response.rfind('}') + 1

            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)

                # Clean topics
                subjects = self._clean_topics(data.get("subjects", []))
                key_concepts = self._clean_topics(data.get("key_concepts", []))

                # Get title, fallback to first subject if not provided
                title = data.get("title", "")
                if not title and subjects:
                    title = subjects[0].title()

                # Get summary, generate fallback if empty
                summary = data.get("summary", "")
                if not summary and original_content:
                    # Generate summary from first sentence of content
                    first_sentence = original_content.split('.')[0].strip()
                    summary = first_sentence[:150] if first_sentence else ""

                return Extraction(
                    source_type=source_type,
                    title=title,
                    summary=summary,
                    intent=data.get("intent", ""),
                    subjects=subjects,
                    questions=data.get("questions", []),
                    decisions=data.get("decisions", []),
                    key_concepts=key_concepts,
                    context_hints=data.get("context_hints", []),
                    confidence=0.8,
                    raw_response=response
                )
        except json.JSONDecodeError:
            pass

        # Parsing failed, generate fallback summary
        fallback_summary = ""
        if original_content:
            first_sentence = original_content.split('.')[0].strip()
            fallback_summary = first_sentence[:150] if first_sentence else ""

        return Extraction(
            source_type=source_type,
            title="Unknown",
            summary=fallback_summary,
            intent="Parsing failed",
            subjects=[],
            questions=[],
            decisions=[],
            key_concepts=[],
            context_hints=[],
            confidence=0.3,
            raw_response=response
        )


def extract_title_from_content(content: str, max_length: int = 60) -> str:
    """
    Extract a meaningful title from content.

    Uses heuristics, not LLM (for speed).

    Args:
        content: Content to extract title from
        max_length: Maximum title length

    Returns:
        Extracted title
    """
    # Clean content
    content = content.strip()

    # If starts with a question, use it
    if content.endswith('?'):
        first_line = content.split('\n')[0]
        if len(first_line) <= max_length:
            return first_line

    # Extract first meaningful sentence
    sentences = content.replace('\n', ' ').split('.')
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) > 10 and len(sentence) <= max_length:
            return sentence

    # Extract significant words
    words = content.split()
    significant = []
    for word in words:
        word = word.strip('.,;:!?"\'()[]{}')
        if len(word) > 3 and word[0].isupper():
            significant.append(word)
        if len(' '.join(significant)) > max_length - 10:
            break

    if significant:
        return ' '.join(significant[:5])

    # Fallback: first N characters
    if len(content) > max_length:
        return content[:max_length - 3] + "..."
    return content
