"""
Local web UI for Greenbook. Start it with `greenbook-ui`.

The UI holds no state of its own: every run reads the show from the data folder, and every
change goes through the same Registrar/Manager calls as the CLI, so the two can be mixed.
"""

import io
import os
import re
import sys
import pandas as pd
import shutil
import zipfile
import streamlit as st
import matplotlib
import subprocess
from pathlib import Path
from datetime import datetime
from collections import Counter

from greenbook.cli.main import get_manager, get_registrar
from greenbook.data.show import Show, ShowClass
from greenbook.data.entries import Contestant
from greenbook.definitions.prices import entry_fee
from greenbook.definitions.prizes import JUDGED_PRIZES
from greenbook.definitions.classes import FLAT_CLASSES

# Streamlit runs the script off the main thread, where GUI backends (e.g. macOS) crash.
matplotlib.use("Agg")

PLACES = {"first": "1st", "second": "2nd", "third": "3rd", "commendations": "Commended"}
BAD_NAME_CHARS = set('\\/:*?"<>|')  # names become PDF filenames, and Windows rejects these
REPORTS = {
    "final-class-report.pdf": "class results",
    "final-prize-report.pdf": "prize winners",
    "final-ranking-report.pdf": "points ranking",
    "final-children-prize-money.pdf": "children's prize money",
}


# region helpers
def class_sort_key(class_id: str):
    number, suffix = re.match(r"(\d*)(.*)", class_id).groups()
    return int(number or 0), suffix


def class_label(class_id: str) -> str:
    return f"{class_id} – {FLAT_CLASSES[class_id]}"


def parse_classes(text: str) -> list[str]:
    return [c.upper() for c in re.split(r"[,\s]+", text) if c]


def check_name(name: str):
    if BAD_NAME_CHARS & set(name):
        raise ValueError(f"Names can't contain any of {' '.join(sorted(BAD_NAME_CHARS))}")


def money(amount: float) -> str:
    return f"£{amount:.2f}"


def entry_key(class_id: str, ref) -> tuple[str, int]:
    """Judging results refer to an entry by number (this class) or "25A-3" (another class)."""
    if isinstance(ref, str) and "-" in ref:
        other_class, number = ref.rsplit("-", 1)
        return other_class, int(number)
    return class_id, int(ref)


def saved_results(show_class: ShowClass) -> dict[str, list[tuple[str, int]]]:
    return {
        place: [entry_key(show_class.class_id, ref) for _, ref in getattr(show_class, attr)]
        for place, attr in [
            ("first", "first_place"),
            ("second", "second_place"),
            ("third", "third_place"),
            ("commendations", "commendations"),
        ]
    }


def is_judged(show_class: ShowClass) -> bool:
    return any(saved_results(show_class).values())


def results_by_entry(show: Show) -> dict[tuple[str, int], str]:
    """Map (class, entry number) to its award, e.g. "1st" or "2nd in class 4"."""
    results = {}
    for show_class in show.classes():
        for place, keys in saved_results(show_class).items():
            for key in keys:
                where = "" if key[0] == show_class.class_id else f" in class {show_class.class_id}"
                results[key] = PLACES[place] + where
    return results


def judged_prize_awards(show: Show) -> dict[str, tuple[str, int]]:
    """Map each judged prize already awarded to its (class, entry number)."""
    awards = {}
    for contestant, class_id, prize in show.prizes:
        show_class = show.class_lookup(class_id)
        if prize in JUDGED_PRIZES and show_class and contestant in show_class.contestants:
            awards[prize] = (class_id, show_class.contestants.index(contestant) + 1)
    return awards


def entry_name(show: Show, key: tuple[str, int]) -> str:
    return show.class_lookup(key[0]).entry_lookup(key[1]).name


def backup(location: Path):
    files = [location / f for f in ("contestants.csv", "classes.yaml") if (location / f).exists()]
    if files:
        dest = location / "backups" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
        dest.mkdir(parents=True)
        for file in files:
            shutil.copy2(file, dest)


def act(slot: str, location: Path, change, *args):
    """Button callback: back up, make a change, and keep its outcome to show under `slot`."""
    try:
        backup(location)
        message = change(location, *args)
        st.session_state[f"flash-{slot}"] = ("success", message)
    except Exception as e:  # show any failure as a message rather than a traceback
        st.session_state[f"flash-{slot}"] = ("error", str(e) or type(e).__name__)


def flash(slot: str):
    if message := st.session_state.pop(f"flash-{slot}", None):
        kind, text = message
        getattr(st, kind)(text)


def open_file(path: Path, slot: str):
    """Open a file in this computer's default app (the UI always runs on the same computer)."""
    try:
        if sys.platform == "win32":
            os.startfile(path)
        else:
            subprocess.run(["open" if sys.platform == "darwin" else "xdg-open", path], check=True)
    except Exception as e:
        st.session_state[f"flash-{slot}"] = (
            "error",
            f"Couldn't open {path.name} ({e}). Use Download instead.",
        )


def pdf_buttons(label: str, path: Path, key: str):
    """Open and Download buttons for a PDF, if it exists."""
    if path.exists():
        col_open, col_download, _ = st.columns([2, 2, 5])
        col_open.button(
            f"Open {label}", key=f"open-{key}", on_click=open_file, args=(path, key), type="primary"
        )
        col_download.download_button(
            "Download", path.read_bytes(), file_name=path.name, key=f"dl-{key}", on_click="ignore"
        )
        flash(key)


def folder_kind(path: Path) -> str:
    if not path.exists():
        return "new"
    if not path.is_dir():
        return "file"
    if (path / "contestants.csv").exists() or (path / "classes.yaml").exists():
        return "show"
    return "empty"


@st.dialog("Change data folder?", dismissible=False)
def confirm_folder(path: Path):
    st.code(str(path), language=None)
    kind = folder_kind(path)
    if kind == "file":
        st.error("That's a file, not a folder.")
    elif kind == "show":
        try:
            n = len(get_registrar(path).contestants())
            st.info(f"📂 This folder already has a show, with {n} registered entrants.")
        except Exception as e:
            st.warning(f"📂 This folder already has show files, but they can't be read: {e}")
    elif kind == "empty":
        st.info("📂 This folder already exists but has no show in it. A new show will start here.")
    else:
        st.info("🆕 This folder doesn't exist yet. It will be created for a new show.")
    labels = {"new": "Create folder and switch", "show": "Switch to this show"}
    col_ok, col_cancel = st.columns(2)
    if col_ok.button(labels.get(kind, "Switch"), type="primary", disabled=kind == "file"):
        path.mkdir(parents=True, exist_ok=True)
        st.session_state.location = str(path)
        message = {
            "new": "Created a new folder and switched to it.",
            "show": "Switched to the existing show in this folder.",
            "empty": "Switched to this folder (no show in it yet).",
        }[kind]
        st.session_state["flash-folder"] = ("success", f"✅ {message}")
        st.session_state.reset_location_input = True
        st.session_state.pop("pending_location", None)
        st.rerun()
    if col_cancel.button("Cancel"):
        st.session_state.reset_location_input = True
        st.session_state.pop("pending_location", None)
        st.rerun()


# endregion


# region changes (each is a button callback that reads its inputs from session state)
def register(location: Path) -> str:
    ss = st.session_state
    name = ss.reg_name.strip()
    check_name(name)
    existing = {c.contestant.name for c in get_registrar(location).contestants()}
    if name in existing and not ss.get("reg_merge"):
        raise ValueError(f"{name} is already registered. Tick the box to add these entries.")
    contestant = Contestant(name=name, classes=parse_classes(ss.reg_classes), paid=ss.reg_paid)
    get_registrar(location).register(contestant)
    ss.reg_name, ss.reg_classes, ss.reg_paid = "", "", 0.0
    ss.pop("reg_merge", None)
    return f"Registered {len(contestant.classes)} entries for {name}."


def allocate(location: Path) -> str:
    get_manager(location).allocate(get_registrar(location).contestants())
    get_manager(location).render_contestants(location / "render")
    st.session_state.pop("allocate_confirm", None)
    return "Entries allocated and entry slips generated."


def judge(location: Path, class_id: str, widget_keys: dict[str, str]) -> str:
    chosen = {place: st.session_state[key] for place, key in widget_keys.items()}
    every = [entry for entries in chosen.values() for entry in entries]
    if len(every) != len(set(every)):
        raise ValueError("An entry can only receive one award in a class.")
    as_ref = {
        place: [n if cid == class_id else (cid, n) for cid, n in entries]
        for place, entries in chosen.items()
    }
    get_manager(location).add_judgment(class_id=class_id, **as_ref)
    return f"Saved results for class {class_label(class_id)}."


def save_prizes(location: Path, prize_keys: dict[str, tuple[str, str | None]]) -> str:
    manager = get_manager(location)
    for prize, (class_key, entry_widget) in prize_keys.items():
        class_id = st.session_state.get(class_key)
        if class_id is None:
            manager.remove_prize(prize)
        elif entry_widget not in st.session_state:
            raise ValueError(f"Choose the winning entry for the {prize}.")
        else:
            entry = st.session_state[entry_widget]
            manager.add_prize(prize=prize, class_id=class_id, contestant_id=entry)
    return "Saved special prizes."


def final_report(location: Path) -> str:
    get_manager(location).render_final_report(location / "render")
    return "Results PDFs generated."


# endregion


st.set_page_config(page_title="Greenbook", page_icon="🥕", layout="wide")

ss = st.session_state
if "location" not in ss:
    default = os.getenv("GREENBOOK_LOCATION", "~/greenbook-data")
    ss.location = str(Path(default).expanduser().resolve())
if "location_input" not in ss or ss.pop("reset_location_input", False):
    ss.location_input = ss.location
location = Path(ss.location)


def location_changed():
    typed = Path(ss.location_input.strip() or ".").expanduser().resolve()
    if typed != Path(ss.location):
        ss.pending_location = typed


with st.sidebar:
    st.title("🥕 Greenbook")
    st.text_input(
        "Data folder",
        key="location_input",
        on_change=location_changed,
        help="Where this show's files are kept. Use a new folder for each year's show. "
        "Type a folder and press Enter to switch.",
    )
    flash("folder")
    st.caption(f"✅ Using `{location}`")
# Kept until the dialog's Switch or Cancel is pressed (the dialog can't be dismissed otherwise).
if pending := ss.get("pending_location"):
    confirm_folder(pending)

try:
    contestants = get_registrar(location).contestants()
    manager = get_manager(location)
except Exception as e:
    st.error(f"Couldn't read the show data in {location}: {e}")
    st.stop()

show = manager.show
show_classes = sorted(show.classes(), key=lambda c: class_sort_key(c.class_id)) if show else []
registered = Counter((c.contestant.name, cls) for c in contestants for cls in c.contestant.classes)
allocated = Counter((c.name, sc.class_id) for sc in show_classes for c in sc.contestants)
judged = [sc for sc in show_classes if is_judged(sc)]
render_dir = location / "render"

with st.sidebar:
    st.metric("Entrants", len(contestants))
    st.metric("Entries", sum(registered.values()))
    if not show:
        st.info("Not allocated yet")
    elif registered != allocated:
        st.warning("New registrations since the last allocation")
    else:
        st.success("Allocation up to date")
    if show_classes:
        st.progress(len(judged) / len(show_classes), f"{len(judged)}/{len(show_classes)} judged")

tab_entries, tab_allocate, tab_judging, tab_results, tab_lookup = st.tabs(
    ["Entries", "Allocation & slips", "Judging", "Results", "Lookup"]
)

# region entries
with tab_entries:
    st.subheader("Register an entrant")
    col_name, col_classes, col_paid = st.columns([2, 3, 1])
    col_name.text_input("Full name", key="reg_name")
    col_classes.text_input(
        "Classes",
        key="reg_classes",
        help="Class numbers separated by commas or spaces, e.g. `1, 14, 34A, 50, 50`. "
        "Repeat a class to enter it twice.",
    )
    col_paid.number_input("Paid (£)", key="reg_paid", min_value=0.0, step=0.1, format="%.2f")

    name = st.session_state.reg_name.strip()
    classes = parse_classes(st.session_state.reg_classes)
    problem = None
    if name or classes:
        try:
            check_name(name)
            if not classes:
                raise ValueError("Enter at least one class.")
            Contestant(name=name, classes=classes, paid=st.session_state.reg_paid)
        except ValueError as e:
            problem = str(e)
            st.error(problem)
    if classes and not problem:
        fee = entry_fee(classes)
        preview = pd.DataFrame({"Class": classes, "Name": [FLAT_CLASSES[c] for c in classes]})
        st.dataframe(preview, hide_index=True)
        st.caption(
            f"Entry fee {money(fee)} · paid {money(st.session_state.reg_paid)} · "
            f"due {money(fee - st.session_state.reg_paid)}"
        )

    names = {c.contestant.name for c in contestants}
    is_existing = name in names
    if is_existing:
        st.warning(f"{name} is already registered.")
        st.checkbox(f"Add these entries to {name}'s existing entries", key="reg_merge")
    elif similar := [n for n in names if n.casefold() == name.casefold()]:
        st.warning(f"Similar to existing entrant {similar[0]}. Check the spelling.")

    st.button(
        "Register",
        type="primary",
        disabled=bool(not name or not classes or problem)
        or (is_existing and not st.session_state.get("reg_merge")),
        on_click=act,
        args=("entries", location, register),
    )
    flash("entries")

    st.subheader(f"Registered entrants ({len(contestants)})")
    if contestants:
        rows = []
        for c in sorted(contestants, key=lambda c: c.contestant.name):
            fee = entry_fee(c.contestant.classes)
            rows.append(
                {
                    "Name": c.contestant.name,
                    "Classes": ", ".join(sorted(c.contestant.classes, key=class_sort_key)),
                    "Entries": len(c.contestant.classes),
                    "Fee": money(fee),
                    "Paid": money(c.contestant.paid),
                    "Due": money(fee - c.contestant.paid),
                }
            )
        st.dataframe(pd.DataFrame(rows), hide_index=True)
# endregion

# region allocation
with tab_allocate:
    st.write(
        "Allocation gives each entry its number in its class and makes one entry-slip PDF per "
        "entrant. Run it again after late registrations: existing entry numbers don't change."
    )
    has_results = bool(judged or (show and show.prizes))
    if has_results:
        st.warning("Judging has started. Allocating again will erase all results and prizes.")
        st.checkbox("I understand: erase all judging results and prizes", key="allocate_confirm")
    st.button(
        "Allocate entries and generate slips",
        type="primary",
        disabled=not contestants or (has_results and not st.session_state.get("allocate_confirm")),
        on_click=act,
        args=("allocate", location, allocate),
    )
    flash("allocate")

    names_allocated = sorted({c.name for c in show.unique_contestants()}) if show else []
    slips = [render_dir / f"{n}.pdf" for n in names_allocated if (render_dir / f"{n}.pdf").exists()]
    if slips:
        st.subheader("Entry slips")
        zipped = io.BytesIO()
        with zipfile.ZipFile(zipped, "w") as zf:
            for slip in slips:
                zf.write(slip, slip.name)
        st.download_button("Download all slips (ZIP)", zipped.getvalue(), "entry-slips.zip")
        slip = st.selectbox("Entrant", slips, format_func=lambda p: p.stem, key="slip_entrant")
        pdf_buttons(f"slip for {slip.stem}", slip, key="slip")
        st.caption(f"Slips are also saved in `{render_dir}`")
# endregion

# region judging
with tab_judging:
    if not show:
        st.info("Allocate entries first.")
    else:
        current = st.selectbox(
            "Class",
            show_classes,
            key="judge_class",
            format_func=lambda sc: f"{'✓ ' if is_judged(sc) else ''}{class_label(sc.class_id)} "
            f"({len(sc)} {'entry' if len(sc) == 1 else 'entries'})",
        )
        cid = current.class_id
        col_names, col_cross = st.columns(2)
        show_names = col_names.toggle(
            "Show entrant names", key="judge_names", help="Off: only entry numbers are shown."
        )
        cross = col_cross.toggle(
            "Include entries from other classes",
            key=f"cross-{cid}",
            help="Award a place here to an entry from another class. "
            "These appear as class-entry, e.g. 25A-3.",
        )
        saved = saved_results(current)
        results = results_by_entry(show)
        own_entries = [(cid, n) for n in range(1, len(current) + 1)]
        table = {"Entry": [n for _, n in own_entries]}
        if show_names:
            table["Name"] = [entry_name(show, key) for key in own_entries]
        table["Result"] = [results.get(key, "") for key in own_entries]
        st.dataframe(pd.DataFrame(table), hide_index=True)

        saved_keys = {key for keys in saved.values() for key in keys}
        others = [
            (sc.class_id, n)
            for sc in show_classes
            if sc.class_id != cid
            for n in range(1, len(sc) + 1)
        ]
        # Saved awards stay selectable even with the toggle off.
        options = own_entries + [k for k in others if cross or k in saved_keys]

        def option_label(key):
            label = str(key[1]) if key[0] == cid else f"{key[0]}-{key[1]}"
            return f"{label} – {entry_name(show, key)}" if show_names else label

        # Keys include the file's modification time so the widgets reload from disk after saving.
        version = (location / "classes.yaml").stat().st_mtime_ns
        widget_keys = {place: f"judge-{place}-{cid}-{cross}-{version}" for place in PLACES}
        # Keep unsaved picks when the toggle flips (the widgets are recreated under new keys).
        previous = {
            place: st.session_state[key]
            for place in PLACES
            if (key := f"judge-{place}-{cid}-{not cross}-{version}") in st.session_state
        }
        columns = st.columns(len(PLACES))
        for column, (place, label) in zip(columns, PLACES.items()):
            column.multiselect(
                label,
                options,
                default=[e for e in previous.get(place, saved[place]) if e in options],
                format_func=option_label,
                key=widget_keys[place],
                placeholder="None",
            )
        chosen = [entry for key in widget_keys.values() for entry in st.session_state[key]]
        duplicates = len(chosen) != len(set(chosen))
        if duplicates:
            st.error("An entry can only receive one award in a class.")
        st.button(
            "Save results",
            type="primary",
            disabled=duplicates,
            on_click=act,
            args=("judging", location, judge, cid, widget_keys),
        )
        flash("judging")

        st.subheader("Special prizes")
        st.caption("Prizes chosen by the judges. Choose the winning entry for each, then save.")
        awards = judged_prize_awards(show)
        class_ids = [None] + [sc.class_id for sc in show_classes]
        prize_keys = {}
        for prize in JUDGED_PRIZES:
            col_prize, col_class, col_entry = st.columns([2, 3, 2], vertical_alignment="center")
            col_prize.markdown(f"**{prize}**")
            awarded_class, awarded_entry = awards.get(prize, (None, 1))
            class_key = f"prize-class-{prize}-{version}"
            chosen = col_class.selectbox(
                f"Class for the {prize}",
                class_ids,
                index=class_ids.index(awarded_class),
                format_func=lambda c: "Not awarded" if c is None else class_label(c),
                key=class_key,
                label_visibility="collapsed",
            )
            entry_widget = None
            if chosen:
                prize_class = show.class_lookup(chosen)
                entry_widget = f"prize-entry-{prize}-{chosen}-{version}"
                col_entry.selectbox(
                    f"Entry for the {prize}",
                    range(1, len(prize_class) + 1),
                    index=awarded_entry - 1 if chosen == awarded_class else 0,
                    format_func=lambda n, sc=prize_class: f"Entry {n} – {sc.entry_lookup(n).name}"
                    if show_names
                    else f"Entry {n}",
                    key=entry_widget,
                    label_visibility="collapsed",
                )
            prize_keys[prize] = (class_key, entry_widget)
        st.button(
            "Save special prizes",
            type="primary",
            on_click=act,
            args=("prize", location, save_prizes, prize_keys),
        )
        flash("prize")
# endregion

# region results
with tab_results:
    if not judged:
        st.info("Results appear here once a class has been judged.")
    else:
        if remaining := [sc.class_id for sc in show_classes if not is_judged(sc)]:
            st.warning(f"Not judged yet: {', '.join(remaining)}")
        col_prizes, col_ranking = st.columns(2)
        with col_prizes:
            st.subheader("Prizes")
            prize_rows = [line.split(": ", 1) for line in manager.report_prizes()]
            st.dataframe(
                pd.DataFrame(prize_rows, columns=["Prize", "Winner"]),
                hide_index=True,
                height=35 * (len(prize_rows) + 1) + 3,  # show every prize without scrolling
            )
        with col_ranking:
            st.subheader("Points ranking")
            ranking = [(c.name, points) for c, points in manager.report_ranking()]
            st.dataframe(pd.DataFrame(ranking, columns=["Name", "Points"]), hide_index=True)

        children = [(c.name, money(amount)) for c, amount in manager.children_prize_money()]
        if children:
            st.subheader("Children's prize money")
            st.dataframe(pd.DataFrame(children, columns=["Name", "Prize money"]), hide_index=True)

        st.subheader("Class results")
        result_class = st.selectbox(
            "Class", show_classes, format_func=lambda sc: class_label(sc.class_id), key="res_class"
        )
        class_df = result_class.to_df().replace({"place": {"None": ""}}).astype(str)
        class_df.columns = class_df.columns.str.capitalize()
        st.dataframe(class_df, hide_index=True)

        st.subheader("Results PDFs")
        st.button(
            "Generate results PDFs",
            type="primary",
            on_click=act,
            args=("report", location, final_report),
        )
        flash("report")
        for report, label in REPORTS.items():
            pdf_buttons(label, render_dir / report, key=report)

        st.subheader("Class winners")
        st.download_button(
            "Download class winners (CSV)",
            # The byte-order mark makes Excel read characters like ” correctly.
            "\ufeff" + manager.class_winners().to_csv(index=False),
            "class-winners.csv",
            on_click="ignore",
        )
# endregion

# region lookup
with tab_lookup:
    if not show:
        st.info("Allocate entries first. Registered entrants are listed on the Entries tab.")
    else:
        st.subheader("Who is this entry?")
        col_class, col_entry = st.columns(2)
        look_class = col_class.selectbox(
            "Class", show_classes, format_func=lambda sc: class_label(sc.class_id), key="lk_cls"
        )
        number = col_entry.number_input(
            "Entry number",
            min_value=1,
            max_value=len(look_class),
            key=f"lk_num-{look_class.class_id}",
        )
        st.success(
            f"Class {look_class.class_id} entry {number}: **{look_class.entry_lookup(number)}**"
        )

        st.subheader("What did this person enter?")
        entries_by_contestant = show.contestant_entries()
        person = st.selectbox(
            "Entrant", sorted(entries_by_contestant), format_func=str, key="lk_person"
        )
        results = results_by_entry(show)
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Class": e.class_id,
                        "Name": e.name,
                        "Entry": e.contestant_id,
                        "Result": results.get((e.class_id, e.contestant_id), ""),
                    }
                    for e in sorted(
                        entries_by_contestant[person], key=lambda e: class_sort_key(e.class_id)
                    )
                ]
            ),
            hide_index=True,
        )

        st.subheader("Entries per class")
        counts = pd.DataFrame(
            [{"Class": sc.class_id, "Name": sc.name, "Entries": len(sc)} for sc in show_classes]
        )
        st.dataframe(counts, hide_index=True)
        st.download_button("Download as CSV", counts.to_csv(index=False), "entry-counts.csv")

        st.subheader("All entries")
        export = manager.to_df().dropna(axis=1, how="all")
        st.dataframe(export)
        st.caption("Rows are entry numbers, columns are classes.")
        st.download_button("Download as CSV", export.to_csv(), "export.csv", key="dl-export")
# endregion
