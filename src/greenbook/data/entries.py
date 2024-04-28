import hashlib
import pickle
from dataclasses import dataclass
from typing import Sequence

from attr import attrib
from ruamel.yaml import YAML, yaml_object

yaml = YAML()

HASH_LEN = 8


@yaml_object(YAML)
@dataclass
class Contestant:
    classes: Sequence[int] = attrib(type=Sequence[int])
    name: str = attrib(type=str)

    @property
    def unique_id(self) -> str:
        hash_data = self.name + "-".join(str(c) for c in sorted(self.classes))
        byte_like = pickle.dumps(hash_data)
        return hashlib.blake2b(byte_like, digest_size=HASH_LEN // 2).hexdigest()

    def __hash__(self) -> int:
        return int(self.unique_id, 16)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Contestant):
            return False
        return self.unique_id == other.unique_id

    def __lt__(self, other) -> bool:
        if self.name == other.name:
            return self.unique_id < other.unique_id
        return self.name < other.name
