import ast
from typing import Callable


def _get_normalized_sources_from_ast(code_ast: ast.AST, /):
    """

    :param code_ast: abstract syntax tree to convert to source code
    :return: noramlized source code string
    """
    statements = []
    for node in code_ast.body:
        statements.append(ast.unparse(node))
    return ("\n".join(statements)).strip()


class Script(Callable):
    """
    A script object represents a small python script that can be executed in a controlled environment. For example, it
    will hold your scripts defined in rules.
    """

    def __init__(self, source: ast.AST | str = None, /, *, filename=None):
        self._filename = filename or f"<{type(self).__name__.lower()}:{id(self)}>"
        self._source = None

        if source is None:
            raise ValueError("Code or AST must be provided.")

        if isinstance(source, str):
            source = ast.parse(source)

        self._code = compile(source, filename=self._filename, mode="exec")
        self._source = _get_normalized_sources_from_ast(source)

    @property
    def source(self):
        return self._source

    @property
    def filename(self):
        return self._filename

    @classmethod
    def from_file(cls, filename: str):
        """Constructor from a file content, by filename."""
        with open(filename) as f:
            return cls(f.read(), filename=filename)

    def __call__(self, context: dict):
        exec(self._code, None, context)

    def __eq__(self, other):
        return isinstance(other, Script) and self._code == other._code

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        _type = type(self).__name__
        _source = self.source
        return f"{_type}({repr(_source)}, filename={repr(self.filename)})"


class ExecutableObject(Callable):
    def __init__(self, target: Callable):
        self._target = target

    def __call__(self, context: dict):
        return self._target(context)
