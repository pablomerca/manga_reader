"""Dictionary Service - Jamdict-backed noun definitions for popups."""

from dataclasses import dataclass
from typing import List, Optional

from jamdict import Jamdict


@dataclass
class DictionarySense:
    """Single sense of a dictionary entry."""

    glosses: List[str]
    pos: List[str]


@dataclass
class DictionaryEntry:
    """Lightweight dictionary entry for UI consumption."""

    surface: str
    reading: str
    senses: List[DictionarySense]


class DictionaryService:
    """Wraps Jamdict to fetch definitions for nouns."""

    def __init__(self):
        self._jamdict = Jamdict()

    def lookup(self, lemma: str | None, surface: str | None) -> Optional[DictionaryEntry]:
        """Lookup a noun by lemma, falling back to surface form."""
        query = (lemma or surface or "").strip()
        if not query:
            return None

        try:
            result = self._jamdict.lookup(query)
        except Exception as exc:  # pragma: no cover - jamdict internals
            print(f"Jamdict lookup failed for '{query}': {exc}")
            return None

        if not result.entries:
            return None

        entry = result.entries[0]
        reading = entry.kana_forms[0].text if entry.kana_forms else query

        senses: List[DictionarySense] = []
        for sense in entry.senses:
            glosses = [gloss.text for gloss in sense.gloss or []]
            pos = [pos.text if hasattr(pos, "text") else str(pos) for pos in (sense.pos or [])]
            senses.append(DictionarySense(glosses=glosses, pos=pos))

        return DictionaryEntry(surface=surface or lemma or query, reading=reading, senses=senses)
