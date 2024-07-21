from rich.console import Console, Group
from rich.padding import Padding
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax

from harp_apps.rules.subscribers import RulesSubscriber

console = Console(force_terminal=True)


class DebugRulesSubscriber(RulesSubscriber):
    def match(self, *args):
        scripts = list(super().match(*args))

        elements = []
        for i, script in enumerate(scripts):
            elements.append(
                Syntax(
                    "# " + script.filename.strip("<>") + "\n" + script.source.strip(),
                    "python",
                    background_color="default",
                )
            )
            if i:
                elements.append(Rule())

        if len(elements):
            console.print(
                Padding(
                    Panel(
                        Group(*elements),
                        title=f":shuffle_tracks_button: Rule – {args[2]} ([bright_green]{len(scripts)}[/bright_green] script(s) found)",
                        expand=True,
                        title_align="left",
                    ),
                    (0, 0, 0, 8) if args[2].startswith("on_remote_") else (0, 0, 0, 4),
                )
            )

        yield from scripts
