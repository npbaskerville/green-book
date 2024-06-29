import logging
from typing import Dict, Sequence
from pathlib import Path
from ruamel.yaml import YAML

from greenbook.data.show import Show, Entry, ShowClass
from greenbook.data.entries import Contestant
from greenbook.definitions.classes import FLAT_CLASSES

_LOG = logging.getLogger(__name__)

yaml = YAML()


class Manager:
    def __init__(self, ledger_loc: Path):
        self._ledger_loc = ledger_loc

    def allocate(self, contestants: Sequence[Contestant], allow_reallocate: bool = False):
        if self._ledger_loc.exists() and not allow_reallocate:
            raise ValueError("Ledger already exists, use allow_reallocate=True to overwrite")
        grouped_by_class = {}
        for contestant in contestants:
            for class_id in contestant.classes:
                if class_id not in grouped_by_class:
                    grouped_by_class[class_id] = []
                grouped_by_class[class_id].append(contestant)
        classes = [
            ShowClass(
                class_id=class_id,
                name=FLAT_CLASSES[class_id],
                contestants=grouped_by_class[class_id],
            )
            for class_id in grouped_by_class
        ]
        show = Show(classes=classes)
        with self._ledger_loc.open("w") as f:
            yaml.dump(show, f)
            _LOG.info(f"Allocated contestants to classes in {self._ledger_loc}")

    def add_judgment(
        self,
        class_id: str,
        first: Sequence[int],
        second: Sequence[int],
        third: Sequence[int],
        commendations: Sequence[int],
    ):
        # first_contestants = [self.lookup_contestant(class_id, c) for c in first]
        # second_contestants = [self.lookup_contestant(class_id, c) for c in second]
        # third_contestants = [self.lookup_contestant(class_id, c) for c in third]
        # commendation_contestants = [self.lookup_contestant(class_id, c) for c in commendations]
        raise NotImplementedError

    def lookup_contestant(self, class_id: str, contestant_id: int) -> Contestant:
        raise NotImplementedError

    def report_prizes(self):
        raise NotImplementedError

    def to_csv(self, location: Path):
        raise NotImplementedError

    def report_ranking(self):
        raise NotImplementedError

    def report_class(self, class_id: str) -> ShowClass:
        raise NotImplementedError

    def contestant_entries(self) -> Dict[Contestant, Sequence[Entry]]:
        raise NotImplementedError
