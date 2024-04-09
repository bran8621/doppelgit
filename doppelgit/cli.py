import argparse
import sys
import os
import data
import base

def main():
    args = parse_args()
    args.func(args)

def parse_args():
    """
    Parse the command-line arguments and return the parsed arguments.
    """
    parser = argparse.ArgumentParser()
    
    commands = parser.add_subparsers(dest = 'command')
    commands.required = True

    init_parser = commands.add_parser('init')
    init_parser.set_defaults(func = init)

    hash_object_parser = commands.add_parser('hash-object')
    hash_object_parser.add_argument('file', type = str)
    hash_object_parser.set_defaults(func = data.hash_object)

    cat_file_parser = commands.add_parser('cat-file')
    cat_file_parser.add_argument('object', type = str)
    cat_file_parser.set_defaults(func = data.cat_file)

    write_tree_parser = commands.add_parser('write-tree')
    write_tree_parser.set_defaults(func = base.write_tree)

    return parser.parse_args()


def init(args):
    """
    Initialize the doppelgit repository with the given arguments.

    Parameters:
        args : list
            The arguments to initialize the doppelgit repository.

    Returns:
        None
    """
    data.init()
    print(f'Initialized doppelgit repository in {os.getcwd()}/{data.GIT_DIR}')

def hash_object(args):
    with open(args.file, 'rb') as f:
        print(data.hash_object(f.read()))

def cat_file(args):
    sys.stdout.flush()
    sys.stdout.buffer.write(data.get_object(args.object, expected = None))

def write_tree(args):
    base.write_tree(args)