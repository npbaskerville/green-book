import pytest

from greenbook.cli.main import get_manager, get_registrar
from greenbook.data.entries import Contestant
from greenbook.definitions.classes import FLAT_CLASSES


class TestContestantValidation:
    @pytest.mark.parametrize(
        "kwargs, message",
        [
            (dict(name="Alice", classes=["1"], paid=0.0), "first and last name"),
            (dict(name="Alice Appleby", classes=["999"], paid=0.0), "Unknown class '999'"),
            (dict(name="Alice Appleby", classes=["1", "1", "1"], paid=0.0), "class 1 has 3"),
            (dict(name="Alice Appleby", classes=["1"], paid=-1.0), "can't be negative"),
        ],
    )
    def test_invalid_contestant_has_readable_error(self, kwargs, message):
        with pytest.raises(ValueError, match=message):
            Contestant(**kwargs)

    def test_names_ignore_case_and_spacing(self, tmp_path):
        registrar = get_registrar(tmp_path)
        registrar.register(Contestant(name="bob  smith", classes=["1"], paid=0.0))
        registrar.register(Contestant(name="BOB Smith", classes=["2"], paid=0.0))
        registrar.register(Contestant(name="Ann McDonald", classes=["3"], paid=0.0))
        assert registrar.canonical_name("ANN MCDONALD") == "Ann McDonald"
        names = sorted(c.contestant.name for c in get_registrar(tmp_path).contestants())
        assert names == ["Ann McDonald", "Bob Smith"]

    def test_valid_contestant(self):
        Contestant(name="Alice Appleby", classes=["1", "1", "25A"], paid=0.5)


class TestManager:
    @pytest.fixture
    def show_dir(self, tmp_path):
        registrar = get_registrar(tmp_path)
        registrar.register(Contestant(name="Alice Appleby", classes=["1", "2"], paid=0.0))
        registrar.register(Contestant(name="Bob Beetroot", classes=["1", "2"], paid=0.0))
        get_manager(tmp_path).allocate(registrar.contestants())
        return tmp_path

    def test_manual_prize_survives_judging(self, show_dir):
        get_manager(show_dir).add_prize(prize="Wonky Spoon", class_id="1", contestant_id=1)
        get_manager(show_dir).add_judgment(
            class_id="2", first=[1], second=[], third=[], commendations=[]
        )
        prizes = get_manager(show_dir).report_prizes()
        assert "Wonky Spoon: Alice Appleby" in prizes

    def test_reports_before_any_judging(self, show_dir, tmp_path):
        manager = get_manager(show_dir)
        assert manager.report_ranking() == []
        manager.render_final_report(tmp_path / "render")
        assert (tmp_path / "render" / "final-prize-report.pdf").exists()


class TestPrizesAndReports:
    @pytest.fixture
    def show_dir(self, tmp_path):
        registrar = get_registrar(tmp_path)
        registrar.register(Contestant(name="Alice Appleby", classes=["1", "2"], paid=0.0))
        registrar.register(Contestant(name="Bob Beetroot", classes=["1", "2", "71"], paid=0.0))
        registrar.register(Contestant(name="Cara Child", classes=["1", "71", "72"], paid=0.0))
        get_manager(tmp_path).allocate(registrar.contestants())
        return tmp_path

    def judge(self, show_dir, class_id, first=(), second=(), third=()):
        get_manager(show_dir).add_judgment(
            class_id=class_id, first=first, second=second, third=third, commendations=[]
        )

    def test_prize_report_order(self, show_dir):
        self.judge(show_dir, "1", first=[1])
        get_manager(show_dir).add_prize(prize="Wonky Spoon", class_id="1", contestant_id=2)
        names = [line.split(":")[0] for line in get_manager(show_dir).report_prizes()]
        assert names == [
            "M & B Shield",
            "Harold Herbert Cup",
            "Swan Inn Cup",
            "William Jowett Trophy",
            "Mrs Ann Porter Cup",
            "Gerald Taylor Cup",
            "Butler Trophy",
            "Court House Salver",
            "Children's Cup",
            "George Wilson Revill Cup",
            "Betty Hughes Cup",
            "William Trow-Poole Trophy",
            "Joan Hollier Plate",
            "Wonky Spoon",
        ]

    def test_awarding_a_prize_again_replaces_the_winner(self, show_dir):
        get_manager(show_dir).add_prize(prize="Swan Inn Cup", class_id="1", contestant_id=1)
        get_manager(show_dir).add_prize(prize="Swan Inn Cup", class_id="1", contestant_id=2)
        assert "Swan Inn Cup: Bob Beetroot" in get_manager(show_dir).report_prizes()
        get_manager(show_dir).remove_prize("Swan Inn Cup")
        assert "Swan Inn Cup: " in get_manager(show_dir).report_prizes()

    def test_children_prize_money(self, show_dir):
        # Class 1: Alice 1, Bob 2, Cara 3. Class 71: Bob 1, Cara 2. Class 72: Cara 1.
        self.judge(show_dir, "1", first=[3], second=[2], third=[1])
        self.judge(show_dir, "71", first=[1], second=[2])
        self.judge(show_dir, "72", third=[1])
        money = {c.name: round(m, 2) for c, m in get_manager(show_dir).children_prize_money()}
        assert money == {"Bob Beetroot": 0.5, "Cara Child": 0.6}

    def test_class_winners(self, show_dir):
        self.judge(show_dir, "1", first=[2])
        winners = get_manager(show_dir).class_winners()
        assert list(winners.columns) == ["class", "winner"]
        assert winners.iloc[0].to_dict() == {
            "class": "1 - White Potatoes",
            "winner": "Bob Beetroot",
        }
        assert winners.iloc[1].to_dict() == {"class": "2 - Coloured Potatoes", "winner": ""}
        assert len(winners) == len(FLAT_CLASSES)

    def test_final_report_includes_children_prize_money(self, show_dir):
        self.judge(show_dir, "71", first=[1])
        get_manager(show_dir).render_final_report(show_dir / "render")
        assert (show_dir / "render" / "final-children-prize-money.pdf").exists()
