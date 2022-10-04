import ast
from typing import Type

from src.upysize.strategies.helpers import (
    all_functions,
    all_global_symbols,
    all_nodes_outside_of_function,
    all_nontype_toplevel_symbol_usages,
    all_toplevel_functions,
    all_toplevel_imported_symbols,
    all_toplevel_nodes,
    all_toplevel_symbol_usages,
    all_type_hint_usages,
    get_func_local_attribute_lookups,
    get_function_call_amounts,
    get_function_name,
    get_global_attribute_lookups,
    get_node_code,
    get_used_func_import_symbols,
    get_used_func_symbols,
    get_variable_name,
    is_attr_modified,
    is_really_a_constant,
    is_symbol_assigned,
    is_used_as_type_hint,
    is_used_outside_function,
    remove_type_annotation,
)

CODE = """\
from micropython import const
from typing import TYPE_CHECKING
from message import MessageType2, MessageType3
from enums import Enum1 as ENUM
import trezor.crypto
from abc import *

HASH_LENGTH = const(32)

if TYPE_CHECKING:
    from message import MessageType1

def main(msg: MessageType1, xyz):
    x = 54  # some comment here
    # other comment
    MessageType3(xyz=x)

    MessageType2(
        xyz=x
    )

    return MessageType2(x)

def abc(x: ENUM):
    return x.ABC + 3
"""


def test_all_toplevel_imported_symbols():
    toplevel_imports = all_toplevel_imported_symbols(CODE)
    assert len(toplevel_imports) == 7
    for item in (
        "MessageType2",
        "MessageType3",
        "ENUM",
        "const",
        "trezor.crypto",
        "TYPE_CHECKING",
        "*",
    ):
        assert item in toplevel_imports


def test_all_global_symbols():
    global_symbols = all_global_symbols(CODE)
    assert len(global_symbols) == 10
    for item in (
        "MessageType2",
        "MessageType3",
        "ENUM",
        "HASH_LENGTH",
        "const",
        "trezor.crypto",
        "TYPE_CHECKING",
        "main",
        "abc",
        "*",
    ):
        assert item in global_symbols


def test_get_node_code():
    toplevel_nodes = all_toplevel_nodes(CODE)
    assert len(toplevel_nodes) == 10

    first_node_code = get_node_code(CODE, toplevel_nodes[0])
    assert first_node_code == "from micropython import const"

    last_node_code = get_node_code(CODE, toplevel_nodes[-1])
    assert (
        last_node_code
        == """\
def abc(x: ENUM):
    return x.ABC + 3"""
    )


CODE2 = """\
from micropython import const
from messages import MessageType1, MessageType2
import messages
from enums import Enum1 as ENUM

HASH_LENGTH = const(32)

ABC = ENUM.ABC
MT = messages.MessageType3

def helper(x: str) -> str:
    send(MT(xyz=x))
    return str[::-1]

def main(msg: MessageType1) -> None:
    helper("abcd")
    helper("gdfg")
    res = helper("error")
    item = ENUM.ABC
    return MessageType2(xyz=res, abc=item, length=HASH_LENGTH)
"""


def test_get_used_func_symbols():
    toplevel_nodes = all_toplevel_nodes(CODE2)
    main_func_node = toplevel_nodes[-1]
    assert isinstance(main_func_node, ast.FunctionDef)
    symbols = get_used_func_symbols(main_func_node)
    assert symbols == {
        "helper": 3,
        "MessageType2": 1,
        "ENUM": 1,
        "HASH_LENGTH": 1,
        "res": 1,
        "item": 1,
    }


def test_get_used_func_import_symbols():
    toplevel_nodes = all_toplevel_nodes(CODE2)
    func_node = toplevel_nodes[-1]
    assert isinstance(func_node, ast.FunctionDef)
    symbols = get_used_func_import_symbols(CODE2, func_node)
    assert symbols == {
        "MessageType2": 1,
        "ENUM": 1,
    }


def test_toplevel_symbol_usages():
    usages = all_toplevel_symbol_usages(CODE2)
    assert usages == {
        "helper": 3,
        "ENUM": 2,
        "HASH_LENGTH": 1,
        "messages": 1,
        "const": 1,
        "MessageType2": 1,
        "MessageType1": 1,
    }


def test_nontype_toplevel_symbol_usages():
    usages = all_nontype_toplevel_symbol_usages(CODE2)
    assert usages == {
        "helper": 3,
        "ENUM": 2,
        "HASH_LENGTH": 1,
        "messages": 1,
        "const": 1,
        "MessageType2": 1,
    }


CODE3 = """\
HASH_LENGTH = 32
_ABC = "abc"
counter = 0

def main() -> None:
    global _ABC, counter
    _ABC  = "def"
    counter += HASH_LENGTH
"""


def test_is_really_a_constant():
    assert is_really_a_constant(CODE3, "HASH_LENGTH")
    assert not is_really_a_constant(CODE3, "counter")
    assert not is_really_a_constant(CODE3, "_ABC")


CODE4 = """\
import messages
import enum

def main(msg: messages.MessageType1, xyz) -> messages.MessageType2:
    x = 54
    enum.MessageType3(xyz=x)
    send(messages.enum.store)
    y: messages.MessageType2 = messages.MessageType2(xyz=x)
    return messages.MessageType2(x)

def abc(x: int):
    return messages.MessageType2(x)
"""


def test_get_global_attribute_lookups():
    lookups = get_global_attribute_lookups(CODE4, include_type_hints=True)
    assert lookups == {
        "messages": {
            "MessageType2": 5,
            "MessageType1": 1,
            "enum": 1,
        },
        "enum": {
            "MessageType3": 1,
        },
    }

    lookups = get_global_attribute_lookups(CODE4, include_type_hints=False)
    assert lookups == {
        "messages": {
            "MessageType2": 3,
            "enum": 1,
        },
        "enum": {
            "MessageType3": 1,
        },
    }


CODE5 = """\
from typing import TYPE_CHECKING
from message import MessageType2, MessageType3, SpecialType
import messages
from enums import Enum1, Enum2
import trezor.crypto

if TYPE_CHECKING:
    from message import MessageType1

def main(msg: MessageType1[bytes], xyz) -> list[MessageType2]:
    x = 54
    abc: SpecialType[Enum2.ABC] = SpecialType(xyz=x)
    MessageType3(xyz=x)
    res: MessageType2 = MessageType2(xyz=x)
    res2: list[MessageType2] = [MessageType2(xyz=x)]
    return res

def abc(x: Enum1, y: messages.MessageType66):
    return x.ABC + 3
"""


def test_all_type_hint_usages():
    usages = all_type_hint_usages(CODE5)
    assert usages == {
        "Enum1": 1,
        "Enum2": 1,
        "MessageType1": 1,
        "MessageType2": 3,
        "messages": 1,
        "SpecialType": 1,
        "list": 2,
        "bytes": 1,
    }


def test_is_used_as_type_hint():
    assert is_used_as_type_hint(CODE5, "Enum1")
    assert is_used_as_type_hint(CODE5, "Enum2")
    assert is_used_as_type_hint(CODE5, "SpecialType")
    assert is_used_as_type_hint(CODE5, "messages")
    assert not is_used_as_type_hint(CODE5, "MessageType3")
    assert not is_used_as_type_hint(CODE5, "TYPE_CHECKING")
    assert not is_used_as_type_hint(CODE5, "trezor.crypto")


CODE6 = """\
import messages
from messages import MyMessage, MyMsg2

def my_func(ctx, msg: MyMsg2) -> messages.MyMessage:
    # comment not to take msg.abc
    new_list = []
    assert msg.abc is not None
    msg.abc = 3
    new_list.append(4)
    new_list.append(abc(msg.abc))
    x = msg.abc.xyz
    y = msg.xyz
    return messages.MyMessage(abc=msg.abc)
"""


def test_get_func_local_attribute_lookups():
    toplevel_nodes = all_toplevel_nodes(CODE6)
    func_node = toplevel_nodes[-1]
    assert isinstance(func_node, ast.FunctionDef)
    lookups = get_func_local_attribute_lookups(CODE6, func_node)
    assert lookups == {
        "msg": {
            "abc": 5,
            "xyz": 1,
        },
        "new_list": {
            "append": 2,
        },
    }


def test_attr_gets_modified():
    toplevel_nodes = all_toplevel_nodes(CODE6)
    func_node = toplevel_nodes[-1]
    assert isinstance(func_node, ast.FunctionDef)
    assert is_attr_modified(func_node, "msg", "abc") is True
    assert is_attr_modified(func_node, "msg", "xyz") is False


CODE7 = """\
import messages, utils, abc, paths
from messages import MSG1, default_msg
from . import CURVE, PATTERNS, SLIP44_ID
HASH_LENGTH = 32
_LOCAL_CONST = 42
counter = 0

if utils.should_do():
    do()

if abc:
    do()

TMP = _LOCAL_CONST + 1

@decorator
@decorator.abc
@decorator(counter)
@decorator(*PATTERNS, slip44_id=SLIP44_ID, curve=CURVE)
@decorator(paths.PATTERN_BIP44_PUBKEY)
async def main(
    msg: messages.ABC, second: MSG1,
    another: default_msg = default_msg()
) -> Awaitable[MSG1]:
    utils.report(msg)
    new = 4 + 5
    paths.validate_path(msg.path)
    counter += TMP
    await send(MSG1.ABC)
"""


def test_all_nodes_outside_of_function():
    all_nodes = all_nodes_outside_of_function(CODE7)

    def _assert_node_count(node_class: Type[ast.AST], count: int) -> None:
        assert sum(1 for node in all_nodes if isinstance(node, node_class)) == count

    _assert_node_count(ast.Assign, 4)
    _assert_node_count(ast.Call, 3)
    _assert_node_count(ast.If, 2)
    _assert_node_count(ast.Import, 0)
    _assert_node_count(ast.ImportFrom, 0)
    _assert_node_count(ast.FunctionDef, 0)
    _assert_node_count(ast.AsyncFunctionDef, 0)
    _assert_node_count(ast.Module, 0)


def test_is_used_outside_function():
    assert is_used_outside_function(CODE7, "_LOCAL_CONST")
    assert is_used_outside_function(CODE7, "utils")
    assert is_used_outside_function(CODE7, "abc")
    assert is_used_outside_function(CODE7, "counter")
    assert is_used_outside_function(CODE7, "paths")
    assert is_used_outside_function(CODE7, "PATTERNS")
    assert is_used_outside_function(CODE7, "SLIP44_ID")
    assert is_used_outside_function(CODE7, "CURVE")
    assert is_used_outside_function(CODE7, "default_msg")
    assert not is_used_outside_function(CODE7, "MSG1")
    assert not is_used_outside_function(CODE7, "messages")
    assert not is_used_outside_function(CODE7, "TMP")
    assert not is_used_outside_function(CODE7, "HASH_LENGTH")


CODE8 = """\
import show, get
from messages import MyMessage, MyMsg2

def helper():
    pass

def my_func(ctx, msg: MyMsg2) -> messages.MyMessage:
    show("abc")
    if get("error"):
        show("error")
    helper()

class ABC:
    def __init__(self, x: int):
        super().__init__(x)
        self.x = self.abc(x)

    def abc(self, x: int) -> int:
        res = my_func(self.ctx, self.msg)
        return x + 1
"""


def test_get_function_call_amounts():
    func_calls = get_function_call_amounts(CODE8)
    assert func_calls == {
        "show": 2,
        "get": 1,
        "my_func": 1,
        "helper": 1,
        "super": 1,
    }


def test_remove_type_annotation():
    def _get_tree_size(node: ast.AST) -> int:
        return sum(1 for _ in ast.walk(node))

    original_tree = ast.parse(CODE8)
    orig_size = _get_tree_size(original_tree)
    modified_tree = remove_type_annotation(original_tree)
    assert _get_tree_size(original_tree) > _get_tree_size(modified_tree)
    assert _get_tree_size(original_tree) == orig_size


def test_all_functions():
    all_funcs = all_functions(CODE8)
    toplevel_funcs = all_toplevel_functions(CODE8)
    assert len(all_funcs) == 4
    assert len(toplevel_funcs) == 2


def test_get_variable_name():
    toplevel_nodes = all_toplevel_nodes(
        """\
HASH_LENGTH = 32
_LOCAL_CONST = 42
counter = 0
"""
    )
    for i, var_name in enumerate(("HASH_LENGTH", "_LOCAL_CONST", "counter")):
        node = toplevel_nodes[i]
        assert isinstance(node, ast.Assign)
        assert get_variable_name(node) == var_name


def test_get_function_name():
    tree = ast.parse(
        """\
res = utils.abc()
show("abc")
super().__init__(x)
"""
    )
    call_nodes = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    for i, var_name in enumerate(("abc", "show", "__init__", "super")):
        node = call_nodes[i]
        assert get_function_name(node) == var_name


def test_is_symbol_assigned():
    toplevel_nodes = all_toplevel_nodes(
        """\
def abc(ctx, msg):
    res = 1
    msg = msg2
"""
    )
    func_node = toplevel_nodes[-1]
    assert isinstance(func_node, ast.FunctionDef)
    assert is_symbol_assigned(func_node, "res")
    assert is_symbol_assigned(func_node, "msg")
    assert not is_symbol_assigned(func_node, "ctx")
