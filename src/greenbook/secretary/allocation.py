import logging
from typing import Sequence
from pathlib import Path
from ruamel.yaml import YAML

from src.greenbook.data.show import ShowClass
from src.greenbook.data.entries import Contestant

_LOG = logging.getLogger(__name__)

yaml = YAML()


class Allocator:
    def __init__(self, ledger_loc: Path):
        self._ledger_loc = ledger_loc

    def allocate(self, contestants: Sequence[Contestant]) -> Sequence[ShowClass]:
        for contestant in contestants:
            for show_class in contestant.classes:
                pass
