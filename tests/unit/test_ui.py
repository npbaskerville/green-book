import pytest

from pathlib import Path
from streamlit.testing.v1 import AppTest
from streamlit.proto.WidgetStates_pb2 import WidgetState
from streamlit.testing.v1.element_tree import Selectbox

from greenbook.cli.main import get_manager, get_registrar

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
    at = AppTest.from_file(str(APP), default_timeout=180)
    at.run()
    assert_ok(at)
    return at


@pytest.fixture(autouse=True)
def selectbox_accepts_typed_values(monkeypatch):
    """
    AppTest can only pick existing selectbox options. Send a typed new value the way the
    browser does for `accept_new_options=True`, so the name box can be tested.
    """

    def widget_state(self):
        value = self.value
        if isinstance(value, str) and value not in self.options:
            ws = WidgetState()
            ws.id = self.id
            ws.string_value = value
            return ws
        return original.fget(self)

    original = Selectbox._widget_state
    monkeypatch.setattr(Selectbox, "_widget_state", property(widget_state))


def type_name(at: AppTest, name: str):
    at.selectbox(key="reg_name").set_value(name)


def register(at: AppTest, name: str, classes: str, paid: float = 0.0):
    type_name(at, name)
    at.text_input(key="reg_classes").set_value(classes)
    at.number_input(key="reg_paid").set_value(paid)
    at.run()
    button(at, "Register").click().run()
    assert_ok(at)
    assert any(" ".join(name.split()).casefold() in s.value.casefold() for s in at.success)


def test_full_show(app, tmp_path):
    at = app
    register(at, "Aunt Dahlia", "1, 2, 25a", paid=0.2)
    register(at, "Bob Beetroot", "1 2 2")
    assert at.selectbox(key="reg_name").value is None

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

    # Special prizes: one row per judged prize. Award the Swan Inn Cup to class 1 entry 1.
    widget(at.selectbox, "Class for the Swan Inn Cup").set_value("1").run()
    widget(at.selectbox, "Entry for the Swan Inn Cup").set_value(1).run()
    button(at, "Save special prizes").click().run()
    assert_ok(at)
    assert "Swan Inn Cup: Aunt Dahlia" in get_manager(tmp_path).report_prizes()
    # The saved winner is shown again, and can be removed.
    assert widget(at.selectbox, "Class for the Swan Inn Cup").value == "1"
    widget(at.selectbox, "Class for the Swan Inn Cup").select_index(0).run()  # "Not awarded"
    button(at, "Save special prizes").click().run()
    assert "Swan Inn Cup: " in get_manager(tmp_path).report_prizes()

    button(at, "Generate results PDFs").click().run()
    assert_ok(at)
    for report in [
        "final-class-report.pdf",
        "final-prize-report.pdf",
        "final-ranking-report.pdf",
        "final-children-prize-money.pdf",
    ]:
        assert (tmp_path / "render" / report).exists()
    assert any(b.label == "Download class winners (CSV)" for b in at.get("download_button"))
    assert any((tmp_path / "backups").iterdir())


def test_invalid_entry_shows_message(app):
    type_name(app, "Aunt Dahlia")
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


def switch_folder(at: AppTest, path: Path, confirm: str):
    at.text_input(key="location_input").set_value(str(path)).run()
    button(at, confirm).click().run()
    assert_ok(at)


def test_switch_to_new_folder(app, tmp_path):
    new = tmp_path / "show-2027"
    switch_folder(app, new, "Create folder and switch")
    assert new.is_dir()
    assert any("Created a new folder" in s.value for s in app.success)
    assert app.text_input(key="location_input").value == str(new)


def test_switch_to_existing_show(app, tmp_path):
    other = tmp_path / "other"
    switch_folder(app, other, "Create folder and switch")
    register(app, "Aunt Dahlia", "1")
    switch_folder(app, tmp_path, "Switch")  # holds no show files, only the "other" folder
    switch_folder(app, other, "Switch to this show")
    assert any("existing show" in s.value for s in app.success)
    assert app.metric[0].value == "1"


def test_cancel_folder_switch(app, tmp_path):
    switch_folder(app, tmp_path / "nope", "Cancel")
    assert not (tmp_path / "nope").exists()
    assert app.text_input(key="location_input").value == str(tmp_path.resolve())


def test_judging_hides_names_by_default(app):
    register(app, "Aunt Dahlia", "1")
    register(app, "Bob Beetroot", "1")
    button(app, "Allocate entries and generate slips").click().run()
    first = widget(app.multiselect, "1st")
    assert first.options == ["1", "2"]
    first.set_value([("1", 2)]).run()
    widget(app.toggle, "Show entrant names").set_value(True).run()
    first = widget(app.multiselect, "1st")
    assert first.options == ["1 – Aunt Dahlia", "2 – Bob Beetroot"]
    assert first.value == [("1", 2)]  # unsaved pick survives the toggle


def test_names_ignore_case(app, tmp_path):
    register(app, "aunt  dahlia", "1")  # new name typed in lower case is tidied
    assert any("Aunt Dahlia" in s.value for s in app.success)
    assert app.selectbox(key="reg_name").options == ["Aunt Dahlia"]  # offered as you type

    type_name(app, "AUNT DAHLIA")
    app.text_input(key="reg_classes").set_value("2")
    app.run()
    assert any("already registered" in w.value for w in app.warning)
    app.checkbox(key="reg_merge").check().run()
    button(app, "Register").click().run()
    assert_ok(app)
    (entrant,) = get_registrar(tmp_path).contestants()
    assert entrant.contestant.name == "Aunt Dahlia"
    assert sorted(entrant.contestant.classes) == ["1", "2"]


def test_hide_entrant_from_table_only(app, tmp_path):
    register(app, "Aunt Dahlia", "1")
    register(app, "Bob Beetroot", "1")
    app.button(key="hide-Bob Beetroot").click().run()
    button(app, "Cancel").click().run()  # the pop-up asks first; cancelling changes nothing
    assert "Bob Beetroot" in [m.value for m in app.markdown]
    app.button(key="hide-Bob Beetroot").click().run()
    button(app, "Hide").click().run()
    assert_ok(app)
    shown = [m.value for m in app.markdown]
    assert "Bob Beetroot" not in shown and "Aunt Dahlia" in shown
    assert len(get_registrar(tmp_path).contestants()) == 2  # still registered

    widget(app.toggle, "Show hidden entrants (1)").set_value(True).run()
    assert ":gray[Bob Beetroot (hidden)]" in [m.value for m in app.markdown]
    app.button(key="hide-Bob Beetroot").click().run()
    assert not any(t.label.startswith("Show hidden") for t in app.toggle)
