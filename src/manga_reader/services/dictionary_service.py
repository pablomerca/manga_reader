"""Dictionary Service - Jamdict-backed noun definitions for popups."""

from dataclasses import dataclass
from typing import List, Optional, Literal, Union

from jamdict import Jamdict
from jamdict.jmdict import JMDEntry
from jamdict.kanjidic2 import Character
from jamdict.util import LookupResult

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


@dataclass
class DictionaryEntryFull:
    """Full dictionary entry for side panel display."""

    entry_id: Optional[int]
    kanji_forms: List[str]
    kana_forms: List[str]
    senses: List[DictionarySense]


@dataclass
class DictionaryLookupResult:
    """Result containing all entries for a lookup term."""

    lemma: str
    surface: str
    entries: List[DictionaryEntryFull]


@dataclass
class KanjiEntry:
    """Kanji dictionary entry from jamdict."""

    literal: str
    stroke_count: Optional[int]
    frequency: Optional[int]
    on_readings: List[str]
    kun_readings: List[str]
    meanings: List[str]


@dataclass
class BreadcrumbItem:
    """Breadcrumb trail item for dictionary panel navigation."""

    # TODO: refactor to use inheritance instead of Union
    type: Literal["word", "kanji"]
    content: Union[DictionaryLookupResult, KanjiEntry]
    label: str
    lemma: Optional[str]


class DictionaryService:
    """Wraps Jamdict to fetch definitions for nouns."""

    def __init__(self):
        self._jamdict = Jamdict()

    def lookup(self, lemma: str, surface: str) -> Optional[DictionaryEntry]:
        """Lookup a noun by lemma, falling back to surface form."""
        query = (lemma or surface).strip()
        if not query:
            return None

        try:
            result: LookupResult = self._jamdict.lookup(query)
        except Exception as exc:  # pragma: no cover - jamdict internals
            print(f"Jamdict lookup failed for '{query}': {exc}")
            return None

        if not result.entries:
            return None

        entry = result.entries[0]
        reading = entry.kana_forms[0].text if entry.kana_forms else query
        senses = self._build_senses(entry)

        return DictionaryEntry(surface=surface or lemma or query, reading=reading, senses=senses)

    def lookup_all_entries(self, lemma: str, surface: str) -> Optional[DictionaryLookupResult]:
        """Lookup all entries for a word using lemma or surface form."""
        query = (lemma or surface).strip()
        if not query:
            return None

        try:
            result: LookupResult = self._jamdict.lookup(query)
        except Exception as exc:  # pragma: no cover - jamdict internals
            print(f"Jamdict lookup failed for '{query}': {exc}")
            return None

        if not result.entries:
            return None

        entries: List[DictionaryEntryFull] = []
        for entry in result.entries:
            entry_id = int(entry.idseq) if entry.idseq else None
            kanji_forms = [form.text for form in entry.kanji_forms]
            kana_forms = [form.text for form in entry.kana_forms]
            senses = self._build_senses(entry)
            entries.append(
                DictionaryEntryFull(
                    entry_id=entry_id,
                    kanji_forms=kanji_forms,
                    kana_forms=kana_forms,
                    senses=senses,
                )
            )

        return DictionaryLookupResult(
            lemma=lemma or query, surface=surface or lemma or query, entries=entries
        )

    def lookup_kanji(self, kanji_char: str) -> Optional[KanjiEntry]:
        """Lookup kanji information from jamdict."""
        query: str = kanji_char.strip()
        if not query:
            return None

        try:
            result: LookupResult = self._jamdict.lookup(query)
        except Exception as exc:  # pragma: no cover - jamdict internals
            print(f"Jamdict lookup failed for '{query}': {exc}")
            return None

        if not result.chars:
            return None

        char: Character = result.chars[0]
        on_readings: List[str] = []
        kun_readings: List[str] = []
        meanings: List[str] = []

        for rm_group in char.rm_groups:
            for reading in rm_group.on_readings:
                on_readings.append(reading.value)
            for reading in rm_group.kun_readings:
                kun_readings.append(reading.value)
            for meaning in rm_group.meanings:
                if meaning.m_lang in ("", "en"):
                    meanings.append(meaning.value)


        return KanjiEntry(
            literal=char.literal,
            stroke_count=char.stroke_count,
            frequency= int(char.freq) if char.freq else None,
            on_readings=on_readings,
            kun_readings=kun_readings,
            meanings=meanings,
        )

    def _build_senses(self, entry: JMDEntry) -> List[DictionarySense]:
        """Build DictionarySense list from JMDEntry.senses."""
        senses: List[DictionarySense] = []
        for sense in entry.senses:
            glosses = [gloss.text for gloss in sense.gloss]
            # POS is a list of strings in jamdict
            pos = [str(p) for p in sense.pos]
            senses.append(DictionarySense(glosses=glosses, pos=pos))
        return senses
