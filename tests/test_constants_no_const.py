from src.upy_size.strategies.constants_no_const import no_const_number

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


def test_no_const_number():
    res = no_const_number(CODE)
    assert len(res) == 1
    assert res[0].name == "Z"
    assert res[0].saved_bytes() == 4
