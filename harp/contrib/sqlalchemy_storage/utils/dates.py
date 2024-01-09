from sqlalchemy import func
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import ColumnElement
from sqlalchemy.types import DateTime


# Code from https://stackoverflow.com/questions/51662547/truncate-hour-day-week-month-year-in-sqlalchemy
class Trunc(ColumnElement):
    type = DateTime()

    def __init__(self, precision, expr):
        self.precision = precision
        self.expr = expr

    @property
    def _from_objects(self):
        return self.expr._from_objects


@compiles(Trunc, "postgresql")
def compile_trunc_postgresql(element, compiler, **kw):
    return compiler.process(func.date_trunc(element.precision, element.expr))


_modifiers = {
    "year": ("start of year",),
    "month": ("start of month",),
    # This does not account for locale specific first day of week. 1 day
    # is added so that the 1st day of week won't truncate to previous week.
    # Replace 'weekday 0' with 'weekday 1', if you'd like first day of
    # week to be Monday (in accordance with ISO 8601)
    "week": ("1 day", "weekday 0", "-7 days", "start of day"),
    "day": ("start of day",),
}


@compiles(Trunc, "sqlite")
def compile_trunc_sqlite(element, compiler, **kw):
    precision = element.precision
    expr = element.expr
    modifiers = _modifiers.get(precision)

    if modifiers:
        return compiler.process(func.datetime(expr, *modifiers))

    elif precision == "hour":
        return compiler.process(
            func.datetime(expr, func.strftime("-%M minutes", expr), func.strftime("-%f seconds", expr))
        )

    elif precision == "minute":
        return compiler.process(func.datetime(expr, func.strftime("-%f seconds", expr)))

    elif precision == "second":
        return compiler.process(
            func.datetime(expr, func.strftime("-%f seconds", expr), func.strftime("%S seconds", expr))
        )
