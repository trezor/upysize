from src.upysize.strategies.constants_local_only import local_only_constants

CODE = """\
from micropython import const

H = "hello"
X = const(1)
_Y = const(2)
Z = 4
ABC = const(5)

def main():
    abc = _Y + 23 + Z

    return abc * X
"""


def test_local_only_constants():
    res = local_only_constants(CODE)
    assert len(res) == 1
    assert res[0].name == "X"
    assert res[0].saved_bytes() == 4
