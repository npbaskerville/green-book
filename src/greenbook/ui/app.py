"""
Local web UI for Greenbook. Start it with `greenbook-ui`.

The UI holds no state of its own: every run reads the show from the data folder, and every
change goes through the same Registrar/Manager calls as the CLI, so the two can be mixed.
"""

import io
import os
import re
import pandas as pd
import shutil
import zipfile
import streamlit as st
import matplotlib
from pathlib import Path
from datetime import datetime
from collections import Counter

from greenbook.cli.main import get_manager, get_registrar
from greenbook.data.show import Show, ShowClass
from greenbook.data.entries import Contestant
from greenbook.definitions.prices import entry_fee
from greenbook.definitions.classes import FLAT_CLASSES

# Streamlit runs the script off the main thread, where GUI backends (e.g. macOS) crash.
matplotlib.use("Agg")

PLACES = {"first": "1st", "second": "2nd", "third": "3rd", "commendations": "Commended"}
BAD_NAME_CHARS = set('\\/:*?"<>|')  # names become PDF filenames, and Windows rejects these
REPORTS = ["final-class-report.pdf", "final-prize-report.pdf", "final-ranking-report.pdf"]


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


def download(label: str, path: Path, **kwargs):
    if path.exists():
        st.download_button(label, path.read_bytes(), file_name=path.name, **kwargs)


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


def add_prize(location: Path, class_id: str, entry_widget: str) -> str:
    prize = st.session_state.prize_name.strip()
    if not prize:
        raise ValueError("Enter the name of the prize.")
    number = st.session_state[entry_widget]
    get_manager(location).add_prize(prize=prize, class_id=class_id, contestant_id=number)
    st.session_state.prize_name = ""
    return f"Awarded {prize} to entry {number} in class {class_id}."


def final_report(location: Path) -> str:
    get_manager(location).render_final_report(location / "render")
    return "Results PDFs generated."


# endregion


st.set_page_config(page_title="Greenbook", page_icon="🥕", layout="wide")

with st.sidebar:
    st.title("🥕 Greenbook")
    default_location = os.getenv("GREENBOOK_LOCATION", str(Path("~/greenbook-data").expanduser()))
    location_text = st.text_input(
        "Data folder",
        value=default_location,
        help="Where this show's files are kept. Use a new folder for each year's show.",
    )
    location = Path(location_text).expanduser().resolve()

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
        download(f"Download slip for {slip.stem}", slip)
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
        saved = saved_results(current)
        results = results_by_entry(show)
        own_entries = [(cid, n) for n in range(1, len(current) + 1)]
        st.dataframe(
            pd.DataFrame(
                {
                    "Entry": [n for _, n in own_entries],
                    "Name": [entry_name(show, key) for key in own_entries],
                    "Result": [results.get(key, "") for key in own_entries],
                }
            ),
            hide_index=True,
        )

        saved_keys = {key for keys in saved.values() for key in keys}
        cross = st.toggle(
            "Include entries from other classes",
            value=any(c != cid for c, _ in saved_keys),
            key=f"cross-{cid}",
            help="Award a place here to an entry from another class. "
            "These appear as class-entry, e.g. 25A-3.",
        )
        others = [
            (sc.class_id, n)
            for sc in show_classes
            if sc.class_id != cid
            for n in range(1, len(sc) + 1)
        ]
        # Saved awards stay selectable even with the toggle off.
        options = own_entries + [k for k in others if cross or k in saved_keys]

        def option_label(key):
            if key[0] == cid:
                return f"{key[1]} – {entry_name(show, key)}"
            return f"{key[0]}-{key[1]} – {entry_name(show, key)}"

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
        st.caption("Prizes outside the standard trophies, e.g. the Wonky Wooden Spoon.")
        col_class, col_entry, col_prize = st.columns([3, 2, 3])
        prize_class = col_class.selectbox(
            "Class",
            show_classes,
            format_func=lambda sc: class_label(sc.class_id),
            key="prize_class",
        )
        entry_widget = f"prize_entry-{prize_class.class_id}"
        col_entry.selectbox(
            "Entry",
            range(1, len(prize_class) + 1),
            format_func=lambda n: f"{n} – {prize_class.entry_lookup(n).name}",
            key=entry_widget,
        )
        col_prize.text_input("Prize", key="prize_name")
        st.button(
            "Award prize",
            on_click=act,
            args=("prize", location, add_prize, prize_class.class_id, entry_widget),
        )
        flash("prize")
        if show.prizes:
            awarded = [
                {"Prize": prize, "Winner": contestant.name, "Class": class_label(class_id)}
                for contestant, class_id, prize in show.prizes
            ]
            st.dataframe(pd.DataFrame(awarded), hide_index=True)
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
            st.dataframe(pd.DataFrame(prize_rows, columns=["Prize", "Winner"]), hide_index=True)
        with col_ranking:
            st.subheader("Points ranking")
            ranking = [(c.name, points) for c, points in manager.report_ranking()]
            st.dataframe(pd.DataFrame(ranking, columns=["Name", "Points"]), hide_index=True)

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
        for report in REPORTS:
            download(f"Download {report}", render_dir / report, key=f"dl-{report}")
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
