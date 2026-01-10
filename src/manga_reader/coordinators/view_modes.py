"""View mode state objects for reader rendering and navigation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from manga_reader.core import MangaPage, MangaVolume


class ViewMode(ABC):
    """State interface for view modes (single vs double)."""

    name: str

    @abstractmethod
    def pages_to_render(
        self,
        volume: MangaVolume | None,
        current_page_number: int,
    ) -> List[MangaPage]:
        """Return the list of pages to render for the current index."""

    @abstractmethod
    def next_page_number(
        self,
        volume: MangaVolume | None,
        current_page_number: int,
    ) -> int:
        """Return the page index to navigate to when moving forward."""

    @abstractmethod
    def previous_page_number(
        self,
        volume: MangaVolume | None,
        current_page_number: int,
    ) -> int:
        """Return the page index to navigate to when moving backward."""

    def page_for_appearance(
        self,
        volume: MangaVolume | None,
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


class SinglePageMode(ViewMode):
    name = "single"

    def pages_to_render(
        self,
        volume: MangaVolume | None,
        current_page_number: int,
    ) -> List[MangaPage]:
        if volume is None:
            return []
        page = volume.get_page(current_page_number)
        return [page] if page else []

    def next_page_number(
        self,
        volume: MangaVolume | None,
        current_page_number: int,
    ) -> int:
        if volume is None:
            return current_page_number
        if current_page_number + 1 < volume.total_pages:
            return current_page_number + 1
        return current_page_number

    def previous_page_number(
        self,
        volume: MangaVolume | None,
        current_page_number: int,
    ) -> int:
        if volume is None:
            return current_page_number
        if current_page_number > 0:
            return current_page_number - 1
        return current_page_number


class DoublePageMode(ViewMode):
    name = "double"

    def pages_to_render(
        self,
        volume: MangaVolume | None,
        current_page_number: int,
    ) -> List[MangaPage]:
        if volume is None:
            return []
        current_page = volume.get_page(current_page_number)
        if not current_page:
            return []

        # Landscape pages render alone
        if not current_page.is_portrait():
            return [current_page]

        # Last page renders alone
        if current_page_number >= volume.total_pages - 1:
            return [current_page]

        next_page = volume.get_page(current_page_number + 1)
        if not next_page:
            return [current_page]

        # Pair portrait pages; otherwise render only current
        if next_page.is_portrait():
            return [current_page, next_page]
        return [current_page]

    def next_page_number(
        self,
        volume: MangaVolume | None,
        current_page_number: int,
    ) -> int:
        if volume is None:
            return current_page_number
        pages_displayed = len(self.pages_to_render(volume, current_page_number))
        next_index = current_page_number + pages_displayed
        if next_index < volume.total_pages:
            return next_index
        return current_page_number

    def previous_page_number(
        self,
        volume: MangaVolume | None,
        current_page_number: int,
    ) -> int:
        if volume is None:
            return current_page_number
        if current_page_number <= 0:
            return current_page_number

        # When possible, step back two pages if the previous spread was double portrait
        if current_page_number >= 2:
            prev_page = volume.get_page(current_page_number - 2)
            current_prev = volume.get_page(current_page_number - 1)
            if prev_page and current_prev and prev_page.is_portrait() and current_prev.is_portrait():
                return current_page_number - 2
        return current_page_number - 1

    def page_for_appearance(
        self,
        volume: MangaVolume | None,
        target_page_index: int,
        current_page_number: int,
    ) -> int:
        if volume is None:
            return current_page_number

        target_page = volume.get_page(target_page_index)
        if not target_page:
            return current_page_number

        if not target_page.is_portrait():
            return target_page_index

        # Place portrait page on the left of a spread when possible
        if target_page_index > 0:
            prev_page = volume.get_page(target_page_index - 1)
            if prev_page and prev_page.is_portrait():
                return target_page_index - 1
        return target_page_index

    def context_view_mode(self) -> ViewMode:
        return SINGLE_PAGE_MODE


SINGLE_PAGE_MODE = SinglePageMode()
DOUBLE_PAGE_MODE = DoublePageMode()


def create_view_mode(mode: str) -> ViewMode | None:
    """Factory returning the appropriate view mode state."""
    if mode == "double":
        return DOUBLE_PAGE_MODE
    if mode == "single":
        return SINGLE_PAGE_MODE
    return None
