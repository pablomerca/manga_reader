"""Coordinators - Orchestration layer connecting UI with business logic."""

from .reader_controller import ReaderController
from .word_interaction_coordinator import WordInteractionCoordinator
from .context_panel_coordinator import ContextPanelCoordinator

__all__ = ["ReaderController", "WordInteractionCoordinator", "ContextPanelCoordinator"]
