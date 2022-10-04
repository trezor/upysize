from src.upysize.strategies.small_classes import init_only_classes

CODE = """\
from message import MessageType2, MessageType3

class NameSize:
    ABC = 1

    def __init__(self, name: str, size: int):
        self.name = name
        self.size = size

class BIGClass:
    ABC = 1

    def __init__(self, name: str, size: int):
        self.name = name
        self.size = size

    def show(self):
        print(self.name, self.size)

class ExceptionDoNotCare(Exception):
    pass

def main(msg: MessageType1, xyz):
    x = 54
    return NameSize("abc", 3)

def abc(x: int):
    return MessageType2(x)
"""


def test_small_classes():
    res = init_only_classes(CODE)
    assert len(res) == 1
    assert res[0].name == "NameSize"
    assert res[0].saved_bytes() == 0
