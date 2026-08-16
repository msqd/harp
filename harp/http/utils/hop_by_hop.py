"""Which header fields belong to a connection rather than to the message travelling on it.

RFC 9110 §7.6.1 binds an intermediary in both directions: a field describing the connection a
message arrived on must not travel onto the next connection, whichever way the message is going.

This lives in core rather than in an application because two independent applications need it.
``proxy`` needs it for the request it forwards and the response it returns, and ``http_cache``
needs it at the point the upstream response arrives, which is the last moment ``Connection`` is
still readable. Neither application depends on the other, so neither can own it.
"""

#: The fixed part of the rule, from RFC 9110 §7.6.1.
#:
#: ``transfer-encoding`` and ``content-length`` are here for a second reason: they describe the
#: framing of a body that has already been read and is being re-sent, so the original sender's
#: claim about them is not ours to forward. Passing both on lets a sender hand the next hop a
#: message carrying both, which RFC 9112 §6.1 forbids an intermediary from relaying, because
#: recipients disagree about which one wins.
HOP_BY_HOP_HEADERS = frozenset(
    {
        "connection",
        "content-length",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
    }
)


def hop_by_hop_names(headers) -> set:
    """The header names in this message that belong to its connection rather than to the message.

    ``Connection`` is why this depends on the message and not only on the fixed set above: it
    *names* further fields as connection-specific, so a sender can mark anything it likes. Dropping
    ``Connection`` itself while passing on what it named is the half that looks correct and is not.

    :param headers: any mapping of header names to values, matched case-insensitively.
    """
    named_by_connection = {name.strip().lower() for name in headers.get("connection", "").split(",") if name.strip()}
    return HOP_BY_HOP_HEADERS | named_by_connection
