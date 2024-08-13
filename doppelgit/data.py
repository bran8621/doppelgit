import os
import hashlib
import json
import shutil
import logging
from collections import namedtuple
from contextlib import contextmanager
from typing import Dict, Optional, Tuple
from pathlib import Path

# Constants
GIT_DIR: Optional[Path] = None
OBJECTS_DIR = "objects"
INDEX_FILE = "index"
REFS_DIR = "refs"
HEAD_FILE = "HEAD"
MERGE_HEAD_FILE = "MERGE_HEAD"
DOPPELGIT_DIR = ".doppelgit"

# Types
RefValue = namedtuple("RefValue", ["symbolic", "value"])

# Logging configuration
logging.basicConfig(level=logging.INFO)


# Git Directory Initialization
def init() -> None:
    """
    Initialize the git directory structure.
    """
    ensure_git_dir_set()
    GIT_DIR.mkdir(parents=True, exist_ok=True)
    (GIT_DIR / OBJECTS_DIR).mkdir(exist_ok=True)
    logging.info(f"Initialized git directory at {GIT_DIR}")


# Context Managers
@contextmanager
def change_git_dir(new_dir: str) -> None:
    """
    Change the GIT_DIR.
    """
    global GIT_DIR
    old_dir = GIT_DIR
    GIT_DIR = Path(new_dir) / DOPPELGIT_DIR
    logging.info(f"Changed GIT_DIR to {GIT_DIR}")
    return old_dir


def get_index() -> Dict[str, str]:
    """
    Read and write the git index.
    """
    ensure_git_dir_set()
    index_path = GIT_DIR / INDEX_FILE
    index = read_json_file(index_path) if index_path.is_file() else {}
    logging.info(f"Read index from {index_path}")
    return index


def write_index(index: Dict[str, str]) -> None:
    """
    Write the git index.
    """
    ensure_git_dir_set()
    index_path = GIT_DIR / INDEX_FILE
    write_json_file(index_path, index)
    logging.info(f"Updated index at {index_path}")


# Object Handling
def hash_object(data: bytes, type_: str = "blob") -> str:
    """
    Hash the object and store it in the git directory.
    """
    ensure_git_dir_set()
    object_data = type_.encode() + b"\x00" + data
    oid = hashlib.sha1(object_data).hexdigest()
    write_to_file(GIT_DIR / OBJECTS_DIR / oid, object_data, mode="wb")
    logging.info(f"Stored object {oid}")
    return oid


def get_object(oid: str, expected: Optional[str] = "blob") -> bytes:
    """
    Get the object content by its oid.
    """
    ensure_git_dir_set()
    object_path = GIT_DIR / OBJECTS_DIR / oid
    object_data = read_binary_file(object_path)

    type_, _, content = object_data.partition(b"\x00")
    type_ = type_.decode()

    if expected is not None:
        assert type_ == expected, f"Expected {expected} but got {type_}"
    return content


def object_exists(oid: str) -> bool:
    """
    Check if the object exists.
    """
    ensure_git_dir_set()
    return (GIT_DIR / OBJECTS_DIR / oid).is_file()


def fetch_objects_if_missing(oid: str, remote_git_dir: str) -> None:
    """
    Fetch the object from a remote git directory if it's missing locally.
    """
    ensure_git_dir_set()
    if object_exists(oid):
        return
    remote_git_dir = Path(remote_git_dir) / DOPPELGIT_DIR
    shutil.copy(remote_git_dir / OBJECTS_DIR / oid, GIT_DIR / OBJECTS_DIR / oid)
    logging.info(f"Fetched object {oid} from remote {remote_git_dir}")


def push_object(oid: str, remote_git_dir: str) -> None:
    """
    Push the object to a remote git directory.
    """
    ensure_git_dir_set()
    remote_git_dir = Path(remote_git_dir) / DOPPELGIT_DIR
    shutil.copy(GIT_DIR / OBJECTS_DIR / oid, remote_git_dir / OBJECTS_DIR / oid)
    logging.info(f"Pushed object {oid} to remote {remote_git_dir}")


# Reference Handling
def update_ref(ref: str, value: str, deref: bool = True) -> None:
    """
    Update the reference to a new value.
    """
    ensure_git_dir_set()
    ref_path = GIT_DIR / ref
    write_to_file(ref_path, value)
    logging.info(f"Updated ref {ref} with value {value}")


def get_ref(ref: str, deref: bool = True) -> RefValue:
    """
    Get the reference value.
    """
    return _get_ref_internal(ref, deref)[1]


def _get_ref_internal(ref: str, deref: bool) -> Tuple[str, RefValue]:
    """
    Internal function to get the reference value.
    """
    ensure_git_dir_set()
    ref_path = GIT_DIR / ref
    value = read_from_file(ref_path).strip() if ref_path.is_file() else None

    symbolic = bool(value) and value.startswith("ref:")
    if symbolic:
        value = value.split(":", 1)[1].strip()
        if deref:
            return _get_ref_internal(value, deref=True)

    return ref, RefValue(symbolic=symbolic, value=value)


def iter_refs(prefix: str = "", deref: bool = True) -> Dict[str, RefValue]:
    """
    Iterate over references with a given prefix.
    """
    ensure_git_dir_set()
    refs = [HEAD_FILE, MERGE_HEAD_FILE]
    for root, _, filenames in os.walk(GIT_DIR / REFS_DIR):
        root = Path(root).relative_to(GIT_DIR)
        refs.extend(f"{root}/{name}" for name in filenames)

    ref_dict = {}
    for refname in refs:
        if not refname.startswith(prefix):
            continue
        ref = get_ref(refname, deref=deref)
        if ref.value:
            ref_dict[refname] = ref

    return ref_dict


def delete_ref(ref: str, deref: bool = True) -> None:
    """
    Delete the reference.
    """
    ensure_git_dir_set()
    ref, _ = _get_ref_internal(ref, deref=False)
    os.remove(GIT_DIR / ref)
    logging.info(f"Deleted ref {ref}")


# Helper Functions
def ensure_git_dir_set() -> None:
    """
    Ensure GIT_DIR is set.
    """
    if not GIT_DIR:
        raise ValueError("GIT_DIR is not set")


def read_from_file(path: Path) -> str:
    """
    Read text from a file.
    """
    with open(path, "r") as f:
        return f.read()


def write_to_file(path: Path, content: str, mode: str = "w") -> None:
    """
    Write text to a file.
    """
    with open(path, mode) as f:
        f.write(content)


def read_binary_file(path: Path) -> bytes:
    """
    Read binary data from a file.
    """
    with open(path, "rb") as f:
        return f.read()


def read_json_file(path: Path) -> Dict:
    """
    Read JSON data from a file.
    """
    with open(path, "r") as f:
        return json.load(f)


def write_json_file(path: Path, content: Dict) -> None:
    """
    Write JSON data to a file.
    """
    with open(path, "w") as f:
        json.dump(content, f, indent=4)
