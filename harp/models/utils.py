def generate_transaction_id_ksuid():
    from ksuid import KsuidMs

    return str(KsuidMs())


def generate_transaction_id_nanoid():
    from nanoid import generate
    from nanoid.resources import alphabet

    return generate(alphabet=alphabet[2:])


def generate_transaction_id_ulid():
    from ulid import ULID

    return str(ULID())
