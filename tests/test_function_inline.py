from src.upysize.strategies import Settings
from src.upysize.strategies.function_inline import function_inline

CODE = """\
from helpers import Obj

def main(abc, xyz):
    x = 54
    used_also_elsewhere(x)
    _used_more_than_once(x)
    Obj.send(x)
    return _function_to_inline(x)

def _function_to_inline(x):
    return x * x

def _used_more_than_once(x):
    return x * x

def used_also_elsewhere(x):
    _used_more_than_once(x)
    return x * x

class ABC:
    def __init__(self, x):
        super().__init__(x)
"""


def test_function_inline():
    SETTINGS = Settings(not_inlineable_funcs=["used_also_elsewhere"])

    res = function_inline(CODE, SETTINGS)
    assert len(res) == 1
    assert res[0].func.name == "_function_to_inline"
    assert res[0].saved_bytes() == 50
