import pytest

import subprocess
from pathlib import Path
from datetime import datetime


class TestCLI:
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

    @pytest.fixture
    def base_cli_invocation(self, out_dir):
        return ["greenbook", "--location", str(out_dir.absolute())]

    def test_cli(self, base_cli_invocation):
        commands = []
        registrations = [
            ("Aunt Dahlia", "35,4,5,39,40,41,42,43,44,45,53,65,65", 0.5),
            ("Bettie Beetroot", "1,2,2,5,17,35,47,56,56,65", 0.0),
        ]
        register_cmds = [
            [
                *base_cli_invocation,
                "register",
                f"--name={name}",
                f"--entries={classes}",
                f"--paid={paid}",
            ]
            for name, classes, paid in registrations
        ]
        commands.extend(register_cmds)
        commands.append([*base_cli_invocation, "allocate"])

        judging = [
            ("1", "--first=1"),
            ("35", "--first=2", "--second=1"),
            ("2", "--first=1", "--second=2"),
        ]
        judging_cmds = [
            [*base_cli_invocation, "judge", "--class", class_id, *places]
            for class_id, *places in judging
        ]

        prize_cmds = [
            [
                *base_cli_invocation,
                "manual_prize",
                "--contestant_id=1",
                "--prize=Wonky Wooden Spoon",
            ],
        ]

        commands.extend(judging_cmds)
        commands.extend(prize_cmds)

        commands.append([*base_cli_invocation, "final_report"])

        # run the CLI via subprocess
        for cmd in commands:
            subprocess.run(cmd, check=True)
