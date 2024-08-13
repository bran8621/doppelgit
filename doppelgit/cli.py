import argparse
import os
import subprocess
import sys
import textwrap
from typing import Callable, List, Optional, Tuple

from . import base, data, diff, remote

GIT_DIR = data.GIT_DIR

CommandArgument = Tuple[str, type, str, Optional[bool], Optional[str]]


def main():
    with data.change_git_dir("."):
        args = parse_args()
        args.func(args)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="A git-like version control system.")
    commands = parser.add_subparsers(dest="command", required=True)
    add_command_parsers(commands)
    return parser.parse_args()


def add_command_parsers(commands: argparse._SubParsersAction) -> None:
    command_definitions = get_command_definitions()

    for command, func, arguments, help_text in command_definitions:
        subparser = commands.add_parser(command, help=help_text)
        subparser.set_defaults(func=func)
        for arg in arguments:
            name, arg_type, arg_help, required, nargs = parse_argument(arg)
            subparser.add_argument(
                name, type=arg_type, help=arg_help, required=required, nargs=nargs
            )


def get_command_definitions() -> List[Tuple[str, Callable, List[CommandArgument], str]]:
    oid = base.get_oid

    return [
        ("init", init, [], "Initialize a new, empty repository."),
        (
            "hash-object",
            hash_object,
            [("file", str, "File to hash")],
            "Compute object ID and optionally creates a blob from a file.",
        ),
        (
            "cat-file",
            cat_file,
            [
                (
                    "object",
                    oid,
                    "Provide content or type and size information for repository objects",
                )
            ],
            "Display the content of an object.",
        ),
        ("write-tree", write_tree, [], "Create a tree object from the current index."),
        (
            "read-tree",
            read_tree,
            [("tree", oid, "Read a tree object into the index")],
            "Read a tree object into the index.",
        ),
        (
            "commit",
            commit,
            [("-m", "--message", str, "The commit message", True)],
            "Record changes to the repository.",
        ),
        (
            "log",
            log,
            [("oid", oid, "Show commit logs", False, "@")],
            "Show commit logs.",
        ),
        (
            "show",
            show,
            [("oid", oid, "Show various types of objects", False, "@")],
            "Show various types of objects.",
        ),
        (
            "diff",
            _diff,
            [
                (
                    "--cached",
                    None,
                    "Show changes between the index and the current HEAD commit",
                ),
                (
                    "commit",
                    str,
                    "Show changes between the working tree and the named commit",
                    False,
                ),
            ],
            "Show changes between commits, commit and working tree, etc.",
        ),
        (
            "checkout",
            checkout,
            [("commit", str, "Checkout a commit")],
            "Switch branches or restore working tree files.",
        ),
        (
            "tag",
            tag,
            [("name", str, "Name of the tag"), ("oid", oid, "Object ID", False, "@")],
            "Create, list, delete or verify a tag object signed with GPG.",
        ),
        (
            "branch",
            branch,
            [
                ("name", str, "Branch name", False),
                ("start_point", oid, "Starting point", False, "@"),
            ],
            "List, create, or delete branches.",
        ),
        ("k", k, [], "Visualize the commit history."),
        ("status", status, [], "Show the working tree status."),
        (
            "reset",
            reset,
            [("commit", oid, "Commit to reset to")],
            "Reset current HEAD to the specified state.",
        ),
        (
            "merge",
            merge,
            [("commit", oid, "Commit to merge")],
            "Join two or more development histories together.",
        ),
        (
            "merge-base",
            merge_base,
            [("commit1", oid, "First commit"), ("commit2", oid, "Second commit")],
            "Find as good common ancestors as possible for a merge.",
        ),
        (
            "fetch",
            fetch,
            [("remote", str, "Fetch from the specified remote")],
            "Download objects and refs from another repository.",
        ),
        (
            "push",
            push,
            [("remote", str, "Remote to push to"), ("branch", str, "Branch to push")],
            "Update remote refs along with associated objects.",
        ),
        (
            "add",
            add,
            [("files", str, "Files to add", True, "+")],
            "Add file contents to the index.",
        ),
    ]


def parse_argument(arg: CommandArgument) -> Tuple[str, type, str, bool, Optional[str]]:
    name, arg_type, arg_help, *extras = arg
    required = extras[0] if extras else False
    nargs = extras[1] if len(extras) > 1 else None
    return name, arg_type, arg_help, required, nargs


def init(args: argparse.Namespace) -> None:
    base.init()
    print(f"Initialized empty ugit repository in {os.getcwd()}/{GIT_DIR}")


def hash_object(args: argparse.Namespace) -> None:
    with open(args.file, "rb") as f:
        print(data.hash_object(f.read()))


def cat_file(args: argparse.Namespace) -> None:
    sys.stdout.flush()
    sys.stdout.buffer.write(data.get_object(args.object, expected=None))


def write_tree(args: argparse.Namespace) -> None:
    print(base.write_tree())


def read_tree(args: argparse.Namespace) -> None:
    base.read_tree(args.tree)


def commit(args: argparse.Namespace) -> None:
    print(base.commit(args.message))


def _print_commit(
    oid: str, commit: base.Commit, refs: Optional[List[str]] = None
) -> None:
    refs_str = f' ({", ".join(refs)})' if refs else ""
    print(f"commit {oid}{refs_str}\n")
    print(textwrap.indent(commit.message, "    "))
    print("")


def log(args: argparse.Namespace) -> None:
    refs = {}
    for refname, ref in data.iter_refs():
        refs.setdefault(ref.value, []).append(refname)

    for oid in base.iter_commits_and_parents({args.oid}):
        commit = base.get_commit(oid)
        _print_commit(oid, commit, refs.get(oid))


def show(args: argparse.Namespace) -> None:
    if not args.oid:
        return
    commit = base.get_commit(args.oid)
    parent_tree = None
    if commit.parents:
        parent_tree = base.get_commit(commit.parents[0]).tree

    _print_commit(args.oid, commit)
    result = diff.diff_trees(base.get_tree(parent_tree), base.get_tree(commit.tree))
    sys.stdout.flush()
    sys.stdout.buffer.write(result)


def _diff(args: argparse.Namespace) -> None:
    oid = args.commit and base.get_oid(args.commit)

    if args.commit:
        tree_from = base.get_tree(oid and base.get_commit(oid).tree)

    if args.cached:
        tree_to = base.get_index_tree()
        if not args.commit:
            oid = base.get_oid("@")
            tree_from = base.get_tree(oid and base.get_commit(oid).tree)
    else:
        tree_to = base.get_working_tree()
        if not args.commit:
            tree_from = base.get_index_tree()

    result = diff.diff_trees(tree_from, tree_to)
    sys.stdout.flush()
    sys.stdout.buffer.write(result)


def checkout(args: argparse.Namespace) -> None:
    base.checkout(args.commit)


def tag(args: argparse.Namespace) -> None:
    base.create_tag(args.name, args.oid)


def branch(args: argparse.Namespace) -> None:
    if not args.name:
        current = base.get_branch_name()
        for branch in base.iter_branch_names():
            prefix = "*" if branch == current else " "
            print(f"{prefix} {branch}")
    else:
        base.create_branch(args.name, args.start_point)
        print(f"Branch {args.name} created at {args.start_point[:10]}")


def k(args: argparse.Namespace) -> None:
    dot = "digraph commits {\n"

    oids = set()
    for refname, ref in data.iter_refs(deref=False):
        dot += f'"{refname}" [shape=note]\n'
        dot += f'"{refname}" -> "{ref.value}"\n'
        if not ref.symbolic:
            oids.add(ref.value)

    for oid in base.iter_commits_and_parents(oids):
        commit = base.get_commit(oid)
        dot += f'"{oid}" [shape=box style=filled label="{oid[:10]}"]\n'
        for parent in commit.parents:
            dot += f'"{oid}" -> "{parent}"\n'

    dot += "}"
    print(dot)

    with subprocess.Popen(
        ["dot", "-Tgtk", "/dev/stdin"], stdin=subprocess.PIPE
    ) as proc:
        proc.communicate(dot.encode())


def status(args: argparse.Namespace) -> None:
    HEAD = base.get_oid("@")
    branch = base.get_branch_name()
    if branch:
        print(f"On branch {branch}")
    else:
        print(f"HEAD detached at {HEAD[:10]}")

    MERGE_HEAD = data.get_ref("MERGE_HEAD").value
    if MERGE_HEAD:
        print(f"Merging with {MERGE_HEAD[:10]}")

    print("\nChanges to be committed:\n")
    HEAD_tree = HEAD and base.get_commit(HEAD).tree
    for path, action in diff.iter_changed_files(
        base.get_tree(HEAD_tree), base.get_index_tree()
    ):
        print(f"{action:>12}: {path}")

    print("\nChanges not staged for commit:\n")
    for path, action in diff.iter_changed_files(
        base.get_index_tree(), base.get_working_tree()
    ):
        print(f"{action:>12}: {path}")


def reset(args: argparse.Namespace) -> None:
    base.reset(args.commit)


def merge(args: argparse.Namespace) -> None:
    base.merge(args.commit)


def merge_base(args: argparse.Namespace) -> None:
    print(base.get_merge_base(args.commit1, args.commit2))


def fetch(args: argparse.Namespace) -> None:
    remote.fetch(args.remote)


def push(args: argparse.Namespace) -> None:
    remote.push(args.remote, f"refs/heads/{args.branch}")


def add(args: argparse.Namespace) -> None:
    base.add(args.files)
