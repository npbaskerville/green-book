import pandas as pd
import logging
from typing import List
from pathlib import Path
from ruamel.yaml import YAML

from greenbook.data.entries import Contestant
from greenbook.definitions.classes import FLAT_CLASSES

yaml = YAML()

_LOG = logging.getLogger(__name__)


class Registrar:
    """
    Manage the registration of contestants and their entries.
    """

    def __init__(self, ledger_loc: Path):
        self._contestants: List[Contestant] = []
        self._ledger_loc = ledger_loc
        if self._ledger_loc.exists():
            with open(self._ledger_loc, "r") as f:
                self._contestants: List[Contestant] = list(yaml.load(f))
                _LOG.info(f"loaded {len(self._contestants)} contestants from {self._ledger_loc}")

        self._name_to_contestant = {c.name: c for c in self._contestants}
        assert len(self._contestants) == len(self._name_to_contestant)

    def register(self, contestant: Contestant, allow_update: bool = False):
        if contestant in self._contestants:
            _LOG.warning(f"contestant {contestant} already registered")
            return
        if contestant.name in self._name_to_contestant:
            if not allow_update:
                raise ValueError(f"contestant with name {contestant.name} already registered")
            else:
                _LOG.warning(f"updating contestant {contestant.name}")
                existing_entry = self._name_to_contestant[contestant.name]
                classes = [*existing_entry.classes, *contestant.classes]
                updated_contestant = Contestant(classes=classes, name=contestant.name)
                index = self._contestants.index(existing_entry)
                self._contestants[index] = updated_contestant
                _LOG.info(
                    f"Added {len(contestant.classes)} entries to contestant {contestant.name}"
                )
        else:
            self._contestants.append(contestant)
            self._name_to_contestant[contestant.name] = contestant
            _LOG.info(
                f"registered contestant {contestant.name} with {len(contestant.classes)} entries"
            )
        with open(self._ledger_loc, "w") as f:
            yaml.dump(self._contestants, f)

    def contestants(self) -> List[Contestant]:
        return self._contestants

    def to_csv(self, location: Path):
        """
        Create a dataframe of contestant x class giving the number of entries
         of each contestant in each class.
        """
        data = {"contestant": [], **{c: [] for c in FLAT_CLASSES}}
        for contestant in self._contestants:
            data["contestant"].append(contestant.name)
            for class_id in FLAT_CLASSES:
                data[class_id].append(contestant.classes.count(class_id))
        df = pd.DataFrame(data)
        df.to_csv(location, index=False)
        _LOG.info(f"exported contestant data to {location}")
