import pytest

import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from greenbook.cli.main import get_manager, get_registrar
from greenbook.data.entries import Contestant
from greenbook.definitions.prizes import MBShield
from greenbook.definitions.classes import FLAT_CLASSES


class TestEndToEndShow:
    @pytest.fixture
    def out_dir(
        self,
    ):
        random_dir = Path(f".{hash(datetime.now())}")
        random_dir.mkdir(exist_ok=True)
        yield random_dir
        # remove all files and dir
        for file in random_dir.iterdir():
            if file.is_file():
                file.unlink()
            else:
                for subfile in file.iterdir():
                    subfile.unlink()
                file.rmdir()
        random_dir.rmdir()

    def test_basic_winners(self, out_dir):
        contestants = [
            Contestant(name="Alice Appleby", classes=["1", "2", "3"]),
            Contestant(
                name="Bob Beetroot",
                classes=["1", "2", "2", "42"],
            ),
            Contestant(
                name="Carole Carrot",
                classes=["1", "42", "61"],
            ),
            Contestant(
                name="Aunt Dahlia",
                classes=["1", "3", "3", "58A", "61"],
            ),
        ]
        registrar = get_registrar(out_dir)
        for contestant in contestants:
            registrar.register(contestant)

        manager = get_manager(out_dir)
        manager.allocate(registrar.contestants())
        contestant_entries = manager.contestant_entries()

        def _lookup_contestant_id(_contestant, class_id):
            entries = contestant_entries[_contestant]
            entry_ids = []
            for entry in entries:
                if entry.class_id == class_id:
                    entry_ids.append(entry.contestant_id)
            return entry_ids

        points = {"Alice": 0, "Bob": 0, "Carole": 0, "Dahlia": 0}
        # Class 1: Alice, Bob, Carole, [Dahlia]
        manager.add_judgment(
            class_id="1",
            first=[_lookup_contestant_id(contestants[0], "1")[0]],
            second=[_lookup_contestant_id(contestants[1], "1")[0]],
            third=[_lookup_contestant_id(contestants[2], "1")[0]],
            commendations=[_lookup_contestant_id(contestants[3], "1")[0]],
        )
        points["Alice"] += 3
        points["Bob"] += 2
        points["Carole"] += 1
        # Class 2: Alice, Bob
        manager.add_judgment(
            class_id="2",
            first=[_lookup_contestant_id(contestants[1], "2")[0]],
            second=[_lookup_contestant_id(contestants[0], "2")[0]],
            third=(),
            commendations=(),
        )
        points["Bob"] += 3
        points["Alice"] += 2
        # Class 3: Dahlia, Alice-Dahlia
        manager.add_judgment(
            class_id="3",
            first=[_lookup_contestant_id(contestants[3], "3")[0]],
            second=[
                _lookup_contestant_id(contestants[0], "3")[0],
                _lookup_contestant_id(contestants[3], "3")[1],
            ],
            third=[],
            commendations=(),
        )
        points["Dahlia"] += 3
        points["Alice"] += 2
        points["Dahlia"] += 2
        # Class 42: Bob, Carole
        manager.add_judgment(
            class_id="42",
            first=[_lookup_contestant_id(contestants[1], "42")[0]],
            second=[_lookup_contestant_id(contestants[2], "42")[0]],
            third=(),
            commendations=(),
        )
        points["Bob"] += 3
        points["Carole"] += 2
        # Class 58A: Dahlia wins
        manager.add_judgment(
            class_id="58A",
            first=[_lookup_contestant_id(contestants[3], "58A")[0]],
            second=[],
            third=[],
            commendations=[],
        )
        points["Dahlia"] += 3
        # Class 61: Carole, Dahlia
        manager.add_judgment(
            class_id="61",
            first=[_lookup_contestant_id(contestants[2], "61")[0]],
            second=[_lookup_contestant_id(contestants[3], "61")[0]],
            third=[],
            commendations=[],
        )
        points["Carole"] += 3
        points["Dahlia"] += 2
        show_class = manager.report_class("1")
        assert tuple(show_class.first_place) == ((contestants[0], 1),)
        assert tuple(show_class.second_place) == ((contestants[1], 2),)
        assert tuple(show_class.third_place) == ((contestants[2], 3),)
        assert tuple(show_class.commendations) == ((contestants[3], 4),)
        show_class = manager.report_class("2")
        assert tuple(show_class.first_place) == ((contestants[1], 2),)
        assert tuple(show_class.second_place) == ((contestants[0], 1),)
        assert tuple(show_class.third_place) == ()
        assert tuple(show_class.commendations) == ()
        show_class = manager.report_class("3")
        assert tuple(show_class.first_place) == ((contestants[3], 2),)
        assert tuple(show_class.second_place) == ((contestants[0], 1), (contestants[3], 3))
        assert tuple(show_class.third_place) == ()
        assert tuple(show_class.commendations) == ()
        show_class = manager.report_class("42")
        assert tuple(show_class.first_place) == ((contestants[1], 1),)
        assert tuple(show_class.second_place) == ((contestants[2], 2),)
        assert tuple(show_class.third_place) == ()
        assert tuple(show_class.commendations) == ()
        show_class = manager.report_class("58A")
        assert tuple(show_class.first_place) == ((contestants[3], 1),)
        assert tuple(show_class.second_place) == ()
        assert tuple(show_class.third_place) == ()
        assert tuple(show_class.commendations) == ()
        show_class = manager.report_class("61")
        assert tuple(show_class.first_place) == ((contestants[2], 1),)
        assert tuple(show_class.second_place) == ((contestants[3], 2),)
        assert tuple(show_class.third_place) == ()
        assert tuple(show_class.commendations) == ()
        ranking = manager.report_ranking()
        expected_ranking = sorted(
            [
                (contestants[1], points["Bob"]),
                (contestants[3], points["Dahlia"]),
                (contestants[0], points["Alice"]),
                (contestants[2], points["Carole"]),
            ],
            key=lambda x: x[1],
            reverse=True,
        )
        assert list(ranking) == expected_ranking
        overall_winner = ranking[0]
        prize = MBShield()
        overall_prize_str = f"{prize}: {overall_winner[0]}"
        winning_strings = manager.report_prizes()
        assert overall_prize_str in winning_strings

        # get repo root dir
        greenbook_dir = Path(__file__).parent.parent.parent
        test_outdir = greenbook_dir / "test-output"
        test_outdir.mkdir(exist_ok=True)
        manager.render_contestants(test_outdir / "rendered-contestants")
        manager.render_final_report(test_outdir / "final-report")
        manager.to_csv(test_outdir / "classes.csv")
        registrar.to_csv(test_outdir / "contestants.csv")

    def test_unique_contestant_ids(self, out_dir):
        """
        Check the contestant IDs in every class are unique.
        """
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

        manager = get_manager(out_dir)
        manager.allocate(registrar.contestants())
        contestant_entries = manager.contestant_entries()

        class_entries = defaultdict(list)
        for entries in contestant_entries.values():
            for entry in entries:
                class_entries[entry.class_id].append(entry.contestant_id)

        for class_id, entries in class_entries.items():
            assert len(entries) == len(set(entries))

    def test_rolling_registration(self, out_dir):
        """
        Check that the contestants IDs in each class do not change as new contestants are added.
        """
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
        out_dir_single = out_dir / "single"
        out_dir_rolling = out_dir / "rolling"
        registrar_rolling = get_registrar(out_dir_single)
        for contestant in contestants:
            registrar_rolling.register(contestant)
            manager = get_manager(out_dir_single)
            manager.allocate(registrar_rolling.contestants())
        contestant_entries_rolling = manager.contestant_entries()
        registrar_single = get_registrar(out_dir_rolling)
        for contestant in contestants:
            registrar_single.register(contestant)
        manager = get_manager(out_dir_rolling)
        manager.allocate(registrar_single.contestants())
        contestant_entries_single = manager.contestant_entries()
        assert contestant_entries_rolling == contestant_entries_single

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

        manager = get_manager(out_dir)
        manager.allocate(registrar.contestants())
        csv_loc = out_dir / "contestants.csv"
        manager.to_csv(csv_loc)
        df = pd.read_csv(csv_loc, index_col=0)
        assert list(df.columns) == list(FLAT_CLASSES.keys())
        alice_locations = [(1, "1"), (1, "2"), (1, "3")]
        bob_locations = [(2, "1"), (2, "2"), (3, "2"), (1, "42")]
        carole_locations = [(3, "1"), (2, "42")]
        dahlia_locations = [(4, "1"), (2, "3"), (3, "3")]
        empty_locations = {(idx, col) for idx in df.index for col in df.columns}
        empty_locations -= set(alice_locations)
        empty_locations -= set(bob_locations)
        empty_locations -= set(carole_locations)
        empty_locations -= set(dahlia_locations)
        for idx, col in empty_locations:
            assert np.isnan(float(df.loc[idx, col]))
        for name, locs in zip(
            ["Alice Appleby", "Bob Beetroot", "Carole Carrot", "Aunt Dahlia"],
            [alice_locations, bob_locations, carole_locations, dahlia_locations],
        ):
            for idx, col in locs:
                assert df.loc[idx, col] == name
