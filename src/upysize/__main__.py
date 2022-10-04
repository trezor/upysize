from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator, TextIO, TypedDict

import click

from .strategies import Settings, SpaceSaving
from .strategies.constants_local_only import local_only_constants
from .strategies.constants_no_const import no_const_number
from .strategies.function_inline import function_inline
from .strategies.import_global_cache import global_import_cache
from .strategies.import_one_function import one_function_import
from .strategies.import_type_only import type_only_import
from .strategies.keyword_arguments import keyword_arguments
from .strategies.local_cache_attribute import local_cache_attribute
from .strategies.local_cache_global import local_cache_global
from .strategies.small_classes import init_only_classes


class ValidatorResult(TypedDict):
    """Individual result of a validator/strategy."""

    validator_name: str
    saved_bytes: int
    lines: list[str]


class FileResults(TypedDict):
    """Results for a single file.

    This data-structure gets saved to a JSON file as cache.
    """

    abs_file_path: str
    saved_bytes: int
    results: list[ValidatorResult]
    file_hash: str


class IgnoreData(TypedDict):
    """Data saved in a JSON file to ignore certain warnings in certain files.

    So far supported only for function inlining, but could be extended.
    """

    function_inline: dict[str, list[str]]


@dataclass
class UserOptions:
    """Holds user input from CLI."""

    ignore_data: IgnoreData | None


HERE = Path(__file__).parent
CACHE_FILE = HERE / "cache.json"

# TODO: resolve the type errors
VALIDATORS: list[Callable[[str, Settings], list[SpaceSaving]]] = [  # type: ignore
    function_inline,  # type: ignore
    global_import_cache,  # type: ignore
    one_function_import,  # type: ignore
    type_only_import,  # type: ignore
    keyword_arguments,  # type: ignore
    local_cache_attribute,  # type: ignore
    local_cache_global,  # type: ignore
    local_only_constants,  # type: ignore
    no_const_number,  # type: ignore
    init_only_classes,  # type: ignore
]


UNEXPECTED_ERRORS: list[str] = []


class ResultCache:
    """Saving file results locally to avoid recomputing them if the file is not changed.

    Allows for usage as a context manager, when the cache is saved on exit.
    """

    def __init__(
        self, cache: dict[str, FileResults], cache_file: Path, force_invalid: bool
    ) -> None:
        self.cache = cache
        self.cache_file = cache_file
        self.force_invalid = force_invalid

    def __enter__(self) -> ResultCache:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:  # type: ignore
        self.save()

    @classmethod
    def load(cls, cache_file: Path, force_invalid: bool = False) -> ResultCache:
        if not cache_file.exists():
            return cls({}, cache_file, force_invalid)

        with open(cache_file, "r") as f:
            try:
                return cls(json.load(f), cache_file, force_invalid)
            except json.JSONDecodeError:
                return cls({}, cache_file, force_invalid)

    def is_valid(self, file_path: str, file_hash: str) -> bool:
        if self.force_invalid:
            return False

        return (
            file_path in self.cache and self.cache[file_path]["file_hash"] == file_hash
        )

    def get(self, file_path: str) -> FileResults:
        return self.cache[file_path]

    def set(self, file_path: str, file_results: FileResults) -> None:
        self.cache[file_path] = file_results

    def save(self) -> None:
        with open(self.cache_file, "w") as f:
            json.dump(self.cache, f, indent=4)


def get_uninlinable_functions(file_path: Path, ignore_data: IgnoreData) -> list[str]:
    """Get a list of functions that should not be inlined.

    Matches filepaths in ignore file with absolute path according to their endings.
    When it doesn't find the wanted file, it returns an empty list.
    """

    # TODO: generalize this function to work with all ignore_data
    # and getting just relevant data for given file

    funcs_to_not_inline = ignore_data["function_inline"]

    file_abs_path = str(file_path.absolute())
    for file, functions in funcs_to_not_inline.items():
        if file_abs_path.endswith(file):
            return functions

    return []


def report_file_results(file_results: FileResults) -> None:
    """Reporting results for a specific file by printing them into terminal."""
    if not file_results["results"]:
        return

    # TODO: offer some other result output, like logging to a file

    print(file_results["abs_file_path"])
    print(f"Potentially saved bytes: {file_results['saved_bytes']}")
    indent = " " * 4
    for result in file_results["results"]:
        print(f"{indent}{result['validator_name']}")
        for line in result["lines"]:
            print(f"{2 * indent}{line}")
    print(80 * "*")


def analyze_file(file_path: Path, cache: ResultCache, options: UserOptions) -> int:
    """Main function for analyzing a single file.

    Handles cache lookup according to file-hash and analyses
    the file only if the cache is not valid.

    Reports file results and returns the amount of saved bytes in this file.
    """
    with open(file_path, "r") as f:
        file_content = f.read()

    abs_path = str(file_path.absolute())
    file_hash = hashlib.md5(file_content.encode()).hexdigest()

    if cache.is_valid(abs_path, file_hash):
        file_results = cache.get(abs_path)
    else:
        results = get_file_results(file_content, file_path, options)
        saved_bytes = sum(r["saved_bytes"] for r in results)
        file_results = FileResults(
            abs_file_path=abs_path,
            saved_bytes=saved_bytes,
            results=results,
            file_hash=file_hash,
        )
        cache.set(abs_path, file_results)

    report_file_results(file_results)

    return file_results["saved_bytes"]


def get_file_results(
    file_content: str, file_path: Path, options: UserOptions
) -> list[ValidatorResult]:
    """Runs a series of validators on a file and returns the results.

    All validators are run with the file content and also with the
    `Settings` object as a way to pass additional information to the validators.
    """

    # List of functions that cannot be inlined for this file, if any
    # TODO: send all the ignore data connected with this file_path
    if options.ignore_data:
        not_inlineable_funcs = get_uninlinable_functions(file_path, options.ignore_data)
    else:
        not_inlineable_funcs = []

    FILE_SETTINGS = Settings(file_path, not_inlineable_funcs)

    def iterator() -> Iterator[ValidatorResult]:
        for validator in VALIDATORS:
            # Error handling so that it is usable even for untested codebases,
            # where one uncaught error does not stop the whole process
            try:
                result = validator(file_content, FILE_SETTINGS)
            except Exception as e:
                report_uncaught_error(validator.__name__, str(file_path), str(e))
                continue

            if result:
                yield ValidatorResult(
                    validator_name=validator.__name__,
                    saved_bytes=sum(p.saved_bytes() for p in result),
                    lines=[str(p) for p in result],
                )

    return list(iterator())


def report_uncaught_error(validator_name: str, file_path: str, err: str) -> None:
    """Process unexpected error by appending it to the list of errors."""
    UNEXPECTED_ERRORS.append(f"Error happened while validating file {file_path}")
    UNEXPECTED_ERRORS.append(f"Validator: {validator_name}")
    UNEXPECTED_ERRORS.append(f"Err: {err}")


@click.command()
@click.argument("path", type=click.Path(exists=True), default=".")
@click.option("-n", "--no-cache", is_flag=True, help="Do not use cache (dev purposes).")
@click.option(
    "-i",
    "--ignore-file",
    type=click.File("r"),
    help="File with warnings that should be ignored.",
)
def main(path: str | Path, no_cache: bool, ignore_file: TextIO | None) -> None:
    # TODO: `output` optionally specifying file where to save the result
    # TODO: `exclude` for not analyzing specific files/patterns
    # TODO: `validator` for running only specific validator
    # TODO: `no-validator` for excluding specific validator

    path = Path(path)
    options = UserOptions(ignore_data=json.load(ignore_file) if ignore_file else None)

    possible_saved_bytes = 0
    file_iterable = path.rglob("*.py") if path.is_dir() else [path]

    with ResultCache.load(CACHE_FILE, force_invalid=no_cache) as cache:
        for file in file_iterable:
            possible_saved_bytes += analyze_file(file, cache, options)

    print(f"Potentially saved bytes: {possible_saved_bytes}")

    if UNEXPECTED_ERRORS:
        for line in UNEXPECTED_ERRORS:
            print(line)
        print("ERROR: There was some unexpected issue. Please check the output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
