from __future__ import annotations

import ast
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Iterable, Iterator, Type

from typing_extensions import TypeAlias, TypeGuard

if TYPE_CHECKING:  # pragma: no cover
    FuncAst: TypeAlias = ast.FunctionDef | ast.AsyncFunctionDef  # type: ignore
    ImportAst: TypeAlias = ast.Import | ast.ImportFrom  # type: ignore


FUNC_ASTS = (ast.FunctionDef, ast.AsyncFunctionDef)
IMPORT_ASTS = (ast.Import, ast.ImportFrom)

# Caching results of frequently called functions
# (those starting with "all" prefix), as some of those
# are called from multiple validators/strategies, always
# with the same input (file content).
# Small size is enough because at one time, only one file
# is being processed.
cache = lru_cache(maxsize=4)


@dataclass
class Function:
    """Basic information about a function definition."""

    name: str
    loc: int
    line_no: int
    node: FuncAst

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.line_no} :: {self.name} ({self.loc} LOC)"

    @classmethod
    def from_node(cls, node: FuncAst) -> Function:
        return cls(
            name=node.name,
            loc=int(node.end_lineno or 0) - node.lineno,
            line_no=node.lineno,
            node=node,
        )


@dataclass
class CacheCandidate:
    """String/attribute lookup that can be cached."""

    cache_string: str
    amount: int

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.cache_string} ({self.amount}x)"


@dataclass
class SymbolUsageInFunction:
    """How many times a symbol is used in a function."""

    func: Function
    usages: int


@cache
def all_nodes(file_content: str) -> list[ast.AST]:
    """All AST nodes in the file."""
    return list(ast.walk(ast.parse(file_content)))


@cache
def all_toplevel_nodes(file_content: str) -> list[ast.AST]:
    """All module's top-level AST nodes in the file."""
    return list(ast.parse(file_content).body)


@cache
def all_global_symbols(file_content: str) -> list[str]:
    """All global symbols in the file."""
    imported = all_toplevel_imported_symbols(file_content)
    constants = all_constants(file_content)
    functions = all_function_names(file_content)
    return imported + constants + functions


@cache
def all_toplevel_imported_symbols(file_content: str) -> list[str]:
    """Symbols imported on module's top level."""
    return _get_imported_symbols(all_toplevel_nodes(file_content))


@cache
def all_function_imported_symbols(func_node: FuncAst) -> list[str]:
    """Symbols imported in the function's scope."""
    return _get_imported_symbols(ast.walk(func_node))


def _get_imported_symbols(nodes: Iterable[ast.AST]) -> list[str]:
    """Symbols imported in given nodes."""

    def iterator() -> Iterator[str]:
        for node in nodes:
            if isinstance(node, IMPORT_ASTS):
                for n in node.names:
                    yield n.asname if n.asname is not None else n.name

    return list(iterator())


@cache
def all_function_names(file_content: str) -> list[str]:
    """Names of all functions defined in the file."""
    return [f.name for f in all_functions(file_content)]


@cache
def all_functions(file_content: str) -> list[Function]:
    """All functions defined in the file."""
    return _functions_from_nodes(all_nodes(file_content))


@cache
def all_toplevel_functions(file_content: str) -> list[Function]:
    """All functions defined on top-level."""
    return _functions_from_nodes(all_toplevel_nodes(file_content))


def _functions_from_nodes(nodes: Iterable[ast.AST]) -> list[Function]:
    """Get all functions from given nodes."""

    def iterator() -> Iterator[Function]:
        for node in nodes:
            if isinstance(node, FUNC_ASTS):
                yield Function.from_node(node)

    return list(iterator())


@cache
def all_constants(file_content: str) -> list[str]:
    """All number constants in the file - `XYZ = const(32)`."""

    def iterator() -> Iterator[str]:
        for ass in all_global_assignments(file_content):
            if _is_const_assignment(ass):
                yield get_variable_name(ass)

    return list(iterator())


@cache
def all_global_assignments(file_content: str) -> list[ast.Assign]:
    """Global assignment nodes."""

    def iterator() -> Iterator[ast.Assign]:
        for body_node in ast.parse(file_content).body:
            if isinstance(body_node, ast.Assign):
                yield body_node

    return list(iterator())


@cache
def all_toplevel_symbol_usages(file_content: str) -> dict[str, int]:
    """Number of times toplevel symbols are used in the file."""
    return _toplevel_symbol_usages(file_content, all_nodes(file_content))


@cache
def all_nontype_toplevel_symbol_usages(file_content: str) -> dict[str, int]:
    """Number of times toplevel symbols are used outside of type hints."""
    return _toplevel_symbol_usages(
        file_content, ast.walk(remove_type_annotation(ast.parse(file_content)))
    )


def _toplevel_symbol_usages(
    file_content: str, nodes: Iterable[ast.AST]
) -> dict[str, int]:
    """Numbers of usages of global/toplevel symbols in given nodes."""
    toplevel_symbols = all_global_symbols(file_content)

    used_symbols: dict[str, int] = defaultdict(int)
    for node in nodes:
        if _is_symbol_usage(node):
            if node.id in toplevel_symbols:
                used_symbols[node.id] += 1

    return used_symbols


@cache
def all_type_hint_usages(file_content: str) -> dict[str, int]:
    """Get the numbers of times symbols are used as type-hints."""
    type_hint_symbols: dict[str, int] = defaultdict(int)

    def _add_symbols_from_type_node(type_node: ast.AST) -> None:
        for name in _get_all_names_in_node(type_node):
            type_hint_symbols[name] += 1

    for node in all_nodes(file_content):
        # Function arguments and variable annotations
        if isinstance(node, (ast.arg, ast.AnnAssign)) and node.annotation is not None:
            _add_symbols_from_type_node(node.annotation)
        # Function return values
        elif isinstance(node, FUNC_ASTS) and node.returns is not None:
            _add_symbols_from_type_node(node.returns)

    return type_hint_symbols


@cache
def all_nodes_outside_of_function(file_content: str) -> list[ast.AST]:
    """Get all nodes outside of any function."""
    return list(_filter_parent_nodes(ast.parse(file_content), IMPORT_ASTS + FUNC_ASTS))


def _filter_parent_nodes(
    node: ast.AST, filter_types: tuple[Type[ast.AST], ...]
) -> Iterator[ast.AST]:
    """Get all nodes that are not children of some types or the types itself.

    Not including module itself.
    """
    if isinstance(node, filter_types):
        return

    if not isinstance(node, ast.Module):
        yield node

    for child in ast.iter_child_nodes(node):
        yield from _filter_parent_nodes(child, filter_types)


def get_method_names(node: ast.ClassDef) -> list[str]:
    """Names of all methods defined in the class."""
    return [n.name for n in node.body if isinstance(n, FUNC_ASTS)]


def get_node_code(file_content: str, node: ast.AST) -> str:
    """Literal python code of the given node."""
    return str(ast.get_source_segment(file_content, node))


def get_node_str(node: ast.AST) -> str:  # pragma: no cover
    """String representation of the AST node."""
    return ast.dump(node, indent=4)


def print_node(node: ast.AST) -> None:  # pragma: no cover
    """Print the AST node."""
    print(get_node_str(node))


def print_node_code(file_content: str, node: ast.AST) -> None:  # pragma: no cover
    """Print the python code of the given node."""
    print(get_node_code(file_content, node))


def print_ast(file_content: str) -> None:  # pragma: no cover
    """Print the whole AST of the file."""
    print_node(ast.parse(file_content))


def get_function_name(node: ast.Call) -> str:
    """Name of the function called in the node."""
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    elif isinstance(node.func, ast.Name):
        return node.func.id
    else:
        return "Unknown function name"


def _is_const_assignment(node: ast.Assign) -> bool:
    """Check whether assignment node is `XYZ = const(x)`."""
    if not isinstance(node.value, ast.Call):
        return False

    return get_function_name(node.value) == "const"


def get_variable_name(node: ast.Assign) -> str:
    """Name of the variable assigned in the node."""
    return node.targets[0].id  # type: ignore


def is_really_a_constant(file_content: str, var_name: str) -> bool:
    """Check if the variable is defined only once."""
    assigned_num = 0
    for node in all_nodes(file_content):
        if _is_symbol_assignment(node):
            if node.id == var_name:
                assigned_num += 1

    return assigned_num == 1


def is_a_constant_number_var(file_content: str, assign: ast.Assign) -> bool:
    """Whether assignment is a constant number."""
    if not isinstance(assign.value, ast.Constant):
        return False
    if not isinstance(assign.value.value, int):
        return False

    return is_really_a_constant(file_content, get_variable_name(assign))


def _get_all_names_in_node(node: ast.AST) -> list[str]:
    """Get all names/symbols appearing in the node and its children."""

    def iterator() -> Iterator[str]:
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                yield child.id

    return list(iterator())


def is_used_outside_function(file_content: str, symbol: str) -> bool:
    """Check if the symbol is used outside of any function.

    Also looking for usages in the function's decorators and default arguments,
    as those places can only use global symbols.
    """
    for node in all_nodes(file_content):
        if isinstance(node, FUNC_ASTS):
            for decorator in node.decorator_list:
                if symbol in _get_all_names_in_node(decorator):
                    return True
            for default_value in node.args.defaults:
                if symbol in _get_all_names_in_node(default_value):
                    return True

    for node in all_nodes_outside_of_function(file_content):
        if _is_symbol_usage(node):
            if node.id == symbol:
                return True

    return False


def is_used_as_type_hint(file_content: str, symbol: str) -> bool:
    """Check if the symbol is used as a type hint."""
    return symbol in all_type_hint_usages(file_content)


def _is_symbol_assignment(node: ast.AST) -> TypeGuard[ast.Name]:
    """Whether the node is a symbol assignment."""
    return isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)


def _is_symbol_usage(node: ast.AST) -> TypeGuard[ast.Name]:
    """Whether the node is a symbol usage."""
    return isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)


def get_used_func_symbols(func_node: FuncAst) -> dict[str, int]:
    """How many times each symbol is being used in a function.

    Disregarding type hints.
    """
    used_symbols: dict[str, int] = defaultdict(int)

    for node in ast.walk(remove_type_annotation(func_node)):
        if _is_symbol_usage(node):
            used_symbols[node.id] += 1

    return used_symbols


def get_used_func_import_symbols(
    file_content: str, func_node: FuncAst
) -> dict[str, int]:
    toplevel_symbols = all_toplevel_imported_symbols(file_content)
    used_symbols = get_used_func_symbols(func_node)
    return {k: v for k, v in used_symbols.items() if k in toplevel_symbols}


def get_toplevel_symbol_usages_in_functions(
    file_content: str,
) -> dict[str, list[SymbolUsageInFunction]]:
    symbol_usages: dict[str, list[SymbolUsageInFunction]] = defaultdict(list)

    for func in all_functions(file_content):
        usages = get_used_func_import_symbols(file_content, func.node)
        for symbol, usage_num in usages.items():
            symbol_usages[symbol].append(SymbolUsageInFunction(func, usage_num))

    return symbol_usages


def get_function_call_amounts(
    file_content: str,
) -> dict[str, int]:
    """How many times each function is called inside the file.

    Does not currently consider methods on objects.
    """
    function_calls: dict[str, int] = defaultdict(int)

    for node in all_nodes(file_content):
        if isinstance(node, ast.Call):
            if _is_symbol_usage(node.func):
                function_calls[node.func.id] += 1

    return function_calls


def remove_type_annotation(
    root: ast.AST,
) -> ast.AST:
    """Remove type annotations from the AST.

    Returns a new tree, without changing the original one.
    """
    copied_root = deepcopy(root)

    for node in ast.walk(copied_root):
        if hasattr(node, "annotation"):
            node.annotation = None  # type: ignore
        elif hasattr(node, "returns"):
            node.returns = None  # type: ignore

    return copied_root


def get_global_attribute_lookups(
    file_content: str, include_type_hints: bool = False
) -> dict[str, dict[str, int]]:
    """Numbers of global symbol attribute lookups."""
    root = ast.parse(file_content)
    if not include_type_hints:
        nodes = ast.walk(remove_type_annotation(root))
    else:
        nodes = ast.walk(root)
    return _get_attribute_lookups(file_content, nodes, is_local=False)


def get_func_local_attribute_lookups(
    file_content: str, func_node: FuncAst
) -> dict[str, dict[str, int]]:
    """Numbers of local symbol attribute lookups in a given function node."""
    return _get_attribute_lookups(file_content, ast.walk(func_node), is_local=True)


def _get_attribute_lookups(
    file_content: str, nodes: Iterable[ast.AST], is_local: bool
) -> dict[str, dict[str, int]]:
    """How many times a certain attribute was accessed on certain object in given nodes.

    `is_local` is deciding whether to look for local or global symbol's lookups.
    """
    lookups: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    all_imported_symbols = all_toplevel_imported_symbols(file_content)

    def _include_lookup(node: ast.Name) -> bool:
        if is_local:
            return node.id not in all_imported_symbols
        else:
            return node.id in all_imported_symbols

    for node in nodes:
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                if _include_lookup(node.value):
                    lookups[node.value.id][node.attr] += 1

    return lookups


def is_attr_modified(func_node: FuncAst, obj_name: str, attr_name: str) -> bool:
    """Check if the given attribute of the given object is modified in the function."""

    def _target_is_ours(node: ast.AST) -> bool:
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                if node.value.id == obj_name and node.attr == attr_name:
                    return True

        return False

    for node in ast.walk(func_node):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if _target_is_ours(target):
                    return True
        elif isinstance(node, ast.AugAssign):
            if _target_is_ours(node.target):
                return True

    return False


def is_symbol_assigned(func_node: FuncAst, symbol: str) -> bool:
    """Check if the given symbol is assigned in the function."""
    for node in ast.walk(func_node):
        if _is_symbol_assignment(node):
            if node.id == symbol:
                return True

    return False
