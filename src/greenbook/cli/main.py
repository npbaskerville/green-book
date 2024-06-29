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


def get_registrar(args) -> Registrar:
    location = Path(args.location) / "contestants.yaml"
    location.parent.mkdir(parents=True, exist_ok=True)
    return Registrar(ledger_loc=location)


def get_manager(args) -> Manager:
    location = Path(args.location) / "classes.yaml"
    location.parent.mkdir(parents=True, exist_ok=True)
    return Manager(ledger_loc=location)


def _handle_register(args):
    registrar = get_registrar(args)
    contestant = Contestant(name=args.name, classes=args.entries)
    registrar.register(contestant, allow_update=args.allow_update)


def _handle_allocate(args):
    registrar = get_registrar(args)
    manager = get_manager(args)
    manager.allocate(contestants=registrar.contestants, allow_reallocate=args.confirm_reallocate)


def _handle_judge(args):
    manager = get_manager(args)
    firsts = [
        manager.lookup_contestant(class_number=args.class_id, contestant_id=contestant_id)
        for contestant_id in args.first
    ]
    seconds = [
        manager.lookup_contestant(class_number=args.class_id, contestant_id=contestant_id)
        for contestant_id in args.second
    ]

    thirds = [
        manager.lookup_contestant(class_number=args.class_id, contestant_id=contestant_id)
        for contestant_id in args.third
    ]

    commendations = [
        manager.lookup_contestant(class_number=args.class_id, contestant_id=contestant_id)
        for contestant_id in args.commendations
    ]

    manager.add_judgment(
        show_number=args.class_id,
        first=firsts,
        second=seconds,
        third=thirds,
        commendations=commendations,
    )


def _handle_lookup(args):
    manager = get_manager(args)
    contestant = manager.lookup_contestant(
        class_number=args.class_id, contestant_id=args.contestant_id
    )
    _LOG.info(f"Contestant {args.contestant_id} in class {args.class_id}: {contestant}")


def _handle_prizes(args):
    manager = get_manager(args)
    manager.report_prizes()


def _handle_export(args):
    registrar = get_registrar(args)
    manager = get_manager(args)
    export_dir = Path(args.location)
    export_dir.mkdir(parents=True, exist_ok=True)
    registrar.to_csv(location=args.location / "contestants.csv")
    manager.to_csv(location=args.location / "classes.csv")


def _handle_ranking(args):
    manager = get_manager(args)
    manager.report_ranking()


class CLI:
    def __init__(self):
        self._parser = argparse.ArgumentParser(
            description=f"Greenbook CLI version {__version__}",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        self._parser.add_argument(
            "--location",
            help="The local in which the Greenbook data are stored.",
            default=os.getenv("GREENBOOK_LOCATION", Path("~/greenbook-data").resolve()),
        )
        self._parser.add_argument(
            "--name", help="The name of the show being managed.", required=True
        )

        subparsers = self._parser.add_subparsers(dest="command")
        self._add_registration(subparsers)
        self._add_allocation(subparsers)
        self._add_judging(subparsers)
        self._add_lookup(subparsers)
        self._add_prizes(subparsers)
        self._add_export(subparsers)
        self._add_ranking(subparsers)

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
            type=lambda x: list(map(int, x.split(","))),
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

        parser.add_argument(
            "--confirm_reallocate",
            dest="confirm_reallocate",
            action="store_true",
            help="Confirm the reallocation of contestants to numbers.",
            default=False,
        )

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
            type=int,
        )

        parser.add_argument(
            "--first",
            dest="first",
            help="The first place contestant(s).",
            required=True,
            type=lambda x: list(map(int, x.split(","))),
        )
        parser.add_argument(
            "--second",
            dest="second",
            help="The second place contestant(s).",
            required=True,
            type=lambda x: list(map(int, x.split(","))),
        )
        parser.add_argument(
            "--third",
            dest="third",
            help="The third place contestant(s).",
            required=True,
            type=lambda x: list(map(int, x.split(","))),
        )
        parser.add_argument(
            "--commendations",
            dest="commendations",
            help="The commended contestant(s).",
            required=True,
            type=lambda x: list(map(int, x.split(","))),
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
            type=int,
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

        parser.add_argument(
            "--location",
            help="The directory to which the data should be exported.",
            required=True,
        )

    def _add_ranking(self, subparsers):
        parser = subparsers.add_parser(
            "ranking",
            help="List the ranking of all contestants.",
        )

        parser.set_defaults(func=_handle_ranking)

    def run(self):
        args = self._parser.parse_args()
        args.func(args)
