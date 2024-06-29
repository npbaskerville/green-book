import logging
from typing import Dict, Sequence
from pathlib import Path
from ruamel.yaml import YAML

from greenbook.data.show import Entry, ShowClass
from greenbook.data.entries import Contestant

_LOG = logging.getLogger(__name__)

yaml = YAML()


class Manager:
    def __init__(self, ledger_loc: Path):
        self._ledger_loc = ledger_loc

    def allocate(self, contestants: Sequence[Contestant], allow_reallocate: bool = False):
        for contestant in contestants:
            for show_class in contestant.classes:
                raise NotImplementedError

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
