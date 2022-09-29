from src.upy_size.strategies.keyword_arguments import keyword_arguments

CODE = """\
import layouts
from layouts import show


def main(msg: MessageType1, xyz):
    x = 54
    layouts.main("abc")
    return show("abc", num=3)

def abc(x: int):
    return layouts.warn(title="abc", num=x)
"""


def test_keyword_arguments():
    res = keyword_arguments(CODE)
    assert len(res) == 2

    assert res[0].name == "show"
    assert res[0].saved_bytes() == 3

    assert res[1].name == "warn"
    assert res[1].saved_bytes() == 6
