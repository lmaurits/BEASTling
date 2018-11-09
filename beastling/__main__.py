# coding: utf8
from __future__ import unicode_literals
from beastling.cli import main

import beastling.cli

class NoneException (Exception):
    pass

beastling.cli.wrap_errors = NoneException


if __name__ == "__main__":
    main()
