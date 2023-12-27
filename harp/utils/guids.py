def generate_transaction_id_ksuid():
    from ksuid import KsuidMs

    return str(KsuidMs())
