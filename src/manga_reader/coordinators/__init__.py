"""Coordinators - Orchestration layer connecting UI with business logic."""

from .reader_controller import ReaderController
from .word_interaction_coordinator import WordInteractionCoordinator

__all__ = ["ReaderController", "WordInteractionCoordinator"]
