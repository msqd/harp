"""Regression test for the MySQL full-text-search filter parameter binding."""

from sqlalchemy import select
from sqlalchemy.dialects import mysql

from harp_apps.storage.models import Transaction as SqlTransaction
from harp_apps.storage.services.sql import _filter_transactions_based_on_text


def test_mysql_full_text_search_binds_a_plain_string():
    # The MySQL branch must bind ``search_text`` as a plain string ("<text>*" for boolean-mode
    # prefix matching). Binding a ``literal_column`` (a column expression) instead is not a valid
    # parameter value: it breaks MySQL full-text search at runtime and crashes literal-binds
    # rendering. Compiling with literal_binds must succeed and inline the escaped string.
    query = _filter_transactions_based_on_text(select(SqlTransaction), "foo", "mysql")
    compiled = str(query.compile(dialect=mysql.dialect(), compile_kwargs={"literal_binds": True}))
    assert "'foo*'" in compiled
