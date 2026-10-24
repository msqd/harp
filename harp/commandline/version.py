from typing import cast

from click import Command, command

import harp


@command(help="Show HARP version.")
def version(**kwargs):
    print(f"{harp.__name__} v{harp.__version__}")


version = cast(Command, version)
