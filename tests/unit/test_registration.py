import pytest

import pandas as pd
from pathlib import Path
from datetime import datetime

from greenbook.cli.main import get_registrar
from greenbook.data.entries import Contestant
from greenbook.definitions.classes import FLAT_CLASSES


class TestRegistrar:
    @pytest.fixture
    def out_dir(
        self,
    ):
        random_dir = Path(f".{hash(datetime.now())}")
        random_dir.mkdir(exist_ok=True)
        yield random_dir
        # remove all files and dir
        for file in random_dir.iterdir():
            file.unlink()
        random_dir.rmdir()

    def test_export(self, out_dir):
        contestants = [
            Contestant(name="Alice Appleby", classes=["1", "2", "3"]),
            Contestant(
                name="Bob Beetroot",
                classes=["1", "2", "2", "42"],
            ),
            Contestant(
                name="Carole Carrot",
                classes=["1", "42"],
            ),
            Contestant(
                name="Aunt Dahlia",
                classes=["1", "3", "3"],
            ),
        ]
        registrar = get_registrar(out_dir)
        for contestant in contestants:
            registrar.register(contestant)
        csv_loc = out_dir / "contestants.csv"
        registrar.to_csv(csv_loc)
        df = pd.read_csv(csv_loc)
        assert list(df.columns) == ["contestant", *FLAT_CLASSES.keys()]
        assert len(df) == 4
        assert df.loc[0, "contestant"] == "Alice Appleby"
        assert df.loc[0, "1"] == 1
        assert df.loc[0, "2"] == 1
        assert df.loc[0, "3"] == 1
        for col in set(FLAT_CLASSES.keys()) - {"1", "2", "3"}:
            assert df.loc[0, col] == 0

        assert df.loc[1, "contestant"] == "Bob Beetroot"
        assert df.loc[1, "1"] == 1
        assert df.loc[1, "2"] == 2
        assert df.loc[1, "42"] == 1
        for col in set(FLAT_CLASSES.keys()) - {"1", "2", "42"}:
            assert df.loc[1, col] == 0

        assert df.loc[2, "contestant"] == "Carole Carrot"
        assert df.loc[2, "1"] == 1
        assert df.loc[2, "42"] == 1
        for col in set(FLAT_CLASSES.keys()) - {"1", "42"}:
            assert df.loc[2, col] == 0

        assert df.loc[3, "contestant"] == "Aunt Dahlia"
        assert df.loc[3, "1"] == 1
        assert df.loc[3, "3"] == 2
        for col in set(FLAT_CLASSES.keys()) - {"1", "3"}:
            assert df.loc[3, col] == 0
