"""Implementation of ``idoit-cli shell`` command.

Lists the constants.
"""

import argparse
import json
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
        if not self.validate(line):
            return False
        arr = shlex.split(line.strip())
        self.execute(arr)

    def execute(self, arr):
        raise NotImplementedError("Abstract method called.")

    def validate(self, line):
        arr = shlex.split(line.strip())
        if len(arr) != self.nargs + 1:
            logger.error("USAGE: %s <term>", self.name)
            return False
        else:
            return True


class EnableCommand(BaseCommand):
    """Start update"""

    def run(self, line):
        self.prompt = "i-doit"
        self.prompt_delim = "#"

        configure = Command("configure", help="Enter configure mode")
        for object_type, object_type_name in self.client.object_types.items():
            obj_cmd = ConfigureCommand(
                object_type, self.config, self.client, object_type_name, dynamic_args=True
            )
            configure.addChild(obj_cmd)

        self.addChild(configure)
        self.loop()


class Search(BaseCommand):
    """``search <term>``"""

    nargs = 1

    def run(self, line):
        if not self.validate(line):
            return
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


class OneObjectCommand(GenericCommand):
    def args(self):
        x = [
            "%s/%s" % (res["id"], res["title"])
            for res in self.client.query(
                "cmdb.objects.read", params={"filter": {"type": self.object_type}}
            )["result"]
        ]
        return x


class SetCommand(Command):
    def __init__(self, values, client, config, parent, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.values = values
        self.client = client
        self.config = config
        self.parent = parent

    def args(self):
        return list(self.values.keys())

    def run(self, line):
        arr = shlex.split(line.strip())
        logger.debug("setting %s to %s", arr[-2], arr[-1])
        self.parent.append_update(arr[-2], arr[-1])


class ShowConfiguredCommand(Command):
    def __init__(self, values, client, config, parent, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.values = values
        self.client = client
        self.config = config
        self.parent = parent

    def run(self, line):
        values = dict(self.values)
        updated = []
        for k, v in self.parent.updates.items():
            updated.append(k)
            values[k] = v
        _show(self.config, self.client.object_types[self.parent.object_type], values, set(updated))


class StoreConfiguredCommand(Command):
    def __init__(self, values, client, config, parent, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.values = values
        self.client = client
        self.config = config
        self.parent = parent

    def run(self, line):
        forbidden = ("id", "sysid", "created", "updated")
        patch = {k: v for k, v in self.parent.updates.items() if k not in forbidden}
        patch["id"] = self.values["id"]
        logger.info("applying updates %s", patch)

        resp = self.client.query("cmdb.object.update", params=patch)
        for key, value in patch.items():
            self.parent.values[key] = value
        logger.info("response: %s", resp)
        self.parent.updates = {}


class ResetConfiguredCommand(Command):
    def __init__(self, values, client, config, parent, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.values = values
        self.client = client
        self.config = config
        self.parent = parent

    def run(self, line):
        forbidden = ("id", "sysid", "created", "updated")
        patch = {k: v for k, v in self.parent.updates.items() if k not in forbidden}
        logger.info("Discarding updates\n%s" % json.dumps(patch, indent="  "))
        self.parent.updates = {}


class ConfigureCommand(OneObjectCommand):
    nargs = 2
    name = "configure"
    command = "cmdb.object"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.updates = {}

    def append_update(self, key, value):
        self.updates[key] = value

    def run(self, line):
        arr = shlex.split(line.strip())
        resp = self.client.query("cmdb.object.read", params={"id": arr[-1]})
        res = resp["result"]
        label = "%s/%s" % (res["id"], res["title"])

        self.prompt = "%s(%s)" % (self.client.object_types[self.object_type], label)
        self.prompt_delim = "#"

        set_ = SetCommand(
            res, self.client, self.config, self, "set", dynamic_args=True, help="Set value"
        )
        show = ShowConfiguredCommand(
            res, self.client, self.config, self, "show", help="Show values"
        )
        store = StoreConfiguredCommand(
            res, self.client, self.config, self, "store", help="Apply updates"
        )
        reset = ResetConfiguredCommand(
            res, self.client, self.config, self, "reset", help="Discard updates"
        )
        # TODO: reload from server (refresh)

        self.addChild(set_)
        self.addChild(show)
        self.addChild(store)
        self.addChild(reset)
        self.loop()

        # forbidden = ("id", "sysid", "created", "updated")
        # patch = {k: v for k, v in self.updates.items() if k not in forbidden}
        # patch["id"] = res["id"]
        # logger.info("applying updates %s", patch)
        #
        # resp = self.client.query("cmdb.object.update", params=patch)
        # logger.info("response: %s", resp)


def _show(config, object_type, res, updated=None):
    updated = updated or ()
    print("Showing details of %s: %s\n" % (object_type, res["title"]))
    fmt = "  %%- %ds  %%s %%s" % (max((len(key) for key in res)),)
    for key, value in sorted(res.items()):
        print(fmt % (key, "->" if key in updated else " :", value))
    print()


class ShowCommand(OneObjectCommand):
    nargs = 2
    name = "show"
    command = "cmdb.object"

    def execute(self, arr):
        if self.config.print_raw_json:
            return super().execute(arr)
        else:
            res = self.run_query(arr)["result"]
            if not res:
                logger.warn("Found no such %s", self.client.object_types[self.object_type])
                return
            if res["objecttype"] != self.object_type:
                logger.warn(
                    "Expected object type %s/%s but was %s/%s",
                    self.object_type,
                    self.client.object_types[self.object_type],
                    res["objecttype"],
                    self.client.object_types[res["objecttype"]],
                )
        _show(self.config, self.client.object_types[self.object_type], res)

    def get_query_params(self, arr):
        return {"id": arr[-1]}


@attr.s(auto_attribs=True, frozen=True)
class Config:
    #: Path to query if tokens are given.
    json_path: typing.Tuple[str, ...] = ()
    #: Print raw JSON
    print_raw_json: bool = False


def add_read_commands(client, config, cmd):
    for object_type, object_type_name in client.object_types.items():
        obj_cmd = Command(object_type_name, help="Management of data type %s" % object_type_name)
        obj_cmd.addChild(ListCommand(object_type, config, client, "list"))
        obj_cmd.addChild(ShowCommand(object_type, config, client, "show", dynamic_args=True))
        cmd.addChild(obj_cmd)


def run(args, parser, subparser):
    """Main entry point for constants command."""
    config = Config(
        json_path=() if not args.json_path else tuple(args.json_path.split(".")),
        print_raw_json=args.print_raw_json,
    )

    with Client(args.idoit_url, args.idoit_user, args.idoit_password, args.idoit_api_key) as client:
        console = Console("i-doit")

        enable = EnableCommand(config, client, "enable", help="Enter edit mode")
        search = Search(config, client, "search", help="Search for a term. Ex: search term")
        version = Version(config, client, "version", help="Show versions")
        constants = Constants(config, client, "constants", help="Show constants")

        console.addChild(enable)
        console.addChild(search)
        console.addChild(version)
        console.addChild(constants)

        add_read_commands(client, config, console)
        add_read_commands(client, config, enable)

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
