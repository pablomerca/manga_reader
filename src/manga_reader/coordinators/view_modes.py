"""View mode state objects for reader rendering and navigation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from manga_reader.core import MangaPage, MangaVolume


def _require_volume(volume: MangaVolume | None) -> MangaVolume:
    """Ensure a volume instance is provided, otherwise fail fast."""
    if volume is None:
        raise ValueError("Volume is required for view mode operations")
    return volume


class ViewMode(ABC):
    """State interface for view modes (single vs double)."""

    name: str

    @abstractmethod
    def pages_to_render(
        self,
        volume: MangaVolume,
        current_page_number: int,
    ) -> List[MangaPage]:
        """Return the list of pages to render for the current index."""

    @abstractmethod
    def next_page_number(
        self,
        volume: MangaVolume,
        current_page_number: int,
    ) -> int:
        """Return the page index to navigate to when moving forward."""

    @abstractmethod
    def previous_page_number(
        self,
        volume: MangaVolume,
        current_page_number: int,
    ) -> int:
        """Return the page index to navigate to when moving backward."""

    def page_for_appearance(
        self,
        volume: MangaVolume,
        target_page_index: int,
        current_page_number: int,
    ) -> int:
        """Return the page index to set when navigating to a specific appearance."""
        return target_page_index

    def page_for_context(
        self,
        current_page_number: int,
        last_clicked_page_index: int | None,
    ) -> int:
        """Return the page that should be shown when entering context view."""
        return last_clicked_page_index if last_clicked_page_index is not None else current_page_number

    def context_view_mode(self) -> ViewMode:
        """Return the view mode to use while viewing context (defaults to self)."""
        return self

    @abstractmethod
    def toggle(self) -> ViewMode:
        """Return the toggled view mode (single <-> double)."""


class SinglePageMode(ViewMode):
    name = "single"

    def pages_to_render(
        self,
        volume: MangaVolume,
        current_page_number: int,
    ) -> List[MangaPage]:
        vol = _require_volume(volume)
        page = vol.get_page(current_page_number)
        return [page]

    def next_page_number(
        self,
        volume: MangaVolume,
        current_page_number: int,
    ) -> int:
        vol = _require_volume(volume)
        if current_page_number + 1 < vol.total_pages:
            return current_page_number + 1
        return current_page_number

    def previous_page_number(
        self,
        volume: MangaVolume,
        current_page_number: int,
    ) -> int:
        vol = _require_volume(volume)
        if current_page_number > 0:
            return current_page_number - 1
        return current_page_number

    def toggle(self) -> ViewMode:
        """Toggle from single to double page mode."""
        return DOUBLE_PAGE_MODE

class DoublePageMode(ViewMode):
    name = "double"

    def pages_to_render(
        self,
        volume: MangaVolume,
        current_page_number: int,
    ) -> List[MangaPage]:
        vol = _require_volume(volume)
        current_page = vol.get_page(current_page_number)

        # Landscape pages render alone
        if not current_page.is_portrait():
            return [current_page]

        # Last page renders alone
        if current_page_number >= vol.total_pages - 1:
            return [current_page]

        next_page = vol.get_page(current_page_number + 1)

        # Pair portrait pages; otherwise render only current
        if next_page.is_portrait():
            return [current_page, next_page]
        return [current_page]

    def next_page_number(
        self,
        volume: MangaVolume,
        current_page_number: int,
    ) -> int:

        vol = _require_volume(volume)
        pages_displayed = len(self.pages_to_render(vol, current_page_number))
        next_index = current_page_number + pages_displayed
        if next_index < vol.total_pages:
            return next_index
        return current_page_number

    def previous_page_number(
        self,
        volume: MangaVolume,
        current_page_number: int,
    ) -> int:

        vol = _require_volume(volume)
        if current_page_number <= 0:
            return current_page_number

        # When possible, step back two pages if the previous spread was double portrait
        if current_page_number >= 2:
            if not (0 <= current_page_number - 2 < vol.total_pages):
                return current_page_number - 1
            prev_page = vol.get_page(current_page_number - 2)
            current_prev = vol.get_page(current_page_number - 1)
            if prev_page.is_portrait() and current_prev.is_portrait():
                return current_page_number - 2
        return current_page_number - 1

    def page_for_appearance(
        self,
        volume: MangaVolume,
        target_page_index: int,
        current_page_number: int,
    ) -> int:
        vol = _require_volume(volume)

        if not (0 <= target_page_index < vol.total_pages):
            return current_page_number

        target_page = vol.get_page(target_page_index)

        if not target_page.is_portrait():
            return target_page_index

        # Place portrait page on the left of a spread when possible
        if target_page_index > 0 and (0 <= target_page_index - 1 < vol.total_pages):
            prev_page = vol.get_page(target_page_index - 1)
            if prev_page.is_portrait():
                return target_page_index - 1
        return target_page_index

    def context_view_mode(self) -> ViewMode:
        return SINGLE_PAGE_MODE

    def toggle(self) -> ViewMode:
        """Toggle from double to single page mode."""
        return SINGLE_PAGE_MODE

SINGLE_PAGE_MODE = SinglePageMode()
DOUBLE_PAGE_MODE = DoublePageMode()


def create_view_mode(mode: str) -> ViewMode:
    """Factory returning the appropriate view mode state.

    Raises:
        ValueError: If an unknown mode name is provided.
    """
    if mode == "double":
        return DOUBLE_PAGE_MODE
    if mode == "single":
        return SINGLE_PAGE_MODE
    raise ValueError(f"Unknown view mode: {mode}")
