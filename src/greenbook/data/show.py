from attr import attrib
from typing import Optional, Sequence
from dataclasses import dataclass
from ruamel.yaml import YAML, yaml_object

from src.greenbook.data.consts import MAX_ENTRIES_PER_CONTESTANT
from src.greenbook.data.entries import Contestant

yaml = YAML()


@yaml_object(YAML)
@dataclass
class ShowClass:
    number: int = attrib(type=int)
    name: str = attrib(type=str)
    contestants: Sequence[Contestant] = attrib(type=Sequence[Contestant])
    first_place: Optional[Contestant] = attrib(type=Contestant, default=None)
    second_place: Optional[Contestant] = attrib(type=Contestant, default=None)
    third_place: Optional[Contestant] = attrib(type=Contestant, default=None)
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


@yaml_object(YAML)
@dataclass
class Show:
    classes: Sequence[ShowClass] = attrib(type=Sequence[ShowClass])

    def __post_init__(self):
        assert len(self.classes) == len(set(s.number for s in self.classes))

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
