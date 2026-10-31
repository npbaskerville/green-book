import pytest

from greenbook.cli.main import get_manager, get_registrar
from greenbook.data.entries import Contestant


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
