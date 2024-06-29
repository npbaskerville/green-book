import logging
from typing import Dict, Optional, Sequence
from pathlib import Path
from ruamel.yaml import YAML

from greenbook.data.show import Show, Entry, ShowClass
from greenbook.data.entries import Contestant
from greenbook.definitions.prizes import ALL_PRIZES, sort_contestant_by_points
from greenbook.definitions.classes import FLAT_CLASSES

_LOG = logging.getLogger(__name__)

yaml = YAML()


class Manager:
    def __init__(self, ledger_loc: Path):
        self._ledger_loc = ledger_loc
        self._show: Optional[Show] = None

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
                first_place=[],
                second_place=[],
                third_place=[],
                commendations=[],
            )
            for class_id in grouped_by_class
        ]
        self._show = Show(classes=classes)
        with self._ledger_loc.open("w") as f:
            yaml.dump(self._show, f)
            _LOG.info(f"Allocated contestants to classes in {self._ledger_loc}")

    def add_judgment(
        self,
        class_id: str,
        first: Sequence[int],
        second: Sequence[int],
        third: Sequence[int],
        commendations: Sequence[int],
    ):
        show_class = self._show.class_lookup(class_id)
        first_contestants = [self.lookup_contestant(class_id, c) for c in first]
        second_contestants = [self.lookup_contestant(class_id, c) for c in second]
        third_contestants = [self.lookup_contestant(class_id, c) for c in third]
        commendation_contestants = [self.lookup_contestant(class_id, c) for c in commendations]
        show_class = show_class.add_judgments(
            first=first_contestants,
            second=second_contestants,
            third=third_contestants,
            commendations=commendation_contestants,
        )
        self._show = self._show.update_class(show_class)
        with self._ledger_loc.open("w") as f:
            yaml.dump(self._show, f)
            _LOG.info(f"Added judgments to class {class_id}")

    def lookup_contestant(self, class_id: str, contestant_id: int) -> Contestant:
        return self._show.class_lookup(class_id).entry_lookup(contestant_id)

    def report_prizes(self):
        _LOG.info("Beginning prize report.")
        for prize in ALL_PRIZES:
            winners = prize.winner(self._show)
            winner_str = ", ".join([w for w in sorted(winners)])
            print(f"{prize}: {winner_str}")
        _LOG.info("Completed prize report.")

    def to_csv(self, location: Path):
        raise NotImplementedError

    def report_ranking(self):
        _LOG.info("Beginning ranking report.")
        for contestant, points in sort_contestant_by_points(self._show):
            print(f"{contestant}: {points}")
        _LOG.info("Completed ranking report.")

    def report_class(self, class_id: str) -> ShowClass:
        show_class = self._show.class_lookup(class_id)
        _LOG.info(f"Reporting on class {show_class}")
        _LOG.info(f"First: {' '.join([str(c) for c in show_class.first_place])}")
        _LOG.info(f"Second: {' '.join([str(c) for c in show_class.second_place])}")
        _LOG.info(f"Third: {' '.join([str(c) for c in show_class.third_place])}")
        _LOG.info(f"Commendations: {' '.join([str(c) for c in show_class.commendations])}")
        return show_class

    def contestant_entries(self) -> Dict[Contestant, Sequence[Entry]]:
        return self._show.contestant_entries()
