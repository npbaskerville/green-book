import pickle
import hashlib
from attr import attrib
from typing import Sequence
from collections import Counter
from dataclasses import dataclass
from ruamel.yaml import YAML, yaml_object

from greenbook.data.consts import MAX_ENTRIES_PER_CONTESTANT

yaml = YAML()

HASH_LEN = 8


@yaml_object(yaml)
@dataclass
class Contestant:
    classes: Sequence[int] = attrib(type=Sequence[int])
    name: str = attrib(type=str)

    def __post_init__(self):
        n_entries_per_class = Counter(self.classes)
        assert all(n <= MAX_ENTRIES_PER_CONTESTANT for n in n_entries_per_class.values())
        assert len(self.name.split()) >= 2

    def unique_id(self) -> str:
        hash_data = self.name + "-".join(str(c) for c in sorted(self.classes))
        byte_like = pickle.dumps(hash_data)
        return hashlib.blake2b(byte_like, digest_size=HASH_LEN // 2).hexdigest()

    def __hash__(self) -> int:
        return int(self.unique_id(), 16)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Contestant):
            return False
        return self.unique_id == other.unique_id

    def __lt__(self, other) -> bool:
        if self.name == other.name:
            return self.unique_id < other.unique_id
        return self.name < other.name
