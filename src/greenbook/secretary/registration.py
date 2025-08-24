import pandas as pd
import numpy as np
import logging
from typing import List, Dict, Tuple
from pathlib import Path
from ruamel.yaml import YAML

from greenbook.data.entries import Contestant, DeletedContestant, ContestantData, AllocatedContestant
from greenbook.definitions import MAX_ENTRIES_PER_CLASS
from greenbook.definitions.classes import FLAT_CLASSES, CLASS_IDS

yaml = YAML()

_LOG = logging.getLogger(__name__)


LEDGER_NAME_COL = "contestant"
PAID_COL = "paid"
LEDGER_COLS = tuple([LEDGER_NAME_COL, PAID_COL, *CLASS_IDS])


def get_contestant_entries(ledger: pd.DataFrame) -> Dict[str, ContestantData]:
    entry_num_ledger = ledger.drop(LEDGER_NAME_COL, axis=1).cumsum(axis=0)
    entry_num_ledger = pd.concat([ledger[[LEDGER_NAME_COL]], entry_num_ledger], axis=1)
    grouped_entries: Dict[str, ContestantData] = {}
    for name, df in entry_num_ledger.groupby(LEDGER_NAME_COL):
        paid = float(df[PAID_COL].values[-1])
        entries_df = df.drop([LEDGER_NAME_COL, PAID_COL], axis=1).dropna(axis=1, how='all').fillna(0)
        entries_df = entries_df.loc[:, (entries_df > 0).values.any(axis=0)]
        grouped_entries[str(name)] = ContestantData(
            entries_df=entries_df.astype(int), paid=paid
        )
    return grouped_entries


def validate_ledger(ledger: pd.DataFrame):
    if (ledger[PAID_COL] < 0).any():
        ValueError("Can't accept negative payments.")
    contestant_entries = get_contestant_entries(ledger)
    for contestant, entries in contestant_entries.items():
        n_entries_per_class = (entries.entries_df > 0).sum(axis=0)
        non_zero_entries = n_entries_per_class[n_entries_per_class > 0]
        if (non_zero_entries > MAX_ENTRIES_PER_CLASS).any():
            raise ValueError(f"{contestant=} has more than {MAX_ENTRIES_PER_CLASS} entries in some classes. Entries: "
                             f"{non_zero_entries}.")


class Registrar:
    """
    Manage the registration of contestants and their entries.
    """

    def __init__(self, ledger_loc: Path):
        self._ledger = pd.DataFrame(columns=LEDGER_COLS)
        self._ledger_loc = ledger_loc
        if self._ledger_loc.exists():
            with open(self._ledger_loc, "r") as f:
                self._ledger = pd.read_csv(self._ledger_loc, index_col=0)
                _LOG.info(f"loaded {len(self._ledger)} rows from {self._ledger_loc}")
                validate_ledger(self._ledger)

    def register(self, contestant: Contestant):
        entry_data = np.full((len(contestant.classes), len(CLASS_IDS)), fill_value=np.nan)
        entry_indices = [CLASS_IDS.index(c) for c in contestant.classes]
        for idx, _class in enumerate(contestant.classes):
            entry_data[idx, CLASS_IDS.index(_class)] = 1
        entries = pd.DataFrame(
            data=entry_data,
            columns=CLASS_IDS,
        )
        paid_col = [0.0]*(len(entries) - 1)
        paid_col.append(contestant.paid)
        entries_meta = pd.DataFrame({
            LEDGER_NAME_COL: [contestant.name] * len(entries),
            PAID_COL: paid_col,
        })
        contestant_df = pd.concat([entries_meta, entries], axis=1)
        assert tuple(contestant_df.columns) == LEDGER_COLS
        new_ledger = pd.concat([self._ledger, contestant_df], axis=0)
        validate_ledger(new_ledger)
        self._ledger = new_ledger
        self._ledger.to_csv(self._ledger_loc)

    def contestants(self) -> List[AllocatedContestant]:
        contestants = []
        for name, data in get_contestant_entries(self._ledger).items():
            classes = []
            for col in data.entries_df.columns:
                n_entries = (data.entries_df[col] > 0).values.sum()
                classes.extend([col] * n_entries)
            contestant = Contestant(
                name=name,
                classes=classes,
                paid=data.paid,
            )
            contestants.append(AllocatedContestant(
                contestant=contestant,
                entries_df=data.entries_df,
            ))
        return contestants

    # def to_csv(self, location: Path):
    #     """
    #     Create a dataframe of contestant x class giving the number of entries
    #      of each contestant in each class.
    #     """
    #     data = {"contestant": [], **{c: [] for c in FLAT_CLASSES}}
    #     for contestant in self._contestants:
    #         data["contestant"].append(contestant.name)
    #         for class_id in FLAT_CLASSES:
    #             data[class_id].append(contestant.classes.count(class_id))
    #     df = pd.DataFrame(data)
    #     df.to_csv(location, index=False)
    #     _LOG.info(f"exported contestant data to {location}")
