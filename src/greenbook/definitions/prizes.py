from abc import ABC, abstractmethod
from typing import Dict, Tuple, Sequence

from greenbook.data.show import Show
from greenbook.data.entries import Contestant
from greenbook.definitions.classes import CLASSES


# region abstract prizes
class BasePrize(ABC):
    def __init__(self, name: str):
        self._name = name

    @abstractmethod
    def winner(self, show: Show) -> Contestant:
        pass

    def __str__(self) -> str:
        return self._name


class HighestPointsInClasses(BasePrize):
    def __init__(self, name: str, class_ids: Sequence[str]):
        self._class_ids = class_ids
        super().__init__(name)

    def winner(self, show: Show) -> Sequence[Contestant]:
        points: Dict[Contestant, int] = {}
        for class_id in self._class_ids:
            show_class = show.class_lookup(class_id)
            if show_class is None:
                continue
            for contestant, point in show_class.points().items():
                points[contestant] = points.get(contestant, 0) + point
        if not points:
            return []
        max_score = max(points.values())
        return [contestant for contestant, point in points.items() if point == max_score]


class HighestPointInSection(HighestPointsInClasses):
    def __init__(self, name: str, section: str):
        class_ids = [class_id for class_id, _ in CLASSES[section]]
        super().__init__(name, class_ids)


# endregion


# region utils
def sort_contestant_by_points(show: Show) -> Sequence[Tuple[Contestant, int]]:
    points: Dict[Contestant, int] = {}
    for show_class in show.classes():
        for contestant, point in show_class.points().items():
            points[contestant] = points.get(contestant, 0) + point
    return sorted(points.items(), key=lambda x: x[1], reverse=True)


# endregion


# region concrete prizes
class WilliamTrowPooleTrophy(HighestPointInSection):
    def __init__(self):
        super().__init__(section="H", name="William Trow-Poole Trophy")


class JoanHollierPlate(HighestPointInSection):
    def __init__(self):
        super().__init__(section="F", name="Joan Hollier Plate")


class MBShield(BasePrize):
    """
    Highest points overall.
    """

    def __init__(self):
        super().__init__(name="M & B Shield")

    def winner(self, show: Show) -> Sequence[Contestant]:
        sorted_contestants = sort_contestant_by_points(show)
        max_score = sorted_contestants[0][1]
        winners = [contestant for contestant, point in sorted_contestants if point == max_score]
        all_scores = [point for _, point in sorted_contestants]
        # sanity check
        assert all(score <= max_score for score in all_scores)
        return winners


class HaroldHerbertCup(HighestPointsInClasses):
    def __init__(self):
        super().__init__(
            name="Harold Herbert Cup",
            class_ids=["25B", "25C"],
        )


class MrsAnnPorterCup(HighestPointsInClasses):
    def __init__(self):
        super().__init__(name="Mrs Ann Porter Cup", class_ids=["16"])


class ButlerTrophy(HighestPointInSection):
    def __init__(self):
        super().__init__(name="Butler Trophy", section="E")


class CourtHouseSalver(HighestPointInSection):
    def __init__(self):
        super().__init__(name="Court House Salver", section="B")


class ChildrensCup(HighestPointInSection):
    def __init__(self):
        super().__init__(
            name="Children's Cup",
            section="J",
        )


ALL_PRIZES = [
    WilliamTrowPooleTrophy(),
    JoanHollierPlate(),
    MBShield(),
    MrsAnnPorterCup(),
    ButlerTrophy(),
    CourtHouseSalver(),
    ChildrensCup(),
]
# endregion
