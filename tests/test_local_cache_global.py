from src.upysize.strategies.local_cache_global import local_cache_global

CODE = """\
import messages
import enum
from writer import write_int

def main(msg: MessageType1, xyz) -> messages.MessageType2:
    x = 54
    enum.MessageType3(xyz=x)
    abc(1)
    abc(1)
    y = messages.MessageType2(xyz=x)
    y = messages.MessageType4(xyz=x)
    return messages.MessageType2(x)

def abc(x: int):
    write_int(x)
    write_int(4)
    write_int(1)
    write_int(1)
    return messages.MessageType2(x)

def defg(x: int):
    abc(1)
    abc(1)
    abc(1)

def local_import_do_not_flag(x: int):
    from writer import write_int
    write_int(x)
    write_int(4)
    write_int(1)
    write_int(1)
"""


def test_local_cache_global():
    res = local_cache_global(CODE, threshold=3)
    assert len(res) == 3

    assert res[0].func.name == "main"
    assert res[0].cache_candidate.cache_string == "messages"
    assert res[0].cache_candidate.amount == 3
    assert res[0].saved_bytes() == 2

    assert res[1].func.name == "abc"
    assert res[1].cache_candidate.cache_string == "write_int"
    assert res[1].cache_candidate.amount == 4
    assert res[1].saved_bytes() == 4

    assert res[2].func.name == "defg"
    assert res[2].cache_candidate.cache_string == "abc"
    assert res[2].cache_candidate.amount == 3
    assert res[2].saved_bytes() == 2
