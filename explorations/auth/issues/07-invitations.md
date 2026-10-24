# auth: invitations and account administration

**Problem**

Once the first Admin exists, there is no way to give anyone else access short of the command line.

**Acceptance criteria**

- `auth_invitations` (`secret_hash`, `role`, `expected_email` nullable, `invited_by` nullable, `account_id`, `created_at`, `expires_at`, `accepted_at`, `revoked_at`). The setup link of child 4 becomes an invitation with no author.
- An Admin invites with a role and an optional expected email; the link is single-use and expires after 72 h (setting). The invitee picks any enabled method; with an expected email, an OIDC acceptance requires a matching `email_verified`.
- An Admin lists pending invitations and revokes them; lists accounts, changes a role, disables and re-enables an account (disabling revokes its sessions).
- The last enabled Admin cannot be demoted or disabled.

**Out of scope**

Sending email: the Admin passes the link on.
