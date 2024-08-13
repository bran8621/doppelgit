#!/usr/bin/env python3

from setuptools import setup

setup(
    name="doppelgit",
    version="1.0.0",
    packages=["doppelgit"],
    entry_points={"console_scripts": ["doppelgit = doppelgit.cli:main"]},
)
