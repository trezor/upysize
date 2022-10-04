from src.upysize.strategies.import_type_only import type_only_import

CODE = """\
from typing import TYPE_CHECKING
from message import MessageType2, MessageType3, OnlyType
from enums import Enum1
import cbor, HashBuilderList
import trezor.crypto

if TYPE_CHECKING:
    from message import MessageType1


def print_builder(builder: HashBuilderList[cbor.CborSequence]) -> None:
    print(builder)

def main(msg: MessageType1, xyz) -> MessageType2:
    x = 54
    MessageType3(xyz=x)
    res: MessageType2 = MessageType2(xyz=x)
    relay: HashBuilderList[cbor.CborSequence] = HashBuilderList()
    return res

def abc(x: Enum1, y: messages.MessageType66):
    res: OnlyType = get_message()
    return x.ABC + 3
"""


def test_type_only_import():
    res = type_only_import(CODE)
    assert len(res) == 3

    assert res[0].symbol == "OnlyType"
    assert res[0].saved_bytes() == 7

    assert res[1].symbol == "Enum1"
    assert res[1].saved_bytes() == 7

    assert res[2].symbol == "cbor"
    assert res[2].saved_bytes() == 7
