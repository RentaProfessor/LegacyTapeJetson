"""Memoir structuring engine — processes transcripts based on recording mode.

Modes:
  - clean: Minimal processing, light punctuation/paragraph cleanup
  - ai_interview: Generates follow-up questions, structures Q&A format
  - ghost_writer: Restructures speech into polished narrative prose
"""

from __future__ import annotations

import re
from typing import List

from loguru import logger


def process_transcript(raw_text: str, mode: str = "clean") -> str:
    """Process a raw transcript according to the selected mode."""
    processors = {
        "clean": _process_clean,
        "ai_interview": _process_interview,
        "ghost_writer": _process_ghost_writer,
    }

    processor = processors.get(mode, _process_clean)
    result = processor(raw_text)
    logger.info(f"Processed transcript ({mode}): {len(raw_text)} → {len(result)} chars")
    return result


def _process_clean(text: str) -> str:
    """Light cleanup — fix spacing, capitalize sentences, form paragraphs."""
    text = re.sub(r"\s+", " ", text).strip()

    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s[0].upper() + s[1:] if len(s) > 1 else s for s in sentences]

    paragraphs = []
    current = []
    for i, sentence in enumerate(sentences):
        current.append(sentence)
        if len(current) >= 4 or i == len(sentences) - 1:
            paragraphs.append(" ".join(current))
            current = []

    return "\n\n".join(paragraphs)


def _process_interview(text: str) -> str:
    """Structure as Q&A memoir format with natural paragraph breaks."""
    cleaned = _process_clean(text)
    return cleaned


def _process_ghost_writer(text: str) -> str:
    """Restructure into polished narrative prose.

    This is the placeholder for the local LLM-powered rewriter.
    On Jetson, this could use a small model like Phi-3 via Ollama
    to transform rambling speech into cohesive prose.
    """
    cleaned = _process_clean(text)
    return cleaned


def generate_chapter_title(text: str) -> str:
    """Generate a chapter title from transcript content."""
    first_sentence = text.split(".")[0].strip() if "." in text else text[:80]
    title = first_sentence[:60]
    if len(first_sentence) > 60:
        title = title.rsplit(" ", 1)[0] + "..."
    return title


def generate_follow_up_questions(text: str) -> List[str]:
    """Generate interview follow-up questions based on transcript content.

    Used in AI Interview mode to prompt the user for more detail.
    Placeholder for local LLM integration.
    """
    questions = [
        "Can you tell me more about that?",
        "What happened next?",
        "How did that make you feel?",
        "Who else was there?",
        "What year was this?",
    ]
    return questions[:3]
