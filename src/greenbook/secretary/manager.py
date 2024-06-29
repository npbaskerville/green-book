import logging
from typing import Sequence
from pathlib import Path
from ruamel.yaml import YAML

from greenbook.data.entries import Contestant

_LOG = logging.getLogger(__name__)

yaml = YAML()


class Manager:
    def __init__(self, ledger_loc: Path):
        self._ledger_loc = ledger_loc

    def allocate(self, contestants: Sequence[Contestant], allow_reallocate: bool = False):
        for contestant in contestants:
            for show_class in contestant.classes:
                pass

    def add_judgment(
        self,
        show_number: int,
        first: Sequence[Contestant],
        second: Sequence[Contestant],
        third: Sequence[Contestant],
        commendations: Sequence[Contestant],
    ):
        pass

    def lookup_contestant(self, class_number: int, contestant_id: int) -> Contestant:
        pass

    def report_prizes(self):
        pass

    def to_csv(self, location: Path):
        pass

    def report_rankings(self):
        pass
