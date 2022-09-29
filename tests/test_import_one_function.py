from src.upy_size.strategies.import_one_function import one_function_import

CODE = """\
from micropython import const
from typing import TYPE_CHECKING
from message import MessageType2, OnlyInOneFunc, InFuncAndTypeHint
import ENUM, abc, cbor
from trezor import ui, wire, utils, paths
import decorators

if not utils.BITCOIN_ONLY:
    from apps.bitcoin import bitcoin

if TYPE_CHECKING:
    import HashBuilderList

nine = const(9)

def main(msg: MessageType1, xyz: InFuncAndTypeHint.abc):
    x = 54
    OnlyInOneFunc(
        xyz=x
    )
    trial()
    return MessageType2(x)

@decorators.decorator("hoho")
@decorators(paths.PATTERN_BIP44_PUBKEY)
def abc(x: int):
    decorators.hello()
    paths.validate_path(x)
    receive(InFuncAndTypeHint)
    send(InFuncAndTypeHint)
    return MessageType2(x)

class ABC(ui.Component, abc.Layout, Generic[K, V]):
    abc = ENUM.abc

    def _init__(self, x: int):
        self.x = const(x)

def print_builder(builder: HashBuilderList[cbor.CborSequence]) -> None:
    print(builder)

def trial(ctx: wire.Context = wire.DUMMY_CONTEXT):
    ui.show("hello")
    if not utils.BITCOIN_ONLY:
        ui.show("hello altcoin")
    relay: HashBuilderList[cbor.CborSequence] = []
    wire.send("ola")
    return ENUM.xyz
"""


def test_one_function_import():
    res = one_function_import(CODE)
    assert len(res) == 2

    assert res[0].symbol == "OnlyInOneFunc"
    assert res[0].func.name == "main"
    assert res[0].used_as_type_hint is False
    assert res[0].usages_in_func == 1
    assert res[0].saved_bytes() == 4

    assert res[1].symbol == "InFuncAndTypeHint"
    assert res[1].func.name == "abc"
    assert res[1].used_as_type_hint is True
    assert res[1].usages_in_func == 2
    assert res[1].saved_bytes() == 6
