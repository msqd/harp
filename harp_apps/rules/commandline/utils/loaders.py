import click

from harp.config.examples import get_example_filename


def load_ruleset_from_files(files, examples, options):
    from harp_apps.rules.settings import RulesSettings

    # todo not easy to implement for now, and not really important for this command set
    if len(options):
        raise click.UsageError("Unsupported options: " + ", ".join(options))

    settings = RulesSettings()
    for file in files:
        settings.load(file)
    for example in examples:
        settings.load(get_example_filename(example))

    return settings.ruleset
