# auth: Basic configurations keep working, deprecated

**Problem**

Existing installs configure `dashboard.auth: {type: basic, users: …}` with passlib hashes of many algorithms, plaintext and lmhash included. They must upgrade without editing their configuration, then move off Basic.

**Acceptance criteria**

- `dashboard.auth.type: basic` enables the password and Basic methods. Its users are imported once: `pbkdf2_sha256` and `argon2` hashes kept and re-hashed to Argon2id at next sign-in, `plaintext` hashed at import, any other algorithm imported without a password with a warning to re-invite. Imported accounts are Admin. Test with a hash produced by passlib.
- After the import, the configured `users` list is ignored; a change to it logs a warning. Startup warns that Basic and accounts in configuration are deprecated.
- Basic authenticates against the password identity, for API clients; browsers get the sign-in page.
- passlib is not a dependency of the auth application.
- The changelog announces the removal of Basic one minor version after the auth application ships.

**Out of scope**

Removing Basic.
