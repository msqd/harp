import shlex

from harp.commandline.utils.manager import HonchoManagerFactory


def test_server_command_reaches_child_unchanged():
    nasty = "a\"b $(id) `id`; \\ 'q'"
    factory = HonchoManagerFactory(proxy_options=["--file " + shlex.quote(nasty)])

    _, command = factory._get_server_executable({})

    watchfiles_argv = shlex.split(command)
    assert watchfiles_argv[0] == "watchfiles"
    server_argv = shlex.split(watchfiles_argv[watchfiles_argv.index("python") + 1])
    assert server_argv[-2:] == ["--file", nasty]
