from sqlalchemy import func
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import ColumnElement
from sqlalchemy.types import DateTime


# Code from https://stackoverflow.com/questions/51662547/truncate-hour-day-week-month-year-in-sqlalchemy
class TruncDatetime(ColumnElement):
    type = DateTime()

    inherit_cache = True

    def __init__(self, precision, expr):
        self.precision = precision
        self.expr = expr

    @property
    def _from_objects(self):
        return self.expr._from_objects


@compiles(TruncDatetime, "postgresql")
def compile_trunc_postgresql(element, compiler, **kw):
    return compiler.process(func.date_trunc(element.precision, element.expr))


@compiles(TruncDatetime, "mysql")
def compile_trunc_mysql(element, compiler, **kw):
    try:
        precision = element.precision.effective_value
    except AttributeError:
        precision = element.precision
    expr = element.expr

    if precision == "year":
        format_str = "%Y-01-01 00:00:00"
    elif precision == "month":
        format_str = "%Y-%m-01 00:00:00"
    elif precision == "day":
        format_str = "%Y-%m-%d 00:00:00"
    elif precision == "hour":
        format_str = "%Y-%m-%d %H:00:00"
    elif precision == "minute":
        format_str = "%Y-%m-%d %H:%i:00"
    elif precision == "second":
        format_str = "%Y-%m-%d %H:%i:%s"
    else:
        raise NotImplementedError(f"Truncating {precision} is not supported for MySQL")

    return compiler.process(func.date_format(expr, format_str))


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


@compiles(TruncDatetime, "sqlite")
def compile_trunc_sqlite(element, compiler, **kw):
    try:
        precision = element.precision.effective_value
    except AttributeError:
        precision = element.precision
    expr = element.expr
    modifiers = _modifiers.get(precision)

    if modifiers:
        return compiler.process(func.datetime(expr, *modifiers))

    if precision == "hour":
        return compiler.process(
            func.datetime(
                expr,
                func.strftime("-%M minutes", expr),
                func.strftime("-%f seconds", expr),
            )
        )

    if precision == "minute":
        return compiler.process(func.datetime(expr, func.strftime("-%f seconds", expr)))

    if precision == "second":
        return compiler.process(
            func.datetime(
                expr,
                func.strftime("-%f seconds", expr),
                func.strftime("%S seconds", expr),
            )
        )

    raise NotImplementedError(f"Truncating {precision} is not supported for SQLite")
