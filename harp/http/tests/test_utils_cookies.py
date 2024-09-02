from harp.http.utils import parse_cookie


class TestCookieParsing:
    """
    Some test cases are adapted from django's httpwrappers tests and/or python's Lib/test/test_utils_cookies.py.
    """

    def test_nonstandard_keys(self):
        """
        A single non-standard cookie name doesn't affect all cookies.
        """
        cookies = parse_cookie("good_cookie=yes;bad:cookie=yes")
        assert "good_cookie" in cookies

    def test_repeated_nonstandard_keys(self):
        """
        A repeated non-standard name doesn't affect all cookies.
        """
        cookies = parse_cookie("a:=b; a:=c; good_cookie=yes")
        assert "good_cookie" in cookies

    def test_python_cookies(self):
        assert parse_cookie("chips=ahoy; vienna=finger") == {
            "chips": "ahoy",
            "vienna": "finger",
        }

        # Here parse_cookie() differs from Python's cookie parsing in that it
        # treats all semicolons as delimiters, even within quotes.
        cookies = parse_cookie('keebler="E=mc2; L=\\"Loves\\"; fudge=\\012;"')
        assert cookies == {
            "keebler": '"E=mc2',
            "L": '\\"Loves\\"',
            "fudge": "\\012",
            "": '"',
        }

        # Illegal cookies that have an '=' char in an unquoted value.
        assert parse_cookie("keebler=E=mc2") == {"keebler": "E=mc2"}

        # Cookies with ':' character in their name.
        assert parse_cookie("key:term=value:term") == {"key:term": "value:term"}

        # Cookies with '[' and ']'.
        assert parse_cookie("a=b; c=[; d=r; f=h") == {
            "a": "b",
            "c": "[",
            "d": "r",
            "f": "h",
        }

    def test_cookie_edgecases(self):
        # Cookies that RFC 6265 allows.
        assert parse_cookie("a=b; Domain=example.com") == {
            "a": "b",
            "Domain": "example.com",
        }
        # TODO: let's see what RFCs sais about what cookie to keep
        assert parse_cookie("a=b; h=i; a=c") == {"a": "c", "h": "i"}

    def test_invalid_cookies(self):
        """
        Cookie strings that go against RFC 6265 but browsers will send if set via document.cookie.
        """
        # Chunks without an equals sign appear as unnamed values per
        # https://bugzilla.mozilla.org/show_bug.cgi?id=169091
        assert "language" in parse_cookie("abc=def; unnamed; language=en")

        # Even a double quote may be an unnamed value.
        assert parse_cookie('a=b; "; c=d') == {"a": "b", "": '"', "c": "d"}
        # Spaces in names and values, and an equals sign in values.
        assert parse_cookie("a b c=d e = f; gh=i") == {"a b c": "d e = f", "gh": "i"}

        # More characters the spec forbids.
        assert parse_cookie('a   b,c<>@:/[]?{}=d  "  =e,f g') == {"a   b,c<>@:/[]?{}": 'd  "  =e,f g'}

        # Unicode characters. The spec only allows ASCII.
        assert parse_cookie("composer=Frédéric Chopin") == {"composer": "Frédéric Chopin"}

        # Browsers don't send extra whitespace or semicolons in Cookie headers,
        # but parse_cookie() should parse whitespace the same way
        # document.cookie parses whitespace.
        assert parse_cookie("  =  b  ;  ;  =  ;   c  =  ;  ") == {"": "b", "c": ""}
