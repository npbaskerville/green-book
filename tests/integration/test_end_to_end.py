import pytest

import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from greenbook.cli.main import get_manager, get_registrar
from greenbook.data.entries import Contestant, DeletedContestant
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
            Contestant(name="Alice Appleby", classes=tuple(["1", "2", "3", "7"]), paid=0.0),
            Contestant(
                name="Bob Beetroot",
                classes=tuple(["1", "2", "2", "42"]),
                paid=0.0,
            ),
            Contestant(
                name="Carole Carrot",
                classes=tuple(["1", "42", "61", "7"]),
                paid=0.0,
            ),
            Contestant(
                name="Aunt Dahlia",
                classes=tuple(["1", "3", "3", "60A", "61", "7", "62", "2"]),
                paid=0.0,
            ),
        ]
        contestant_lookup = {
            ("Alice Appleby", "1", 0): 1,
            ("Alice Appleby", "2", 0): 1,
            ("Alice Appleby", "3", 0): 1,
            ("Alice Appleby", "7", 0): 1,
            ("Bob Beetroot", "1", 0): 2,
            ("Bob Beetroot", "2", 0): 2,
            ("Bob Beetroot", "2", 1): 3,
            ("Bob Beetroot", "42", 0): 1,
            ("Carole Carrot", "1", 0): 3,
            ("Carole Carrot", "42", 0): 2,
            ("Carole Carrot", "61", 0): 1,
            ("Carole Carrot", "7", 0): 2,
            ("Aunt Dahlia", "1", 0): 4,
            ("Aunt Dahlia", "3", 0): 2,
            ("Aunt Dahlia", "3", 1): 3,
            ("Aunt Dahlia", "58A", 0): 1,
            ("Aunt Dahlia", "61", 0): 2,
            ("Aunt Dahlia", "7", 0): 2,
            ("Aunt Dahlia", "62", 0): 1,
            ("Aunt Dahlia", "2", 0): 4,
        }

        registrar = get_registrar(out_dir)
        for contestant in contestants:
            registrar.register(contestant)

        manager = get_manager(out_dir)
        manager.allocate(registrar.contestants())

        def _lookup_contestant_id(_contestant, class_id, entry_ord):
            return contestant_lookup[(_contestant.name, class_id, entry_ord)]

        points = {"Alice": 0, "Bob": 0, "Carole": 0, "Dahlia": 0}
        # Class 1: Alice, Bob, Carole, [Dahlia]
        manager.add_judgment(
            class_id="1",
            first=[_lookup_contestant_id(contestants[0], "1", 0)],
            second=[_lookup_contestant_id(contestants[1], "1",0)],
            third=[_lookup_contestant_id(contestants[2], "1", 0)],
            commendations=[_lookup_contestant_id(contestants[3], "1", 0)],
        )
        points["Alice"] += 3
        points["Bob"] += 2
        points["Carole"] += 1
        # Class 2: Alice, Bob
        manager.add_judgment(
            class_id="2",
            first=[_lookup_contestant_id(contestants[1], "2", 0)],
            second=[_lookup_contestant_id(contestants[0], "2", 0)],
            third=(),
            commendations=(),
        )
        points["Bob"] += 3
        points["Alice"] += 2
        # Class 3: Dahlia, Alice-Dahlia
        manager.add_judgment(
            class_id="3",
            first=[_lookup_contestant_id(contestants[3], "3", 0)],
            second=[
                _lookup_contestant_id(contestants[0], "3", 0),
                _lookup_contestant_id(contestants[3], "3", 1),
            ],
            third=[],
            commendations=(),
        )
        points["Dahlia"] += 3
        points["Alice"] += 2
        # no points for Dahlia's second entry
        # Class 42: Bob, Carole
        manager.add_judgment(
            class_id="42",
            first=[_lookup_contestant_id(contestants[1], "42", 0)],
            second=[_lookup_contestant_id(contestants[2], "42", 0)],
            # Dahlia's entry in class 2 was reclassified to class 42, and then she won third.
            third=(("2", _lookup_contestant_id(contestants[3], "2", 0)),),
            commendations=(),
        )
        points["Bob"] += 3
        points["Carole"] += 2
        points["Dahlia"] += 1
        # Class 58A: Dahlia wins
        manager.add_judgment(
            class_id="60A",
            first=[_lookup_contestant_id(contestants[3], "60A", 0)],
            second=[],
            third=[],
            commendations=[],
        )
        points["Dahlia"] += 3
        # Class 61: Carole, Dahlia
        manager.add_judgment(
            class_id="61",
            first=[_lookup_contestant_id(contestants[2], "61", 0)],
            second=[_lookup_contestant_id(contestants[3], "61", 0)],
            third=[],
            commendations=[],
        )
        points["Carole"] += 3
        points["Dahlia"] += 2
        # Class 7: No winners
        manager.add_judgment(
            class_id="7",
            first=[],
            second=[],
            third=[],
            commendations=[],
        )
        # Class 62: Dahlia
        manager.add_judgment(
            class_id="62",
            first=[_lookup_contestant_id(contestants[3], "62", 0)],
            second=[],
            third=[],
            commendations=[],
        )
        points["Dahlia"] += 3
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
        # -3 signifies it was the 4th entry in class 2, but was moved to class 42
        assert tuple(show_class.third_place) == ((contestants[3], "2-4"),)
        assert tuple(show_class.commendations) == ()
        show_class = manager.report_class("60A")
        assert tuple(show_class.first_place) == ((contestants[3], 1),)
        assert tuple(show_class.second_place) == ()
        assert tuple(show_class.third_place) == ()
        assert tuple(show_class.commendations) == ()
        show_class = manager.report_class("61")
        assert tuple(show_class.first_place) == ((contestants[2], 1),)
        assert tuple(show_class.second_place) == ((contestants[3], 2),)
        assert tuple(show_class.third_place) == ()
        assert tuple(show_class.commendations) == ()
        show_class = manager.report_class("7")
        assert tuple(show_class.first_place) == ()
        assert tuple(show_class.second_place) == ()
        assert tuple(show_class.third_place) == ()
        assert tuple(show_class.commendations) == ()
        show_class = manager.report_class("62")
        assert tuple(show_class.first_place) == ((contestants[3], 1),)
        assert tuple(show_class.second_place) == ()
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
        manual_prize = "Wonky Wooden Spoon"
        manager.add_prize(
            class_id="1",
            contestant_id=_lookup_contestant_id(contestants[0], "1", 0),
            prize=manual_prize,
        )
        manual_prize_str = f"{manual_prize}: {contestants[0].name}"
        overall_winner = ranking[0]
        prize = MBShield()
        overall_prize_str = f"{prize}: {overall_winner[0]}"
        winning_strings = manager.report_prizes()
        assert overall_prize_str in winning_strings
        assert manual_prize_str in winning_strings
        # get repo root dir
        greenbook_dir = Path(__file__).parent.parent.parent
        test_outdir = greenbook_dir / "test-output"
        test_outdir.mkdir(exist_ok=True)
        manager.render_contestants(test_outdir / "rendered-contestants")
        manager.render_final_report(test_outdir / "final-report")
        manager.to_csv(test_outdir / "classes.csv")
        # registrar.to_csv(test_outdir / "contestants.csv")

    def test_unique_contestant_ids(self, out_dir):
        """
        Check the contestant IDs in every class are unique.
        """
        contestants = [
            Contestant(name="Alice Appleby", classes=["1", "2", "3"], paid=0.0),
            Contestant(
                name="Bob Beetroot",
                classes=["1", "2", "2", "42"],
                paid=0.0,
            ),
            Contestant(
                name="Carole Carrot",
                classes=["1", "42"],
                paid=0.1,
            ),
            Contestant(
                name="Aunt Dahlia",
                classes=["1", "3", "3"],
                paid=0.30,
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
            Contestant(name="Alice Appleby", classes=["1", "2", "3"], paid=0.0),
            Contestant(name="Bob Beetroot", classes=["1", "2", "2", "42"], paid=0.0),
            Contestant(name="Carole Carrot", classes=["1", "42"], paid=0.0),
            Contestant(name="Aunt Dahlia", classes=["1", "3", "3"], paid=0.0),
        ]
        out_dir_single = out_dir / "single"
        out_dir_rolling = out_dir / "rolling"
        registrar_rolling = get_registrar(out_dir_rolling)
        for contestant in contestants:
            registrar_rolling.register(contestant)
            manager = get_manager(out_dir_rolling)
            manager.allocate(registrar_rolling.contestants())
        contestant_entries_rolling = manager.contestant_entries()

        registrar_single = get_registrar(out_dir_single)
        for contestant in contestants:
            registrar_single.register(contestant)
        manager = get_manager(out_dir_single)
        manager.allocate(registrar_single.contestants())
        contestant_entries_single = manager.contestant_entries()
        assert contestant_entries_rolling == contestant_entries_single

    def test_export(self, out_dir):
        contestants = [
            Contestant(name="Alice Appleby", classes=["1", "2", "3"], paid=0.0),
            Contestant(name="Bob Beetroot", classes=["1", "2", "2", "42"], paid=0.0),
            Contestant(name="Carole Carrot", classes=["1", "42"], paid=0.1),
            Contestant(name="Aunt Dahlia", classes=["1", "3", "3"], paid=0.30),
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

    @pytest.mark.skip(reason="deprecate")
    def test_registration_with_deletes(self, out_dir):
        """
        Check that the contestant IDs are not changes by deletion of other contestants.
        """
        contestants = [
            Contestant(name="Alice Appleby", classes=["1", "2", "3"], paid=0.0),
            Contestant(name="Bob Beetroot", classes=["1", "2", "2", "42"], paid=0.0),
            Contestant(name="Carole Carrot", classes=["1", "42"], paid=0.0),
            Contestant(name="Aunt Dahlia", classes=["1", "3", "3"], paid=0.0),
        ]
        out_dir_single = out_dir / "single"
        out_dir_del = out_dir / "delete"
        registrar_del = get_registrar(out_dir_del)
        for contestant in contestants:
            registrar_del.register(contestant)
        manager = get_manager(out_dir_del)
        manager.allocate(registrar_del.contestants())
        delete = "Bob Beetroot"
        registrar_del.delete_contestant(delete)
        manager.allocate(registrar_del.contestants())
        contestant_entries_del = manager.contestant_entries()

        registrar_single = get_registrar(out_dir_single)
        for contestant in contestants:
            registrar_single.register(contestant)
        manager = get_manager(out_dir_single)
        manager.allocate(registrar_single.contestants())
        contestant_entries_single = manager.contestant_entries()

        for contestant in contestant_entries_del:
            if not isinstance(contestant, DeletedContestant):
                assert contestant_entries_del[contestant] == contestant_entries_single[contestant]
                assert contestant.name != delete
            else:
                assert contestant.name == f"DELETED ({delete})"
        assert delete in [c.name for c in contestant_entries_single]
        assert not any(isinstance(c, DeletedContestant) for c in contestant_entries_single)
