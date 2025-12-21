"""
Agents模块
"""

from .organizer_agent import OrganizerAgent
from .theorist_tool import theorist_speak
from .practitioner_tool import practitioner_speak
from .skeptic_tool import skeptic_speak
from .rewriter_tools import rewrite_if_needed
from .model_client import llm_theorist, llm_practitioner, llm_skeptic, llm_organizer

__all__ = [
    'OrganizerAgent',
    'theorist_speak',
    'practitioner_tool',
    'skeptic_tool',
    'rewrite_if_needed',
    'llm_theorist',
    'llm_practitioner',
    'llm_skeptic',
    'llm_organizer'
]