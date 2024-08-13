import os
from collections import deque, namedtuple
from . import data, diff


def init():
    """Initialize a new doppelgit repository."""
    data.init()
    data.update_ref("HEAD", data.RefValue(symbolic=True, value="refs/heads/master"))


def write_tree(directory="."):
    """
    Write a tree object for the current directory.

    This function recursively writes a tree object for the specified directory and
    returns the object ID of the tree.
    """
    entries = []
    with os.scandir(directory) as it:
        for entry in it:
            full_path = os.path.join(directory, entry.name)
            if is_ignored(full_path):
                continue
            if entry.is_file(follow_symlinks=False):
                type_ = "blob"
                with open(full_path, "rb") as f:
                    oid = data.hash_object(f.read())
            elif entry.is_dir(follow_symlinks=False):
                type_ = "tree"
                oid = write_tree(full_path)
            entries.append((entry.name, oid, type_))

    tree_content = "".join(
        f"{type_} {oid} {name}\n" for name, oid, type_ in sorted(entries)
    )
    return data.hash_object(tree_content.encode(), "tree")


def iterate_tree_entries(oid):
    """Yield each entry of the tree with the given object ID."""
    if not oid:
        return
    tree_contents = data.get_object(oid, "tree").decode().splitlines()
    for entry in tree_contents:
        entry_type, entry_oid, entry_name = entry.split()
        yield entry_type, entry_oid, entry_name


def read_tree(directory="."):
    with os.scandir() as it:
        for entry in it:
            full = f"{dir}/{entry.name}"
            if entry.is_file():
                print(full)
            elif entry.is_dir():
                read_tree(full)


def get_tree(oid, base_path=""):
    """
    Get the contents of a tree object.

    This function retrieves the contents of a tree object and returns a dictionary
    mapping file paths to object IDs.
    """
    result = {}
    for type_, oid, name in iterate_tree_entries(oid):
        assert "/" not in name, "File name can't contain forward slash"
        assert name not in ("..", ".")
        path = os.path.join(base_path, name)
        if type_ == "blob":
            result[path] = oid
        elif type_ == "tree":
            result.update(get_tree(oid, f"{path}/"))
        else:
            assert False, f"Unkown tree entry {type_}"
    return result


def get_working_tree():
    """
    Get the current working directory's tree.

    This function returns a dictionary mapping file paths to their object IDs for the current
    working directory.
    """
    result = {}
    for root, _, filenames in os.walk("."):
        for filename in filenames:
            path = os.path.relpath(os.path.join(root, filename))
            if is_ignored(path) or not os.path.isfile(path):
                continue
            with open(path, "rb") as f:
                result[path] = data.hash_object(f.read())
    return result


def get_index_tree():
    """
    Get the index tree.

    This function returns the current index tree as a dictionary mapping file paths to object IDs.
    """
    with data.get_index() as index:
        return index


def get_commit(oid):
    pass


def read_tree(tree_oid):
    """
    Read a tree object into the working directory.

    This function reads the contents of the specified tree object ID into the current
    working directory, creating directories and files as needed.
    """
    for path, oid in get_tree(tree_oid, base_path="./").items():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data.get_object(oid))


def read_tree_merged(t_base, t_head, t_other, update_working=False):
    with data.get_index() as index:
        index.clear()
        index.update(
            diff.merge_trees(get_tree(t_base), get_tree(t_head), get_tree(t_other))
        )
        if update_working:
            _checkout_index(index)


def _checkout_index(index):
    _empty_current_directory()
    for (
        path,
        oid,
    ) in index.items():
        os.makedirs(os.path.dirname(f"./{path}"), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data.get_object(oid, "blob"))


def commit(message):
    commit = f"tree{write_tree ()}\n"
    HEAD = data.get_ref("HEAD").value
    if HEAD:
        commit += f"parent {HEAD}\n"
    MERGE_HEAD = data.get_ref("MERGE_HEAD").value
    if MERGE_HEAD:
        commit += f"parent{MERGE_HEAD}\n"
        data.delete_ref("Merge")

    commit += "\n"
    commit += f"{message}\n"

    oid = data.hash_object(commit.encode(), "commit")

    data.update_ref("HEAD", data.RefValue(symbolic=False, value=oid))

    return oid


def _empty_current_directory():
    """
    Empty the current directory.

    This function removes all files and directories in the current working directory
    except for those that are ignored.
    """
    for root, dirnames, filenames in os.walk("."):
        for filename in filenames:
            path = os.path.relpath(os.path.join(root, filename))
            if is_ignored(path):
                continue
            os.remove(path)
        for dirname in dirnames:
            path = os.path.relpath(os.path.join(root, dirname))
            if is_ignored(path):
                continue
            try:
                os.rmdir(path)
            except (FileNotFoundError, OSError):
                pass


def is_ignored(path):
    """
    Check if a path is ignored.

    This function returns True if the specified path should be ignored, otherwise False.
    """
    return ".doppelgit" in path.split("/")


# Example usage
tree_oid = write_tree((os.getcwd().rsplit("/", 2))[0])
print(f"Tree object ID for the specified directory: {tree_oid}")
