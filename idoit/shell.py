"""Implementation of ``idoit-cli shell`` command.

Lists the constants.
"""

import argparse
import shlex
import typing

import attr
import columnize
import inflect
from ishell.command import Command
from ishell.console import Console
from ishell.utils import _print
from logzero import logger

from .api import Client
from .common import pprint


class InterfaceConsole(Command):
    """Interface Console.
    Parameters:
    interface name -- Press tab for options
    """

    def args(self):
        return ["FastEthernet0/0", "FastEthernet1/0"]

    def run(self, line):
        interface = line.split()[-1]
        self.interface = interface
        self.prompt = "RouterA(config-if-%s)" % self.interface
        self.prompt_delim = "#"
        ip = Command("ip", help="Configure ip parameters: address")
        address = Command("address")
        address.run = self.set_address
        self.addChild(ip).addChild(address)
        self.loop()

    def set_address(self, line):
        addr = line.split()[-1]
        _print("Setting interface %s address %s" % (self.interface, addr))


class RouteAdd(Command):
    """RouteAdd Command.
    Parameters:
    network gateway - Example: ip route add 10.0.0.0/8 192.168.0.1
    """

    def run(self, line):
        _print("Route added!")


class ConfigureTerminal(Command):
    """Configure Console.
    Childs:
    interface -- Configure mode for interface
    ip --  IP configuration: route add
    """

    def run(self, line):
        self.prompt = "RouterA(config)"
        self.prompt_delim = "#"
        ip = Command("ip", help="Set ip configurations")
        route = Command("route")
        add = RouteAdd("add")

        interface = InterfaceConsole(
            "interface", dynamic_args=True, help="Configure interface parameters"
        )

        self.addChild(interface)
        self.addChild(ip).addChild(route).addChild(add)
        self.loop()


class Show(Command):
    """Show Command.
    Childs:
    running-config -- Show RAM configuration
    startup-config --  Show NVRAM configuration
    """

    def args(self):
        return ["running-config", "startup-config"]

    def run(self, line):
        arg = line.split()[-1]
        if arg not in self.args():
            _print("%% Invalid argument: %s" % arg)
            _print("\tUse:")
            _print("\trunning-config -- Show RAM configuration")
            _print("\tstartup-config --  Show NVRAM configuration")
            return
        _print("Executing show %s..." % arg)


class Enable(Command):
    """Enable Command"""

    def run(self, line):
        self.prompt = "i-doit"
        self.prompt_delim = "#"

        configure = Command("configure", help="Enter configure mode")
        terminal = ConfigureTerminal("terminal")
        configure.addChild(terminal)
        show = Show("show", help="Show configurations", dynamic_args=True)
        self.addChild(configure)
        self.addChild(show)
        self.loop()


def _retrieve_json(json_path: typing.List[str], obj: typing.Dict[str, typing.Any]) -> typing.Any:
    """Retrieve object from nested dicts."""
    if json_path:
        return _retrieve_json(json_path[1:], obj[json_path[0]])
    else:
        return obj


class BaseCommand(Command):
    """Base command class."""

    nargs: typing.Optional[int] = None

    def __init__(self, config, client, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config
        self.client = client

    def run(self, line):
        self.validate(line)
        arr = shlex.split(line.strip())
        self.execute(arr)

    def execute(self, arr):
        raise NotImplementedError("Abstract method called.")

    def validate(self, line):
        arr = shlex.split(line.strip())
        if len(arr) != self.nargs + 1:
            logger.error("USAGE: %s <term>", self.name)
            return


class Search(BaseCommand):
    """``search <term>``"""

    nargs = 1

    def run(self, line):
        self.validate(line)
        arr = shlex.split(line.strip())
        self.execute(arr)

    def execute(self, arr):
        pprint(self.client.query("idoit.search", params={"q": arr[1]}))


class SimpleCommand(BaseCommand):

    nargs = 0
    name: typing.Optional[str] = None
    command: typing.Optional[str] = None

    def execute(self, arr):
        result = self.run_query(arr)
        pprint(_retrieve_json(self.config.json_path, result["result"]))

    def run_query(self, arr):
        return self.client.query(self.command, params=self.get_query_params(arr))

    def get_query_params(self, arr: typing.List[str]):
        return {}


class Version(SimpleCommand):
    """``version``"""

    name = "version"
    command = "idoit.version"


class Constants(SimpleCommand):
    """``constants <term>``"""

    name = "constants"
    command = "idoit.constants"


class GenericCommand(SimpleCommand):
    def __init__(self, object_type, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.object_type = object_type


class ListCommand(GenericCommand):

    nargs = 1
    name = "list"
    command = "cmdb.objects.read"

    def execute(self, arr):
        if self.config.print_raw_json:
            return super().execute(arr)
        else:
            p = inflect.engine()
            res = self.run_query(arr)
            max_title_len = max((len(obj["title"]) for obj in res["result"]))
            print(
                "Listing all (%d) %s\n"
                % (len(res["result"]), p.plural(self.client.object_types[self.object_type]))
            )
            print(columnize.columnize([self._label(obj, max_title_len) for obj in res["result"]]))

    def _label(self, obj, max_title_len):
        if self.object_type:
            return ("%% 5d/%% %ds" % max_title_len) % (obj["id"], obj["title"])
        else:
            return ("%% 5d/%% %ds %%- 10s" % max_title_len) % (
                obj["id"],
                obj["title"],
                "(%s/%d)" % (obj["type_title"], obj["type"]),
            )

    def get_query_params(self, arr):
        if self.object_type:
            return {"filter": {"type": self.object_type}, "order_by": "title"}
        else:
            return {"order_by": "title"}


class ShowCommand(GenericCommand):
    nargs = 2
    name = "show"
    command = "cmdb.object"

    def execute(self, arr):
        if self.config.print_raw_json:
            return super().execute(arr)
        else:
            res = self.run_query(arr)["result"]
            if res["objecttype"] != self.object_type:
                logger.warn(
                    "Expected object type %s/%s but was %s/%s",
                    self.object_type,
                    self.client.object_types[self.object_type],
                    res["objecttype"],
                    self.client.object_types[res["objecttype"]],
                )
            print(
                "Showing details of %s: %s\n"
                % (self.client.object_types[self.object_type], res["title"])
            )
            fmt = "  %%- %ds : %%s" % max((len(key) for key in res))
            for key, value in sorted(res.items()):
                print(fmt % (key, value))
            print()

    def get_query_params(self, arr):
        return {"id": arr[-1]}


@attr.s(auto_attribs=True, frozen=True)
class Config:
    #: Path to query if tokens are given.
    json_path: typing.Tuple[str, ...] = ()
    #: Print raw JSON
    print_raw_json: bool = False


def run(args, parser, subparser):
    """Main entry point for constants command."""
    config = Config(
        json_path=() if not args.json_path else tuple(args.json_path.split(".")),
        print_raw_json=args.print_raw_json,
    )

    with Client(args.idoit_url, args.idoit_user, args.idoit_password, args.idoit_api_key) as client:
        console = Console("i-doit")

        search = Search(config, client, "search", help="Search for a term. Ex: search term")
        version = Version(config, client, "version", help="Show versions")
        constants = Constants(config, client, "constants", help="Show constants")

        console.addChild(search)
        console.addChild(version)
        console.addChild(constants)

        for object_type, object_type_name in client.object_types.items():
            cmd = Command(object_type_name, help="Management of data type %s" % object_type_name)
            cmd.addChild(ListCommand(object_type, config, client, "list"))
            cmd.addChild(ShowCommand(object_type, config, client, "show"))
            console.addChild(cmd)

        if args.tokens:
            console.walk_and_run(" ".join(args.tokens))
        else:
            console.loop()


def setup_argparse(parser: argparse.ArgumentParser) -> None:
    """Main entry point for subcommand."""

    parser.add_argument(
        "--print-raw-json", action="store_true", default=False, help="Print raw JSON"
    )
    parser.add_argument(
        "--json-path", "-p", help="Dot-separated path in JSON to extract (when tokens are given)"
    )

    parser.add_argument("tokens", nargs="*", help="Command tokens to execute.")
