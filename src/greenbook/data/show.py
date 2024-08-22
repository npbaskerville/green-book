from __future__ import annotations

import pandas as pd
from attr import attrib
from typing import Dict, Optional, Sequence
from dataclasses import dataclass
from ruamel.yaml import YAML, yaml_object

from greenbook.data.consts import MAX_ENTRIES_PER_CONTESTANT
from greenbook.data.entries import Contestant
from greenbook.definitions.point import (
    FIRST_PLACE_POINTS,
    THIRD_PLACE_POINTS,
    SECOND_PLACE_POINTS,
)

yaml = YAML()


@dataclass
class Entry:
    contestant_id: int = attrib(type=int)
    class_id: str = attrib(type=str)
    name: str = attrib(type=str)


@yaml_object(yaml)
@dataclass
class ShowClass:
    class_id: str = attrib(type=str)
    name: str = attrib(type=str)
    contestants: Sequence[Contestant] = attrib(type=Sequence[Contestant])
    first_place: Sequence[Contestant] = attrib(type=Sequence[Contestant])
    second_place: Sequence[Contestant] = attrib(type=Sequence[Contestant])
    third_place: Sequence[Contestant] = attrib(type=Sequence[Contestant])
    commendations: Sequence[Contestant] = attrib(type=Sequence[Contestant])

    def __post_init__(self):
        assert all(
            self.count_contestant(c) <= MAX_ENTRIES_PER_CONTESTANT
            for c in self.unique_contestants()
        )

    def __contains__(self, contestant: Contestant) -> bool:
        return contestant in self.contestants

    def __len__(self) -> int:
        return len(self.contestants)

    def count_contestant(self, contestant: Contestant) -> int:
        return len([c for c in self.contestants if c == contestant])

    def unique_contestants(self) -> Sequence[Contestant]:
        return sorted(set(self.contestants))

    def entry_lookup(self, number: int) -> Contestant:
        assert number > 0
        return self.contestants[number - 1]

    def add_judgments(
        self,
        first: Sequence[Contestant],
        second: Sequence[Contestant],
        third: Sequence[Contestant],
        commendations: Sequence[Contestant],
    ) -> ShowClass:
        return ShowClass(
            class_id=self.class_id,
            name=self.name,
            contestants=self.contestants,
            first_place=first,
            second_place=second,
            third_place=third,
            commendations=commendations,
        )

    def points(self) -> Dict[Contestant:int]:
        contestant_points = {}
        for contestants, points in zip(
            [
                self.first_place,
                self.second_place,
                self.third_place,
            ],
            [FIRST_PLACE_POINTS, SECOND_PLACE_POINTS, THIRD_PLACE_POINTS],
        ):
            for contestant in contestants:
                contestant_points[contestant] = contestant_points.get(contestant, 0) + points
        return contestant_points

    def __str__(self) -> str:
        return f"{self.class_id}: {self.name} ({len(self.contestants)} contestants)"

    def to_df(self) -> pd.DataFrame:
        """
        Produce and return a DataFrame with columns: contestant_id, name, place (if any)
        """
        df_data = {"name": [], "entry": [], "place": []}
        for i, contestant in enumerate(self.contestants):
            df_data["name"].append(contestant.name)
            df_data["entry"].append(i + 1)
            if contestant in self.first_place:
                df_data["place"].append(1)
            elif contestant in self.second_place:
                df_data["place"].append(2)
            elif contestant in self.third_place:
                df_data["place"].append(3)
            elif contestant in self.commendations:
                df_data["place"].append(42)
            else:
                df_data["place"].append(None)
        df = pd.DataFrame(df_data)
        # change place to int type
        df["place"] = df["place"].astype("Int64")
        df.sort_values("place", inplace=True)
        return df


@yaml_object(yaml)
class Show:
    def __init__(self, classes: Sequence[ShowClass]):
        self._classes = {s.class_id: s for s in classes}
        assert len(self._classes) == len(classes)

    def classes(self) -> Sequence[ShowClass]:
        return sorted(self._classes.values(), key=lambda s: s.class_id)

    def __contains__(self, contestant: Contestant) -> bool:
        return any(contestant in s for s in self.classes())

    def unique_contestants(self) -> Sequence[Contestant]:
        return sorted(set(c for s in self.classes() for c in s.contestants))

    def count_contestant(self, contestant: Contestant) -> int:
        return len([c for s in self.classes() for c in s.contestants if c == contestant])

    def total_entries(self) -> int:
        return sum(len(s) for s in self.classes())

    def class_lookup(self, class_id: str) -> Optional[ShowClass]:
        return self._classes.get(class_id)

    def update_class(self, show_class: ShowClass) -> Show:
        classes = {key: value for key, value in self._classes.items() if key != show_class.class_id}
        classes[show_class.class_id] = show_class
        return Show(list(classes.values()))

    def contestant_entries(
        self,
    ) -> Dict[Contestant, Sequence[Entry]]:
        entries = {}
        for show_class in self.classes():
            for number, contestant in enumerate(show_class.contestants):
                entries[contestant] = entries.get(contestant, []) + [
                    Entry(
                        contestant_id=number + 1, class_id=show_class.class_id, name=show_class.name
                    )
                ]
        return entries
