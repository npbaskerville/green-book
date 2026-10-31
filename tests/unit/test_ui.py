import pytest

from pathlib import Path
from streamlit.testing.v1 import AppTest

from greenbook.cli.main import get_manager

APP = Path(__file__).parents[2] / "src" / "greenbook" / "ui" / "app.py"


def button(at: AppTest, label: str):
    return next(b for b in at.button if b.label == label)


def widget(widgets, label: str):
    return next(w for w in widgets if w.label == label)


def assert_ok(at: AppTest):
    assert not at.exception, [e.value for e in at.exception]
    assert not at.error, [e.value for e in at.error]


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("GREENBOOK_LOCATION", str(tmp_path))
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    assert_ok(at)
    return at


def register(at: AppTest, name: str, classes: str, paid: float = 0.0):
    at.text_input(key="reg_name").set_value(name)
    at.text_input(key="reg_classes").set_value(classes)
    at.number_input(key="reg_paid").set_value(paid)
    at.run()
    button(at, "Register").click().run()
    assert_ok(at)
    assert any(name in s.value for s in at.success)


def test_full_show(app, tmp_path):
    at = app
    register(at, "Aunt Dahlia", "1, 2, 25a", paid=0.2)
    register(at, "Bob Beetroot", "1 2 2")
    assert at.text_input(key="reg_name").value == ""

    button(at, "Allocate entries and generate slips").click().run()
    assert_ok(at)
    assert (tmp_path / "render" / "Aunt Dahlia.pdf").exists()

    # Judging: class 1 is selected first. Award 2nd to an entry from class 2.
    widget(at.multiselect, "1st").set_value([("1", 2)])
    widget(at.toggle, "Include entries from other classes").set_value(True)
    at.run()
    widget(at.multiselect, "2nd").set_value([("2", 3)])
    at.run()
    button(at, "Save results").click().run()
    assert_ok(at)
    show_class = get_manager(tmp_path).show.class_lookup("1")
    assert [ref for _, ref in show_class.first_place] == [2]
    assert [ref for _, ref in show_class.second_place] == ["2-3"]

    at.text_input(key="prize_name").set_value("Wonky Wooden Spoon")
    at.run()
    button(at, "Award prize").click().run()
    assert_ok(at)

    button(at, "Generate results PDFs").click().run()
    assert_ok(at)
    for report in ["final-class-report.pdf", "final-prize-report.pdf", "final-ranking-report.pdf"]:
        assert (tmp_path / "render" / report).exists()
    assert "Wonky Wooden Spoon: Aunt Dahlia" in get_manager(tmp_path).report_prizes()
    assert any((tmp_path / "backups").iterdir())


def test_invalid_entry_shows_message(app):
    app.text_input(key="reg_name").set_value("Aunt Dahlia")
    app.text_input(key="reg_classes").set_value("1, 999")
    app.run()
    assert any("Unknown class '999'" in e.value for e in app.error)
    assert button(app, "Register").disabled


def test_reallocation_needs_confirmation(app):
    register(app, "Aunt Dahlia", "1")
    button(app, "Allocate entries and generate slips").click().run()
    widget(app.multiselect, "1st").set_value([("1", 1)])
    app.run()
    button(app, "Save results").click().run()
    assert button(app, "Allocate entries and generate slips").disabled
    app.checkbox(key="allocate_confirm").check().run()
    assert not button(app, "Allocate entries and generate slips").disabled
