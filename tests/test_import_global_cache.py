from src.upy_size.strategies.import_global_cache import global_import_cache

CODE = """\
import messages
import enum

senf(messages.MessageType2)

def main(msg: MessageType1, xyz):
    x = 54
    enum.MessageType3(xyz=x)
    send(messages.enum.store)
    y = messages.MessageType2(xyz=x)
    return messages.MessageType2(x)

def abc(x: int):
    return messages.MessageType2(x)
"""


def test_global_import_cache():
    res = global_import_cache(CODE)
    assert len(res) == 1
    assert res[0].cache_candidate.cache_string == "messages.MessageType2"
    assert res[0].cache_candidate.amount == 4
    assert res[0].saved_bytes() == 4
