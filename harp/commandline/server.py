from harp.commandline.options.server import CommonServerOptions, add_harp_server_click_options
from harp.utils.commandline import click


@click.command(
    short_help="Starts HARP server.",
    help="""Starts HARP server, using the provided configuration. This is the main process and will be the only process
    you need on a live server, it will serve both the proxy ports and the compiled frontend assets (dashboard).""",
)
@add_harp_server_click_options
def server(**kwargs):
    options = CommonServerOptions(**kwargs)

    from harp import Config, run

    config = Config()
    config.add_defaults()
    config.read_env(options)

    return run(config)
