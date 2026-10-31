# Plan: local web UI and easy cross-platform install for Greenbook

## Goals

- A local, single-user browser UI that covers the existing functionality: entries, allocation and entry slips, judging, manual prizes, results PDFs and basic lookups.
- As little new code as possible. The UI calls the existing `Registrar` and `Manager` classes and adds no new business logic.
- Robust and friendly: clear error messages instead of tracebacks, nothing that silently destroys data, and automatic backups.
- One-command install on macOS, Linux and Windows, with no conda.

Out of scope: multi-user use, authentication, hosting, changes to scoring or prizes, and redesigning the PDF layouts.

## Key decisions

| Decision | Choice | Why |
|---|---|---|
| UI framework | **Streamlit** | Pure Python, one file, built-in tables, forms and download buttons. No HTML, JS or REST layer to maintain. |
| UI structure | One file, `src/greenbook/ui/app.py`, using `st.tabs` | Simplest to read and maintain. Multi-page apps add files and routing for no gain. |
| State | None held in the UI. Every action builds a fresh `Registrar` or `Manager` from disk. | Fits Streamlit's rerun model. The CSV and YAML files stay the single source of truth, so the CLI and UI can be used side by side. |
| Packaging and install | **uv** (`uv tool install`) from the GitHub repo | One installer for every OS. It fetches the right Python automatically, and it's the same command on Windows, macOS and Linux. |
| Dependency definition | `setup.cfg` only, for users | Removes the need for conda-lock for end users. |

Estimated size: about 300 lines for the UI, about 20 for the launcher, about 30 lines of fixes to the core, and about 60 lines of tests.

## Current state (findings from reading the code)

Tests pass on Python 3.13: 5 passed and 2 skipped. These issues affect the UI work:

1. **Bug: judging a class erases manual prizes.** `Show.update_class` builds `Show(list(classes.values()))` without passing `self._prizes`. I reproduced it: `manual_prize`, then `judge` on another class, and the prize is gone from `classes.yaml`. One-line fix.
2. **`allocate` overwrites `classes.yaml` and wipes all judging and prizes.** The README mentions `--confirm_reallocation`, but it doesn't exist. The UI needs a guard (see "Allocation" below).
3. **No delete or amend.** The README documents `delete --name`, but the CLI has no such command and the related tests are skipped as "deprecated". `DeletedContestant` exists and `render_contestants` already skips it, but nothing creates one.
4. **Missing dependencies.** `setup.cfg` lists only `pandas` and `attrs`. `ruamel.yaml` and `matplotlib` are imported but come only from conda, so `pip install` / `uv tool install` would give a broken install.
5. **Unhelpful validation errors.** `Contestant.__post_init__` uses bare `assert`s for the two-word name, max 2 entries per class and non-negative paid checks, so users would see an empty `AssertionError`. `validate_ledger` also builds a `ValueError` for negative payments without raising it.
6. **Final report crashes before any judging.** `MBShield.winner` indexes `sorted_contestants[0]` on an empty list.
7. **Stale docs and CI.** The README refers to `--show_name`, `delete` and `--confirm_reallocation`, none of which exist. CI sets up Python 3.10 (the package requires 3.12 or later), runs Linux only and depends on conda.
8. **Threading.** Streamlit runs scripts in a worker thread, and matplotlib's default macOS backend crashes outside the main thread. The UI must force the `Agg` backend. This is also the right choice on Windows and Linux.

Known limitations to leave alone for now: the ranking and prize PDFs are a single page and will overflow with many contestants (more than about 18 in the ranking).

## Implementation phases

### Phase 0: core fixes (small and independent; worth doing first)

All in existing files, each with a unit test:

- `Show.update_class`: pass the prizes through (`return Show(list(classes.values()), self._prizes)`).
- `Contestant.__post_init__`: replace the asserts with `ValueError`s that carry readable messages, for example "Name must include first and last name", "At most 2 entries per class (class 50 has 3)" or "Unknown class 99".
- `validate_ledger`: add the missing `raise`.
- `MBShield.winner`: return `[]` when nobody has points.
- `setup.cfg` `install_requires`: add `ruamel.yaml`, `matplotlib` and `streamlit`. Add `greenbook-ui = greenbook.ui.launch:main` to `console_scripts`.

### Phase 1: deletion ("withdraw entrant")

This is needed for "amend an entrant", which the README workflow relies on.

- Add `Registrar.withdraw(name)`, about 10 lines. It renames that contestant's ledger rows to `DELETED (<name>)` and saves.
- In `Registrar.contestants()`, build a `DeletedContestant` when the name starts with `DELETED (`.
- **Why a tombstone instead of dropping rows:** entry numbers come from the cumulative row order of the ledger. Dropping rows would renumber every later entrant's slips after they've been printed. A tombstone keeps every number stable, and the existing `DeletedContestant` code already expects this. To amend someone, withdraw them and register again; their new entries get fresh numbers at the end of each class.
- Re-enable and update the skipped deletion test.

### Phase 2: the UI (`src/greenbook/ui/app.py`)

Shared pieces at the top of the file (about 50 lines):

- `matplotlib.use("Agg")` before anything imports pyplot.
- **Data folder** in the sidebar: a text input defaulting to `$GREENBOOK_LOCATION`, otherwise `~/greenbook-data` (the same default as the CLI). Show the resolved absolute path. The same folder works with the CLI.
- **Status panel** in the sidebar: number of entrants and entries, whether entries are allocated, how many classes are judged out of the total, and a warning when `contestants.csv` is newer than `classes.yaml` ("New registrations since last allocation; re-allocate to include them").
- `run(action, success_msg)`: wraps every write. It first copies `contestants.csv` and `classes.yaml` to `backups/<timestamp>/` (about 8 lines). It then runs the action and shows `st.success`, or shows `st.error(str(e))` instead of a traceback.
- Class labels come from `FLAT_CLASSES`, for example `25A – Pompom Dahlias`. They're used everywhere a class is chosen.

**Tab 1: Entries**

- Form fields: name, entries and amount paid. Entries are typed as text exactly like the CLI (`1,14,34A,50,50`), because that's fastest when copying from paper forms. A live preview table below shows each class name and the count, and flags unknown classes. It also shows the amount due, using the existing `ENTRY_COST` and `FREE_CLASSES` rules. Submit calls `Registrar.register`.
- Registering an existing name adds entries to that person. The form says so and asks for confirmation with a checkbox, so a typo can't silently merge two people.
- Entrants table from `Registrar.contestants()`: name, classes, paid, due and balance.
- **Withdraw entrant:** choose a name, tick to confirm, then call `Registrar.withdraw`.

**Tab 2: Allocation and entry slips**

- An "Allocate and generate entry slips" button calls `Manager.allocate` and then `render_contestants` into `render/`, as the CLI does.
- **Guard:** if any class has judging results or there are manual prizes, the button is disabled until the user ticks "I understand this erases all judging results". The backup is taken in any case.
- Download buttons: one per entrant's slip PDF, plus "Download all as ZIP" (about 5 lines using `zipfile`).

**Tab 3: Judging**

- Choose a class from those allocated. The label shows ✓ when the class has been judged.
- Table of the entries in that class (entry number and name). This doubles as the judge's lookup sheet.
- Four multiselects (1st, 2nd, 3rd, Commended) whose options are the entry numbers in the class, labelled `3 – Bob Beetroot`. They're pre-filled with any existing results, so re-judging edits rather than starts over (`add_judgment` already replaces a class's results).
- Before saving, warn if the same entry appears in more than one place.
- **Manual prize** form: class, entry number and prize name, which calls `Manager.add_prize`. Below it, a list of the manual prizes awarded so far.
- Cross-class awards (the CLI's `--first=25A:3`): leave them out of the UI at first (see open questions). The CLI keeps supporting them.

**Tab 4: Results**

- On screen: the trophy winners (`report_prizes`) and the points ranking (`report_ranking`) as tables. They're shown only once at least one class is judged.
- A "Generate results PDFs" button calls `render_final_report` into `render/`, with download buttons for the class, prize and ranking PDFs.
- Results for each class: choose a class and show `ShowClass.to_df()`.

**Tab 5: Lookup**

- **Who is entry N in class X?** Choose a class and an entry number to see the name (`lookup_contestant`).
- **What did this person enter?** Choose a name to see their classes, entry numbers and any results (from `contestant_entries`).
- **Entries per class:** `entry_count()` as a table, plus a CSV download.
- **Full export:** `to_df()` with a CSV download (the same as `greenbook export`).
- Before allocation, the name lookup falls back to registration data (classes only, no entry numbers yet).

### Phase 3: launcher (`src/greenbook/ui/launch.py`, about 20 lines)

```python
def main():
    from streamlit.web import cli as stcli
    app = Path(__file__).with_name("app.py")
    sys.argv = ["streamlit", "run", str(app),
                "--server.address=localhost",          # local only
                "--browser.gatherUsageStats=false",
                "--server.headless=false"]             # open the browser
    sys.exit(stcli.main())
```

Optional: `--location` passes through to the app via `GREENBOOK_LOCATION`.

### Phase 4: install experience (macOS, Linux and Windows)

End-user instructions for the README:

1. Install uv, once.
   - macOS and Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Windows (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
2. Install Greenbook: `uv tool install git+https://github.com/npbaskerville/green-book`. uv downloads Python 3.12 automatically if needed.
3. Run: `greenbook-ui`, which opens the browser. The `greenbook` CLI is installed alongside it.
4. Update: `uv tool upgrade greenbook`.

Optional extra (about 10 lines in total): double-click launchers in `launchers/`. These are `Greenbook.command` for macOS, `Greenbook.bat` for Windows and `greenbook.sh` for Linux. Each installs uv if it's missing and runs `greenbook-ui`. Caveat: macOS Gatekeeper may warn about a downloaded `.command` file the first time.

Cross-platform details to handle:

- Use `pathlib` everywhere. It's already used, so the default folder resolves to `C:\Users\<you>\greenbook-data` on Windows.
- Contestant names become PDF filenames. Reject `\ / : * ? " < > |` in names in the UI, since these are invalid on Windows.
- Force the matplotlib `Agg` backend (see Phase 2).
- No shell-specific code. The launcher is pure Python.

Developer setup: keep `environment.yml` and `conda-lock` for now if you like them. Optionally replace them later with `uv sync --extra testing`, so dependencies are defined in one place.

### Phase 5: tests and CI

- **UI smoke test** (about 50 lines) with `streamlit.testing.v1.AppTest`, pointed at a temporary data folder. It registers two entrants, allocates, judges a class, adds a manual prize, generates the final report, then checks that the PDFs exist, the prize survives and no exceptions were rendered.
- Unit tests for the Phase 0 and Phase 1 fixes.
- **CI:** replace the conda workflow with a matrix of `ubuntu-latest`, `macos-latest` and `windows-latest` on Python 3.12. It runs `pip install -e .[testing]` and then `pytest`. This proves the install works on Windows without anyone needing a Windows machine.

### Phase 6: docs

- Rewrite the README with the install steps (Phase 4), a short "using the web UI" section with the show-day workflow (register, allocate and print slips, judge, results PDFs), and the CLI reference with stale options removed or corrected.

## Suggested order and pull requests

1. **PR 1:** Phase 0 core fixes and the dependency fixes, plus tests. Low risk and useful even without the UI.
2. **PR 2:** Phase 1 withdraw entrant.
3. **PR 3:** Phases 2 and 3, the UI and launcher, with the smoke test.
4. **PR 4:** Phases 4 to 6, the install docs, cross-platform CI and the optional launchers.

## Open questions

1. **Deletion semantics.** I recommend tombstones so printed slip numbers never change (Phase 1). The alternative is a true delete that renumbers later entrants.
2. **Cross-class awards** (`--first=25A:3`). How often are they used? If they're needed on show day, they can be added as an "entry from another class" field (about 15 lines).
3. **Streamlit as a required dependency or an optional `[ui]` extra.** I recommend required, so there's a single install command.
4. **Conda for development.** Keep it, or switch to uv so dependencies live in one place?
5. **One folder per show.** Should the UI default to a folder per year (for example `~/greenbook-data/2026`) so last year's data is never mixed in, or keep the CLI's single default?
