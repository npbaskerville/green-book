"""
The CLI module for the Greenbook application.
"""

import os
import logging
import argparse
from pathlib import Path

from greenbook import __version__
from greenbook.data.entries import Contestant
from greenbook.secretary.manager import Manager
from greenbook.secretary.registration import Registrar

ALLOWED_SCORES = [
    "1",
    "2",
    "3",
    "C",
]

_LOG = logging.getLogger(__name__)


def get_registrar(loc) -> Registrar:
    location = Path(loc) / "contestants.yaml"
    location.parent.mkdir(parents=True, exist_ok=True)
    return Registrar(ledger_loc=location)


def get_manager(loc) -> Manager:
    location = Path(loc) / "classes.yaml"
    location.parent.mkdir(parents=True, exist_ok=True)
    return Manager(ledger_loc=location)


def _handle_register(args):
    registrar = get_registrar(args.location)
    contestant = Contestant(name=args.name, classes=args.entries)
    registrar.register(contestant, allow_update=args.allow_update)


def _handle_allocate(args):
    registrar = get_registrar(args.location)
    manager = get_manager(args.location)
    manager.allocate(contestants=registrar.contestants())
    _handle_render_entrants(args)


def _handle_judge(args):
    manager = get_manager(args.location)
    manager.add_judgment(
        class_id=args.class_id,
        first=args.first,
        second=args.second,
        third=args.third,
        commendations=args.commendations,
    )


def _handle_lookup(args):
    manager = get_manager(args.location)
    contestant = manager.lookup_contestant(class_id=args.class_id, contestant_id=args.contestant_id)
    _LOG.info(f"Contestant {args.contestant_id} in class {args.class_id}: {contestant}")


def _handle_prizes(args):
    manager = get_manager(args.location)
    manager.report_prizes()


def _handle_export(args):
    registrar = get_registrar(args.location)
    manager = get_manager(args.location)
    export_dir = Path(args.location)
    export_dir.mkdir(parents=True, exist_ok=True)
    out_loc = Path(args.location) / "export"
    out_loc.mkdir(parents=True, exist_ok=True)
    registrar.to_csv(location=out_loc / "contestants.csv")
    manager.to_csv(location=out_loc / "classes.csv")


def _handle_ranking(args):
    manager = get_manager(args.location)
    manager.report_ranking()


def _handle_report_class(args):
    manager = get_manager(args.location)
    manager.report_class(class_id=args.class_id)


def _handle_render_entrants(args):
    location = Path(args.location)
    manager = get_manager(location)
    render_loc = location / "render"
    render_loc.mkdir(parents=True, exist_ok=True)
    manager.render_contestants(render_loc)


def _handle_final_report(args):
    manager = get_manager(args.location)
    render_loc = Path(args.location) / "render"
    manager.render_final_report(render_loc)


class CLI:
    def __init__(self):
        self._parser = argparse.ArgumentParser(
            description=f"Greenbook CLI version {__version__}",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        self._parser.add_argument(
            "--location",
            help="The local in which the Greenbook data are stored.",
            default=os.getenv("GREENBOOK_LOCATION", Path("~/greenbook-data").expanduser()),
        )
        subparsers = self._parser.add_subparsers(dest="command")
        self._add_registration(subparsers)
        self._add_allocation(subparsers)
        self._add_judging(subparsers)
        self._add_lookup(subparsers)
        self._add_prizes(subparsers)
        self._add_export(subparsers)
        self._add_ranking(subparsers)
        self._add_report_class(subparsers)
        self._add_final_report(subparsers)
        self._add_render_entrants(subparsers)

    def _add_registration(self, subparsers):
        parser = subparsers.add_parser("register", help="Register a new contestant.")
        parser.set_defaults(func=_handle_register)

        parser.add_argument(
            "--name", dest="name", help="The name of the contestant.", required=True
        )

        parser.add_argument(
            "--entries",
            dest="entries",
            required=False,
            type=lambda x: list(x.split(",")),
            help=("Comma-separated list of entry numbers for the contestant. "),
        )

        parser.add_argument(
            "--allow_update",
            dest="allow_update",
            action="store_true",
            help="Allow updating an existing contestant.",
            default=False,
        )

    def _add_allocation(self, subparsers):
        parser = subparsers.add_parser(
            "allocate",
            help="Allocate contestants to numbers inside classes.",
        )

        parser.set_defaults(func=_handle_allocate)

    def _add_judging(self, subparsers):
        parser = subparsers.add_parser(
            "judge",
            help="Add judging results for contestants.",
        )

        parser.set_defaults(func=_handle_judge)

        parser.add_argument(
            "--class",
            dest="class_id",
            help="The class being judged.",
            required=True,
            type=str,
        )

        parser.add_argument(
            "--first",
            dest="first",
            help="The first place contestant(s).",
            required=False,
            type=lambda x: list(map(int, x.split(","))),
            default=[],
        )
        parser.add_argument(
            "--second",
            dest="second",
            help="The second place contestant(s).",
            required=False,
            type=lambda x: list(map(int, x.split(","))),
            default=[],
        )
        parser.add_argument(
            "--third",
            dest="third",
            help="The third place contestant(s).",
            required=False,
            type=lambda x: list(map(int, x.split(","))),
            default=[],
        )
        parser.add_argument(
            "--commendations",
            dest="commendations",
            help="The commended contestant(s).",
            required=False,
            type=lambda x: list(map(int, x.split(","))),
            default=[],
        )

    def _add_lookup(self, subparsers):
        parser = subparsers.add_parser(
            "lookup",
            help="Look up contestant name from their ID in a class.",
        )

        parser.set_defaults(func=_handle_lookup)

        parser.add_argument(
            "--contestant_id",
            dest="contestant_id",
            help="The contestant being judged.",
            required=True,
            type=int,
        )

        parser.add_argument(
            "--class",
            dest="class_id",
            help="The class being judged.",
            required=True,
            type=str,
        )

    def _add_prizes(self, subparsers):
        parser = subparsers.add_parser(
            "prizes",
            help="List the recipients of all prizes.",
        )

        parser.set_defaults(func=_handle_prizes)

    def _add_export(self, subparsers):
        parser = subparsers.add_parser(
            "export",
            help="Export all data to CSV files.",
        )

        parser.set_defaults(func=_handle_export)

    def _add_ranking(self, subparsers):
        parser = subparsers.add_parser(
            "ranking",
            help="List the ranking of all contestants.",
        )

        parser.set_defaults(func=_handle_ranking)

    def _add_report_class(self, subparsers):
        parser = subparsers.add_parser(
            "report_class",
            help="List the ranking of all contestants in a class.",
        )

        parser.set_defaults(func=_handle_report_class)

        parser.add_argument(
            "--class",
            dest="class_id",
            help="The class being judged.",
            required=True,
            type=str,
        )

    def _add_final_report(self, subparsers):
        parser = subparsers.add_parser(
            "final_report",
            help="Generate the final report.",
        )

        parser.set_defaults(func=_handle_final_report)

    def _add_render_entrants(self, subparsers):
        parser = subparsers.add_parser(
            "render_entrants",
            help="Render the entrants to the show.",
        )

        parser.set_defaults(func=_handle_render_entrants)

    def run(self):
        args = self._parser.parse_args()
        args.func(args)


def run_cli():
    logging.basicConfig(level=logging.INFO)
    cli = CLI()
    cli.run()
