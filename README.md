# Greenbook - village show management app

Greenbook handles a village show from start to finish: registering entrants, numbering their
entries and printing entry slips, recording the judging, and producing the results PDFs.

## Installation

Greenbook runs on Windows, macOS and Linux. Installation uses [uv](https://docs.astral.sh/uv/),
which also downloads the right version of Python for you.

1. Install uv (once).

   macOS or Linux, in Terminal:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
   Windows, in PowerShell:
   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```
   Then close and reopen the terminal.

2. Install Greenbook:
   ```bash
   uv tool install git+https://github.com/npbaskerville/green-book
   ```

To update to the latest version later, run `uv tool upgrade greenbook`.

## Using the web app

```bash
greenbook-ui
```

This opens Greenbook in your web browser. It runs only on your computer: nothing is sent
anywhere, and closing the terminal window stops it. The show's files are kept in
`~/greenbook-data` (on Windows, `C:\Users\<you>\greenbook-data`). To change the folder, type
it in the sidebar and press Enter, then confirm; you'll be told whether it holds an existing
show or will be a new one. You can also start with `greenbook-ui --location <folder>`. Use a
new folder for each year's show.

Work through the tabs in order:

1. **Entries**: type each entrant's name, their classes (e.g. `1, 14, 34A, 50, 50`; repeat a
   class to enter it twice) and what they've paid. The fee and amount due are worked out for
   you. To add entries for someone already registered, register them again under the same name.
2. **Allocation & slips**: once entries close, allocate them. This numbers every entry within
   its class and makes one entry-slip PDF per entrant, which you can download individually or
   as a ZIP. Late registrations can be allocated later without changing existing numbers.
3. **Judging**: on the day, choose a class and pick the 1st, 2nd, 3rd and commended entries.
   Only entry numbers are shown unless you turn on *Show entrant names*.
   Turn on *Include entries from other classes* to award a place to an entry from another
   class. Special prizes, such as the Wonky Wooden Spoon, are awarded at the bottom.
4. **Results**: trophy winners, the points ranking and each class's results. *Generate results
   PDFs* makes the final reports. *Open* shows a PDF in your computer's PDF viewer, ready to
   print.
5. **Lookup**: find who an entry belongs to, what a person entered, and entry counts per class.

Before every change, a copy of the show's files is saved under `backups/` in the data folder.

## Command line

Everything can also be done from the command line, and the two can be mixed. Run
`greenbook --help` for all commands. Each command takes an optional `--location` (default:
`$GREENBOOK_LOCATION` or `~/greenbook-data`), which is omitted below.

### Registration
Run this every time you want to add a new contestant.
```bash
greenbook register --name "John Smith" --entries=1,14,34A,50,50 --paid 0.5
```

### Class allocation
Run this after entries have closed. It numbers the entries and writes one entry-slip PDF per
contestant. Running it again erases any judging results.
```bash
greenbook allocate
```

### Judging
Run this on the day of the show to record the results of the judging. To award a place to an
entry from another class, write it as `CLASS:ENTRY`, e.g. `--third=25A:1`.
```bash
greenbook judge --class 42 --first=31 --second=14,27 --commendations=50
```

## Development

```bash
pip install -e ".[testing]"
pytest
```

### Full worked example
```bash
# register
greenbook  --location /Users/nick/green-book-testing-29aug register --name "Aunt Dahlia" --entries=4,5,39,40,41,42,43,45,53,65 --paid 0.5
greenbook  --location /Users/nick/green-book-testing-29aug register --name "Bettie Beetroot" --entries=1,2,2,5,17,35,47,56,56,65
greenbook  --location /Users/nick/green-book-testing-29aug register --name "Major Marrow" --entries=21,22,30,33,39,40,41,42,43,44,45,46,47,68
greenbook  --location /Users/nick/green-book-testing-29aug register --name "Sean Shortbread" --entries=25A,21,22,30,44,59A
greenbook  --location /Users/nick/green-book-testing-29aug register --name "Tommy Tomato" --entries=4,22,33,33,44,46,47,53,56,56,59A,52
greenbook  --location /Users/nick/green-book-testing-29aug register --name "Willy Wilja" --entries=25A,26,26,21,44,46,47,53,59A,65
greenbook  --location /Users/nick/green-book-testing-29aug register --name "Baby Carrot" --entries=70,72

# run this any time to get entry slips
greenbook  --location /Users/nick/green-book-testing-29aug allocate

# To add more entries for an existing entrant, register them again with the same name:
greenbook  --location /Users/nick/green-book-testing-29aug register --name "Aunt Dahlia" --entries=35,44,65
greenbook  --location /Users/nick/green-book-testing-29aug allocate


# judging
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 1 --first=1
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 2 --first=2 --second=1
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 4 --first=1 --commendations=2
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 5
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 17 --first=1

greenbook  --location /Users/nick/green-book-testing-29aug judge --class 21 --first=3 --second=1 --third=2
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 22 --first=2 --second=1 --third=3

greenbook  --location /Users/nick/green-book-testing-29aug judge --class 25A --first=1
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 26 --first=1 --commendations=2
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 30
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 33 --first=3 --second=1 --third=2

greenbook  --location /Users/nick/green-book-testing-29aug judge --class 35  --commendations=1

greenbook  --location /Users/nick/green-book-testing-29aug judge --class 39 --second=1 --first=2
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 40 --second=1 --first=2
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 41 --second=1 --first=2
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 42 --second=2 --first=1
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 43 --first=2 --commendations=1
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 44 --first=1 --second=3 --third=2 --commendations=4,5
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 45

greenbook  --location /Users/nick/green-book-testing-29aug judge --class 46 --second=1 --first=2
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 47 --first=3
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 52 --first=1

greenbook  --location /Users/nick/green-book-testing-29aug judge --class 53 --first=2 --second=1 --third=3
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 56 --commendations=3

greenbook  --location /Users/nick/green-book-testing-29aug judge --class 59A --first=1 --third=2 --second=3
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 65 --first=1 --commendations=2 --second=3 --third=4
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 68 --first=1

greenbook  --location /Users/nick/green-book-testing-29aug judge --class 70 --first=1
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 72 --first=1

greenbook --location /Users/nick/green-book-testing-29aug manual_prize --class 65 --contestant_id 2 --prize "Wonky Wooden Spoon"

# final
greenbook  --location /Users/nick/green-book-testing-29aug final_report
```
