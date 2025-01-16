from typing import cast

from click import BaseCommand, command

import harp


@command(help="Show HARP version.")
def version(**kwargs):
    print(f"{harp.__name__} v{harp.__version__}")


version = cast(BaseCommand, version)
