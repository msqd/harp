"""
HARP command-line interface entry point.

This module enables running HARP using `python -m harp` or via uvx.
"""

import sys


def main():
    """Main entry point for the HARP CLI."""
    from harp.commandline import entrypoint

    # Call the Click command group
    return entrypoint()


if __name__ == "__main__":
    sys.exit(main())
