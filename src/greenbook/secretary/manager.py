import re
import pandas as pd
import logging
from typing import Dict, List, Tuple, Optional, Sequence
from pathlib import Path
from ruamel.yaml import YAML

from greenbook.data.show import Show, Entry, ShowClass
from greenbook.data.entries import Contestant
from greenbook.render.labels import render_contestant_to_file
from greenbook.render.results import render_prizes, render_ranking, render_class_results
from greenbook.definitions.prices import ENTRY_COST, FREE_CLASSES
from greenbook.definitions.prizes import ALL_PRIZES, sort_contestant_by_points
from greenbook.definitions.classes import FLAT_CLASSES, CLASS_ID_TO_SECTION

_LOG = logging.getLogger(__name__)

yaml = YAML()


class Manager:
    def __init__(self, ledger_loc: Path):
        self._ledger_loc = ledger_loc
        self._show: Optional[Show] = None
        if self._ledger_loc.exists():
            with self._ledger_loc.open("r") as f:
                self._show = yaml.load(f)

    def allocate(self, contestants: Sequence[Contestant]):
        grouped_by_class: Dict[str, List[Contestant]] = {}
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
        first_contestants = [(self.lookup_contestant(class_id, c), c) for c in first]
        second_contestants = [(self.lookup_contestant(class_id, c), c) for c in second]
        third_contestants = [(self.lookup_contestant(class_id, c), c) for c in third]
        commendation_contestants = [(self.lookup_contestant(class_id, c), c) for c in commendations]
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

    def add_prize(self, prize: str, class_id: str, contestant_id: int):
        contestant = self.lookup_contestant(class_id, contestant_id)
        self._show = self._show.add_prize(prize=prize, class_id=class_id, contestant=contestant)
        with self._ledger_loc.open("w") as f:
            yaml.dump(self._show, f)
            _LOG.info(f"Added prize {prize} to contestant {contestant_id} in class {class_id}")

    def lookup_contestant(self, class_id: str, contestant_id: int) -> Contestant:
        return self._show.class_lookup(class_id).entry_lookup(contestant_id)

    def report_prizes(self) -> Sequence[str]:
        _LOG.info("Beginning prize report.")
        winning_strings = []
        for prize in ALL_PRIZES:
            winners = prize.winner(self._show)
            winner_str = ", ".join([str(w) for w in sorted(winners)])
            winning_strings.append(f"{prize}: {winner_str}")
            print(f"{prize}: {winner_str}")
        for prize in self._show.prizes:
            contestant, _, prize_name = prize
            winner_str = f"{prize_name}: {contestant.name}"
            winning_strings.append(winner_str)
            print(winner_str)
        _LOG.info("Completed prize report.")
        return winning_strings

    def to_csv(self, location: Path):
        """
        Create a dataframe of contestant_id x class. In each cell, the value
         is the name of the contestant corresponding to the contestant_id in the class,
          or None if that contestant id does not exist in that class.
        """
        all_contestant_ids = set()
        for contestant, entries in self.contestant_entries().items():
            all_contestant_ids.update([entry.contestant_id for entry in entries])
        all_contestant_ids = sorted(all_contestant_ids)
        data = {c: [None] * len(all_contestant_ids) for c in FLAT_CLASSES}
        df = pd.DataFrame(data, index=all_contestant_ids)
        for contestant, entries in self.contestant_entries().items():
            name = contestant.name
            for entry in entries:
                df.at[entry.contestant_id, entry.class_id] = name
        df.to_csv(location)
        _LOG.info(f"Exported contestant data to {location}")

    def report_ranking(self) -> Sequence[Tuple[Contestant, int]]:
        _LOG.info("Beginning ranking report.")
        ranking = sort_contestant_by_points(self._show)
        for contestant, points in ranking:
            print(f"{contestant}: {points}")
        _LOG.info("Completed ranking report.")
        return ranking

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

    def render_contestants(self, directory: Path):
        for contestant, entries in self.contestant_entries().items():
            price = 0.0
            for entry in entries:
                if CLASS_ID_TO_SECTION[entry.class_id] not in FREE_CLASSES:
                    price += ENTRY_COST
            price -= contestant.paid
            render_contestant_to_file(contestant.name, entries, directory, price=price)

    def render_final_report(self, directory: Path):
        """
        Produce 2 PDFs:
            1. A table per class in the show, giving the entry numbers, the names
            of the contestants and their results in the class.
            2. A list of all the prizes and their winners.
        """
        # 1. Produce a table per class in the show
        class_dfs: List[Tuple[str, str, pd.DataFrame]] = []
        for show_class in sorted(
            self._show.classes(), key=lambda c: int(re.sub(r"\D", "", c.class_id))
        ):
            class_df = show_class.to_df()
            class_dfs.append((show_class.class_id, show_class.name, class_df))
        render_class_results(class_dfs, directory)
        # 2. Produce a list of all the prizes and their winners
        render_prizes(self.report_prizes(), directory)
        # 3. produce overall points ranking
        render_ranking(self.report_ranking(), directory)
