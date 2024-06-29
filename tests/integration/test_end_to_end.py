import pytest

from pathlib import Path
from datetime import datetime

from greenbook.cli.main import get_manager, get_registrar
from greenbook.data.entries import Contestant


class TestEndToEndShow:
    @pytest.fixture
    def out_dir(
        self,
    ):
        random_dir = Path(f".{hash(datetime.now())}")
        random_dir.mkdir(exist_ok=True)
        yield random_dir

    def test_basic_winners(self, out_dir):
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
                name="David Date",
                classes=["1", "3", "3"],
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

        # Class 1: Alice, Bob, Carole, [David]
        manager.add_judgment(
            class_id="1",
            first=[_lookup_contestant_id(contestants[0], "1")[0]],
            second=[_lookup_contestant_id(contestants[1], "1")[0]],
            third=[_lookup_contestant_id(contestants[2], "1")[0]],
            commendations=[_lookup_contestant_id(contestants[3], "1")[0]],
        )
        # Class 2: Alice, Bob
        manager.add_judgment(
            class_id="2",
            first=[_lookup_contestant_id(contestants[1], "2")[0]],
            second=[_lookup_contestant_id(contestants[0], "2")[0]],
            third=(),
            commendations=(),
        )
        # Class 3: David, Alice, David
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
        # Class 42: Bob, Carole
        manager.add_judgment(
            class_id="42",
            first=[_lookup_contestant_id(contestants[1], "42")[0]],
            second=[_lookup_contestant_id(contestants[2], "42")[0]],
            third=(),
            commendations=(),
        )
        show_class = manager.report_class("1")
        assert tuple(show_class.first_place) == (contestants[0],)
        assert tuple(show_class.second_place) == (contestants[1],)
        assert tuple(show_class.third_place) == (contestants[2],)
        assert tuple(show_class.commendations) == (contestants[3],)
        show_class = manager.report_class("2")
        assert tuple(show_class.first_place) == (contestants[1],)
        assert tuple(show_class.second_place) == (contestants[0],)
        assert tuple(show_class.third_place) == ()
        assert tuple(show_class.commendations) == ()
        show_class = manager.report_class("3")
        assert tuple(show_class.first_place) == (contestants[3],)
        assert tuple(show_class.second_place) == (contestants[0], contestants[3])
        assert tuple(show_class.third_place) == ()
        assert tuple(show_class.commendations) == ()
        show_class = manager.report_class("42")
        assert tuple(show_class.first_place) == (contestants[1],)
        assert tuple(show_class.second_place) == (contestants[2],)
        assert tuple(show_class.third_place) == ()
        assert tuple(show_class.commendations) == ()
