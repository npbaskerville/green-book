from collections.abc import Iterable

from greenbook.definitions.classes import CLASS_ID_TO_SECTION

ENTRY_COST = 0.1  # 10p
FREE_CLASSES = ("J",)


def entry_fee(class_ids: Iterable[str]) -> float:
    """The fee for entering the given classes (one item per entry)."""
    return ENTRY_COST * sum(CLASS_ID_TO_SECTION[c] not in FREE_CLASSES for c in class_ids)
