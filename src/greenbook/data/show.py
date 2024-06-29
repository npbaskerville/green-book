from __future__ import annotations

from attr import attrib
from typing import Dict, Sequence
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


@yaml_object(YAML)
@dataclass
class ShowClass:
    class_id: str = attrib(type=str)
    name: str = attrib(type=str)
    contestants: Sequence[Contestant] = attrib(type=Sequence[Contestant])
    first_place: Sequence[Contestant] = attrib(type=Contestant, default=())
    second_place: Sequence[Contestant] = attrib(type=Contestant, default=())
    third_place: Sequence[Contestant] = attrib(type=Contestant, default=())
    commendations: Sequence[Contestant] = attrib(type=Sequence[Contestant], default=())

    def __post_init__(self):
        assert all(
            self.count_contestant(c) <= MAX_ENTRIES_PER_CONTESTANT for c in self.unique_contestants
        )

    def __contains__(self, contestant: Contestant) -> bool:
        return contestant in self.contestants

    def __len__(self) -> int:
        return len(self.contestants)

    def count_contestant(self, contestant: Contestant) -> int:
        return len([c for c in self.contestants if c == contestant])

    @property
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
        points = {}
        for contestants, points in zip(
            [
                self.first_place,
                self.second_place,
                self.third_place,
            ],
            [FIRST_PLACE_POINTS, SECOND_PLACE_POINTS, THIRD_PLACE_POINTS],
        ):
            for contestant in contestants:
                points[contestant] = points.get(contestant, 0) + points
        return points


@yaml_object(YAML)
class Show:
    def __init__(self, classes: Sequence[ShowClass]):
        self._classes = {s.class_id: s for s in classes}
        assert len(self._classes) == len(classes)

    @property
    def classes(self) -> Sequence[ShowClass]:
        return sorted(self._classes.values(), key=lambda s: s.number)

    def __contains__(self, contestant: Contestant) -> bool:
        return any(contestant in s for s in self.classes)

    @property
    def unique_contestants(self) -> Sequence[Contestant]:
        return sorted(set(c for s in self.classes for c in s.contestants))

    def count_contestant(self, contestant: Contestant) -> int:
        return len([c for s in self.classes for c in s.contestants if c == contestant])

    @property
    def total_entries(self) -> int:
        return sum(len(s) for s in self.classes)

    def class_lookup(self, class_id: str) -> ShowClass:
        return self._classes[class_id]

    def update_class(self, show_class: ShowClass) -> Show:
        classes = {key: value for key, value in self._classes.items() if key != show_class.class_id}
        classes[show_class.class_id] = show_class
        return Show(list(classes.values()))
