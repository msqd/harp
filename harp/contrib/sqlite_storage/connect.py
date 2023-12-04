def connect_to_sqlite():
    import aiosqlite

    return aiosqlite.connect("harp.db")
