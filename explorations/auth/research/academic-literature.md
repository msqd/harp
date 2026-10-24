# Auth app: what the academic literature and the standards say

Scope: primary sources only (papers on publisher, arXiv, USENIX or NDSS pages, RFCs, NIST, OWASP).
Each topic gives what the sources establish, how strong the evidence is, and a verdict on the
draft design: **keep**, **change** or **open**.

Draft under review: `auth_users(kind, role, session_epoch, disabled_at)`,
`auth_identities(provider local|oidc:<name>, subject, password_hash PHC)`,
`auth_api_tokens(harp_<prefix>_<secret>, sha256 secret_hash, role capped by owner, expiry, revoked_at)`,
stateless HMAC-signed session cookies carrying `user_id, epoch, exp`, role read from the DB on
every request.

Starting point in the code: `harp_apps/dashboard/settings/auth.py` verifies passwords through
`passlib.hash.<algorithm>.verify`. The default is `pbkdf2_sha256`, and the allowed list
(`harp_apps/dashboard/constants.py`) includes `plaintext`, `lmhash`, `md5_crypt` and
`ldap_plaintext`. Whatever we import from there has to be migrated (section 1.4).

Evidence strength scale used below:

- **Normative**: a SHALL or MUST in a standard (NIST, IETF), or a specification we must interoperate with.
- **Empirical**: a measured study of deployed systems or users.
- **Formal**: a proof or attack in a formal model.
- **Guidance**: a curated recommendation (OWASP), based on consensus more than measurement.

---

## 1. Password storage and verification

### 1.1 NIST SP 800-63B-4 (final, July 2025)

SP 800-63B-4 is final, dated 2025-07-31, and supersedes 800-63B (2017, updated 2020).
DOI [10.6028/NIST.SP.800-63b-4](https://doi.org/10.6028/NIST.SP.800-63b-4),
[CSRC page](https://csrc.nist.gov/pubs/sp/800/63/b/4/final),
[HTML text](https://pages.nist.gov/800-63-4/sp800-63b.html). Section 3.1.1.2 (passwords) says:

| Rule | Level |
|---|---|
| Minimum 15 characters when the password is the only factor; 8 when it is used only inside MFA | SHALL |
| Accept at least 64 characters | SHOULD |
| No other composition rules (no forced mix of character classes) | SHALL NOT |
| No periodic forced change; force a change only on evidence of compromise | SHALL NOT / SHALL |
| Compare the whole candidate password against a blocklist of common, expected or compromised passwords | SHALL |
| Normalise Unicode (NFC, "stabilized strings"); each code point counts as one character | SHOULD / SHALL |
| No hints readable by an unauthenticated claimant; no knowledge-based questions | SHALL NOT |
| Allow password managers and autofill | SHALL |
| Allow paste; offer to show the password | SHOULD |
| Rate-limit failed attempts | SHALL |
| At most 100 consecutive failures on one account before disabling that authenticator (lower limits allowed) | SHALL (§3.2.2) |
| Salt and hash with "a suitable password hashing scheme"; salt at least 32 bits; cost "as high as practical" | SHALL / SHOULD |
| Add a keyed hash or encryption step (pepper), with the key in a hardware-protected area | SHOULD |

800-63B-4 points to SP 800-132 for the hashing scheme and does not name memory-hard functions.
On algorithm choice it is neutral, so the choice comes from the sources in 1.2.

### 1.2 Memory-hard hashing: Argon2, RFC 9106, OWASP parameters

- **Argon2 design** (Biryukov, Dinu, Khovratovich, PHC winner,
  [spec v1.2.1](https://www.password-hashing.net/argon2-specs.pdf)). It is built to maximise the
  ASIC cost of an attack for a given CPU time. The 2015 spec already recommended Argon2i (memory
  access that does not depend on the data) for password hashing, because Argon2d's data-dependent
  access leaks through side channels.
- **Attack on Argon2i** (Alwen & Blocki, "Efficiently Computing Data-Independent Memory-Hard
  Functions", [IACR ePrint 2016/115](https://eprint.iacr.org/2016/115), CRYPTO 2016). Argon2i
  can be computed at energy and area-time cost O(n^7/4 log n), below the ideal. The hybrid
  Argon2id answers this: data-independent passes first, data-dependent passes after. **Formal.**
- **RFC 9106** ([rfc-editor](https://www.rfc-editor.org/rfc/rfc9106.html), Sept. 2021) makes
  Argon2id the primary variant ("MUST be supported"). Its first recommended option is t=1, p=4,
  m=2 GiB. Its second, for memory-constrained hosts, is **t=3, p=4, m=64 MiB**. Both use a
  128-bit salt and a 256-bit tag. **Normative** (IRTF CFRG, informational).
- **OWASP Password Storage Cheat Sheet**
  ([link](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)):
  Argon2id with at least **m=19 MiB, t=2, p=1** (or 46 MiB/t=1, 12 MiB/t=3). scrypt N=2^17 when
  Argon2id is unavailable. bcrypt for legacy only, cost ≥10, with a **72-byte input limit**.
  Pre-hashing before bcrypt invites null-byte truncation and "password shucking". PBKDF2-HMAC-SHA256
  with 600,000 iterations only where FIPS-140 is required. **Guidance.**
- **Field measurement** (Tippe & Berner, "Evaluating Argon2 Adoption and Effectiveness in
  Real-World Software", [arXiv 2504.17121](https://arxiv.org/abs/2504.17121), 2025, LNCS 15993).
  OWASP's 46 MiB setting cut compromise rates by 42.5% against SHA-256 for strong passwords at a
  $1 per-account attack budget. RFC 9106's 2 GiB setting, at 44.5× the memory, adds only 23.3%
  more protection. Weak (RockYou-like) passwords fall at 96.9–99.8% whatever the algorithm.
  46.6% of Argon2 deployments on GitHub use parameters below OWASP's. **Empirical.**

### 1.3 Password policy: what the evidence supports

- Tan, Bauer, Christin, Cranor, "Practical Recommendations for Stronger, More Usable Passwords
  Combining Minimum-strength, Minimum-length, and Blocklist Requirements", CCS 2020,
  [doi:10.1145/3372297.3417882](https://doi.org/10.1145/3372297.3417882)
  ([PDF](https://www.andrew.cmu.edu/user/nicolasc/publications/Tan-CCS20.pdf)). Two online
  experiments. Character-class requirements "may provide very little improvement and may even
  reduce effective security" against expert attackers. Minimum length combined with a minimum
  strength (passwords guessable within 10^6 guesses rejected) beats the best blocklist policies.
  When a blocklist is required, they recommend at least 8 characters plus either a fuzzy match
  against the most popular leaked passwords or a full-string match against a very large leak
  corpus. **Empirical.**
- Zhang, Monrose, Reiter, "The Security of Modern Password Expiration", CCS 2010,
  [doi:10.1145/1866307.1866328](https://doi.org/10.1145/1866307.1866328). About 7,700 accounts;
  new passwords are often predictable from the old ones, which undercuts forced expiration.
  **Empirical.** NIST's SHALL NOT on periodic change follows from this line of work.
- An offline crack of a weak password stays cheap whatever the hash (Tippe & Berner above). The
  policy (length, blocklist) does more for weak passwords than the hash parameters do.

### 1.4 Rehash on login and migration

OWASP describes the standard pattern: store the algorithm and its parameters with each hash
(the PHC string format), verify with whatever the stored hash names, and re-hash with the current
algorithm and parameters on the next successful login. Accounts that never log in keep the old
hash; for those, expire the hash and force a reset, or wrap it ("layered": Argon2id over the
legacy hash) until the next login. **Guidance.**

### Implications

- **Keep** a PHC string in `auth_identities.password_hash`. It is what makes rehash-on-login and
  mixed formats work.
- **Keep Argon2id as the only algorithm for new hashes.** Prefer it over bcrypt, and not only on
  strength: NIST asks us to accept 64 characters with each Unicode code point counted as one, and
  64 code points easily exceed bcrypt's 72 bytes. Supporting bcrypt would mean pre-hashing, which
  OWASP flags as risky. Default to OWASP's minimum (m=19 MiB, t=2, p=1) or RFC 9106's second
  option (64 MiB, t=3, p=4). Measurements show little gain above 64 MiB.
- **Change: bound concurrent hashing.** Each verification allocates m of RAM, and HARP shares the
  host with the proxy. Without a semaphore, a login flood turns into memory pressure on the proxy.
  This is an inference from the parameters, not something a source states.
- **Change: migration path from `dashboard.auth.basic`.** Verify legacy passlib hashes through a
  read-only adapter. Re-hash to Argon2id on success. Refuse import of `plaintext`, `lmhash` and the
  like, or wrap them at import time.
- **Policy:** minimum 15 characters while HARP has no MFA (SHALL), at least 64 accepted, no
  composition rules, a blocklist (a bundled top-N leak list is enough; Tan et al. show a
  full-string match against a big corpus also works), no expiry, NFC normalisation before hashing.
- **Rate limiting** on login is a SHALL: per account (≤100 consecutive failures, then disable or
  throttle) and per source.
- **Open:** pepper (NIST SHOULD). It only helps if the key lives outside the database. HARP's
  config or secret file is a natural home, but rotating the pepper forces every password to be
  reset.

---

## 2. Session management

### 2.1 What the sources establish

- **NIST SP 800-63B-4 §5** ([HTML](https://pages.nist.gov/800-63-4/sp800-63b.html)):
  - The session secret comes from an approved RBG, is at least 64 bits, and is generated "in
    direct response to an authentication event" (§5.1).
  - It must not sit in insecure locations such as HTML5 Local Storage (SHOULD NOT).
  - Cookies: Secure-only (SHALL); scoped to the "minimum practical hostnames and paths" (SHALL);
    HttpOnly (SHOULD). Use the `__Host-` prefix with `Path=/` and SameSite Lax or Strict
    (recommended). Values should be opaque, with no readable personal data.
  - Cookie expiry "SHALL NOT be relied upon to enforce session timeouts". The server has to
    enforce them.
  - On logout, secrets "are erased or invalidated".
  - Two timeouts. AAL1: overall ≤30 days (SHOULD), inactivity optional. AAL2: overall ≤24 h,
    inactivity ≤1 h (SHOULD). AAL3: ≤12 h (SHALL) and 15 min (SHOULD). Activity resets the
    inactivity timer.
  - Federation: the RP is authoritative for its own reauthentication; a live IdP session does
    not extend it (§5).
  - Access tokens do not prove the subscriber is present (SHALL NOT).
  **Normative.**
- **OWASP Session Management Cheat Sheet**
  ([link](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)):
  - Identifiers need ≥64 bits of entropy (128 when you generate them yourself).
  - Renew the session after any privilege change, password change included (session fixation).
  - Use `__Host-` with SameSite=Strict (preferred) or Lax.
  - Idle timeout of 15–30 min for low-risk applications; absolute timeout of 4–8 h for an office
    application; both enforced server-side.
  - **Invalidate on the server at logout**: clearing the client cookie is not enough, because "a
    stolen copy … remains usable".
  - The cookie value should be a bare identifier, never personal data.
  **Guidance.**
- **Session fixation.** Calzavara, Focardi, Squarcina, Tempesta, "Surviving the Web: A Journey
  into Web Session Security", ACM CSUR 50(1), 2017,
  [doi:10.1145/3038923](https://doi.org/10.1145/3038923). The survey (§4.5.3–4.5.4) names renewing
  the authentication cookie at login "the most popular, effective and widespread" defense against
  fixation. It also notes that renewal does **not** stop *cookie forcing*, where the attacker logs
  in and plants their own valid cookie in the victim's browser. **Survey of empirical and formal
  work.**
- **Cookie integrity.** Zheng et al., "Cookies Lack Integrity: Real-World Implications", USENIX
  Security 2015
  ([page](https://www.usenix.org/conference/usenixsecurity15/technical-sessions/presentation/zheng)).
  The Secure flag protects confidentiality only. A network attacker on HTTP, or a related-domain
  attacker, can inject or overwrite cookies that later travel over HTTPS; the paper demonstrates
  this on Google and Bank of America, among others. The `__Host-` prefix, now in
  [draft-ietf-httpbis-rfc6265bis](https://datatracker.ietf.org/doc/draft-ietf-httpbis-rfc6265bis/)
  (in the RFC Editor queue, not yet an RFC), exists to close this hole. **Empirical.**
- **Cookie theft in practice.** Sivakorn, Polakis, Keromytis, "The Cracked Cookie Jar", IEEE S&P
  2016 ([PDF](https://www.cs.columbia.edu/~suphannee/papers/sivakorn.sp2016.cookiehijack.pdf)).
  Session cookies stolen over partly-HTTPS sites exposed private data and account functions on
  major services. **Empirical.**
- **Revocation matters after compromise.** Ghasemisharif, Ramesh, Checkoway, Kanich, Polakis,
  "O Single Sign-Off, Where Art Thou?", USENIX Security 2018
  ([page](https://www.usenix.org/conference/usenixsecurity18/presentation/ghasemisharif)). Across
  95 services, most offer no way to recover from an IdP account takeover, because sessions at the
  RPs survive it. Sudhodanan & Paverd (section 4) found the "Unexpired Session" attack the most
  widely applicable (19 vulnerable out of 74 testable services): sessions not invalidated at
  password reset. **Empirical.**

### 2.2 Stateless signed cookies against the draft

The sources contain no academic comparison of stateless and server-side sessions as such. They
do set requirements a stateless design has to meet:

1. **Logout must invalidate on the server** (NIST §5.1, OWASP). With `user_id, epoch, exp`, the
   only server-side lever is bumping `session_epoch`, which signs the user out **everywhere**.
   Clearing the cookie alone leaves a stolen copy valid until `exp`, which OWASP explicitly
   rejects.
2. **The inactivity timeout must be enforced by the server** (NIST §5.2, OWASP). A stateless
   cookie has to carry a last-activity time in the signed payload and be re-issued on activity
   (sliding). The cookie's `Max-Age` alone does not count (NIST SHALL NOT).
3. **The absolute timeout needs the original authentication time** (`auth_time`) in the payload,
   separate from the sliding `exp`.
4. **Fixation** cannot happen if the cookie is minted only at authentication and only by the
   server. **Cookie forcing** (login CSRF) remains: an attacker can plant their own valid cookie.
   Defenses: `__Host-` (blocks injection from related domains and from HTTP), SameSite, and CSRF
   protection on the login endpoint.
5. **Opaqueness.** A signed but unencrypted payload with only a numeric `user_id` is acceptable.
   Do not put email or name in it (NIST, OWASP).
6. Rotating the HMAC key logs everyone out. Support at least two verification keys so it can be
   rotated without that.

### Implications

- **Keep** the role read from the DB per request: role changes and `disabled_at` take effect
  immediately. **Keep** `session_epoch` as the "sign out everywhere" lever. Bump it on password
  change or reset, on disable, on role downgrade, on unlinking an identity, and on admin request.
  This is the Sudhodanan defense.
- **Change, or decide explicitly:** per-device logout. Since every request already reads the user
  row, a server-side `auth_sessions` row (random 128-bit id, `user_id`, `created_at`,
  `last_seen_at`, `revoked_at`) costs one indexed lookup in the same query. It buys real
  per-session logout, a server-enforced idle timeout, and a "your active sessions" list (which
  Sudhodanan & Paverd cite as how victims notice an attack). Stateless with an epoch is
  defensible only if "logout = logout everywhere" is acceptable. Both options satisfy the sources
  if the epoch bump happens at logout.
- **Change:** put `auth_time` and a sliding `last_activity` in the signed payload (or the session
  row). Defaults aligned with NIST AAL2 and OWASP: idle about 1 h, absolute about 12–24 h,
  configurable.
- **Cookie:** `__Host-harp_session`, `Secure; HttpOnly; Path=/; SameSite=Lax`, no `Domain`.
  **Open:** HARP is often served over plain HTTP on localhost or an internal network, where
  `Secure` and `__Host-` do not apply. We need a documented fallback cookie name and a startup
  warning, not a silent downgrade.
- Re-issue the session (new epoch-bound cookie) at every privilege change, including after
  linking an OIDC identity (OWASP).

---

## 3. OAuth 2.0 / OIDC as a relying party, and MCP

### 3.1 Formal analyses and the mix-up attack

Fett, Küsters, Schmitz, "A Comprehensive Formal Security Analysis of OAuth 2.0", CCS 2016
([arXiv 1601.01229](https://arxiv.org/abs/1601.01229)). Trying to prove OAuth secure in the Web
Infrastructure Model, the authors found four attacks, all of which also apply to OpenID Connect
(§3.5). **Formal, and verified on real implementations** (mod_auth_openidc, pyoidc, the Facebook
PHP SDK, nytimes.com):

1. **307 Redirect** (§3.1): an IdP that redirects with 307 after the credentials POST makes the
   browser re-POST the credentials to the RP. This is an IdP fix (use 303).
2. **IdP Mix-Up** (§3.2): the RP is tricked about which IdP the user picked and sends the honest
   IdP's code or token to the attacker. Fix: the IdP's identity goes into the response; this
   became the `iss` parameter of [RFC 9207](https://www.rfc-editor.org/rfc/rfc9207.html). The RP
   checks it against the IdP recorded at the start of the flow.
3. **State Leak** (§3.3): `state` and `code` leak through the `Referer` header of the page served
   at the redirect endpoint, enabling login CSRF. Fix: single-use `state` and a `Referrer-Policy`
   on RP pages.
4. **Naïve RP Session Integrity** (§3.4): an RP that infers the IdP from the redirect URI alone
   can be led to log the user in under the attacker's identity. Fix: always track the user's
   intention explicitly in the session.

With the fixes, the authors prove the authorization, authentication and session integrity
properties (§5).

### 3.2 RFC 9700, the OAuth 2.0 Security BCP (BCP 240, January 2025)

[rfc-editor](https://www.rfc-editor.org/rfc/rfc9700.html). Normative points for a client or RP:

- Prevent CSRF; one-time `state` protected against tampering and swapping (§4.7.1).
- Prevent authorization code injection (§2.1.1, §4.5). PKCE is a MUST for public clients and
  RECOMMENDED for confidential clients, with `S256`. A confidential OIDC client may rely on
  `nonce` instead (§4.5.3.2).
- A client that talks to several authorization servers MUST prevent mix-up (§4.4.2), using
  RFC 9207 `iss` and aborting on mismatch. Distinct redirect URIs per issuer are a fallback only
  (SHOULD only "if other options are not available").
- Exact redirect URI matching (§2.1, §4.1.3); no open redirectors (§2.1).
- Implicit grant SHOULD NOT be used (§2.1.2); ROPC MUST NOT be used (§2.4).
- No access tokens in query strings (§4.3.2).
- Access tokens audience-restricted (SHOULD, via RFC 8707) and limited to minimal privileges
  (§2.3).
- Refresh tokens for public clients sender-constrained or rotated (§2.2.2).

[RFC 7636 (PKCE)](https://www.rfc-editor.org/rfc/rfc7636.html) defines `code_verifier` and the
`S256` challenge. RFC 9207 itself says mix-up "is only relevant to clients that interact with
multiple authorization servers".

### 3.3 OIDC Core

[OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html):

- §5.7: "the only guaranteed unique identifier for a given End-User is the combination of the
  iss Claim and the sub Claim". Email, phone number, preferred_username and name "MUST NOT be
  used" as identifiers. An issuer "MAY re-use an email Claim Value across different End-Users at
  different points in time".
- §3.1.3.7: the ID token `iss` MUST match exactly, `aud` MUST contain the client, and `nonce`
  MUST match.
- §5.1: `email_verified` only says the IdP verified the address. It carries no promise about
  when, or that the address still belongs to the same person.

### 3.4 MCP authorization (spec 2025-11-25)

[MCP Authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization).
Authorization is optional. When an HTTP-based MCP server implements it:

- The MCP server is an **OAuth 2.1 resource server** and **MUST implement RFC 9728** Protected
  Resource Metadata ([RFC 9728](https://www.rfc-editor.org/rfc/rfc9728.html), April 2025),
  including `authorization_servers`. It is advertised through the `WWW-Authenticate:
  Bearer resource_metadata="…"` header on 401, or at
  `/.well-known/oauth-protected-resource[/path]`.
- The authorization server provides RFC 8414 metadata or OIDC Discovery. It is "beyond the scope"
  of the spec and may be a separate entity.
- Client registration, in priority order: pre-registration, **Client ID Metadata Documents**
  (SHOULD), then **RFC 7591 Dynamic Client Registration** (MAY, "for backwards compatibility").
  The 2025-11-25 revision demoted DCR.
- Clients MUST send RFC 8707 `resource`. Servers MUST validate that the token was issued for them
  (audience), MUST reject other tokens, and **MUST NOT pass the received token through to
  upstream APIs** (confused deputy, token passthrough).
- PKCE `S256` MUST; clients refuse to proceed if `code_challenge_methods_supported` is absent.
- 403 `insufficient_scope` with `scope` and `resource_metadata` for step-up.

RFC 9728 §7.3: the client MUST check that the `resource` in the metadata matches the URL it used
(anti-impersonation). §7.4 recommends audience-restricted tokens.

[RFC 7591 §5](https://www.rfc-editor.org/rfc/rfc7591.html): with open registration, all metadata
is self-asserted (`client_name` and `logo_uri` are phishing vectors), and redirect URIs must be
registered and restricted. The MCP spec repeats the SSRF and localhost-impersonation risks of
Client ID Metadata Documents.

### Implications

- **Keep** `identities(provider, subject)`, but **change** the key to the **issuer URL** (or a
  provider name bound to a fixed issuer in config) plus `sub`. Never email (OIDC Core §5.7, NIST
  800-63C §3.4). If a provider's `issuer` ever changes in config, existing identities must not
  silently re-bind.
- **RP flow:** authorization code + PKCE S256 + `nonce` + single-use `state`.
  - Bind the pending login (state, verifier, nonce, **expected issuer**) in a short-lived signed
    cookie or a row, not in the URL.
  - Several `oidc:<name>` providers make HARP a multi-AS client, so mix-up defense is a MUST:
    check RFC 9207 `iss` when the provider supports it, otherwise use a **per-provider redirect
    URI** (`/auth/oidc/<name>/callback`).
  - Exact redirect URI. Send `Referrer-Policy: no-referrer` on the callback (Fett state leak).
  - Validate the ID token `iss`, `aud`, `exp` and `nonce`.
  - No implicit flow, no ROPC.
- **The proxy angle.** HARP is literally a proxy, so the MCP "MUST NOT pass through" rule
  generalises: HARP's own session cookie and `Authorization: Bearer harp_…` must be stripped
  before forwarding to an upstream. **Change**, if the proxy does not already do it on
  dashboard-adjacent routes.
- **MCP (open, if HARP exposes an MCP endpoint):** HARP acts as a resource server. RFC 9728
  metadata is a MUST, and pointing `authorization_servers` at the configured OIDC provider is
  cheap. Becoming an authorization server itself (CIMD/DCR, consent screens, SSRF-safe metadata
  fetching) is a large surface. Recommendation: do not build an AS in the first iteration. Accept
  HARP API tokens for MCP clients that support static bearer tokens, and leave full OAuth to an
  external AS. Token audience validation applies either way.

---

## 4. Account linking and pre-hijacking

### 4.1 Sudhodanan & Paverd, USENIX Security 2022

"Pre-hijacked accounts: An Empirical Study of Security Failures in User Account Creation on the
Web" ([USENIX page](https://www.usenix.org/conference/usenixsecurity22/presentation/sudhodanan),
[arXiv 2205.10174](https://arxiv.org/abs/2205.10174)). The attacker knows only the victim's email
and acts *before* the victim creates the account. 75 popular services analysed, **35 vulnerable**,
56 vulnerabilities (Table 3, January–June 2021). **Empirical.** The five attacks (§4):

| Attack | Mechanism | Vulnerable / testable |
|---|---|---|
| Classic-Federated Merge | Attacker creates a password account with the victim's email; the victim later signs in via SSO; the service merges on email; the attacker's password still works | 13 / 54 |
| Unexpired Session | Attacker keeps a session open; the victim "recovers" via password reset; sessions are not invalidated | 19 / 74 |
| Trojan Identifier | Attacker links their own IdP identity (or an alternate email or phone) to the pre-created account; it survives the victim's reset | 12 / 49 |
| Unexpired Email Change | Attacker starts an email change to their own address and confirms it after the victim recovers | 11 / 72 |
| Non-verifying IdP | Attacker signs in through an IdP that does not verify email (custom or business IdPs such as Okta and OneLogin test tenants), using the victim's email; the service merges with the victim's later classic account | 1 / 3 |

Root cause (§6.2.1): "failure to verify ownership of the claimed identifier", at the service or at
the IdP. Defenses (§6.2.2):

- Require verification **before** the account can do anything.
- On password reset: sign out all other sessions and **invalidate all other authentication
  tokens**, cancel pending email changes, and show the linked federated identities for explicit
  keep or unlink.
- On merging classic and federated accounts, "the service must ensure that the user currently
  controls both accounts" (provide or reset the classic password).
- Invalidate pre-MFA sessions when MFA is enabled; notify on security-critical changes.

### 4.2 NIST SP 800-63C-4

[HTML text](https://pages.nist.gov/800-63-4/sp800-63c.html):

- §3.4: a federated identifier is subject identifier plus issuer; SHALL be unique; SHALL NOT
  contain plaintext personal information at FAL2 (email included).
- §3.8.1: "the RP SHALL require an authenticated session with the subscriber account for all
  linking functions". It SHOULD require authentication with an existing federated identifier
  before adding a new one. When an identifier is removed, the RP SHALL disallow access through it.
- §3.8.2: requested attributes must be sufficient to uniquely resolve the subscriber.

**Normative.**

### Implications for HARP

HARP cannot send email, so it has no way to verify that a local account's email belongs to
anyone. Under these conditions **automatic linking of an OIDC identity to an existing local
account by matching email is the Classic-Federated Merge / Non-verifying IdP pattern**. The
sources rule it out: NIST requires an authenticated session for linking, and OIDC Core forbids
email as an identifier.

- **Change: no email-based auto-merge.** Linking happens only:
  - from an authenticated session (the user is logged in locally and clicks "link provider X"),
    which is NIST §3.8.1; or
  - by an admin pre-binding: the admin creates the user with an expected `(issuer, sub)`, or an
    invite that the first OIDC login claims once.
- **Open: JIT provisioning on first OIDC login.** Creating a *new* user is safe from pre-hijack
  only when no local account can collide. Restrict it to an allowlist of issuers, optionally an
  email-domain allowlist **combined with `email_verified=true`**, default role `viewer`. Treat
  `email_verified` as a property of the IdP's process, and trust it only for configured issuers
  known to verify (the Non-verifying IdP finding).
- **Keep** the epoch bump on password reset or change, and **extend** it: revoke or flag API
  tokens? Sudhodanan & Paverd recommend invalidating "all other authentication tokens". For API
  tokens that breaks automation, so **open**: revoke a human's tokens on admin-forced reset, keep
  them on self-service change, and always show the list.
- Unlinking an identity bumps the epoch (NIST §3.8.1: removed identifier SHALL lose access).
- Security-relevant changes (identity linked, password changed, token created) go to the audit
  log and appear in the user's own view: the "notify" defense.

---

## 5. API tokens and bearer secrets

### 5.1 Leak studies

Meli, McNiece, Reaves, "How Bad Can It Git? Characterizing Secret Leakage in Public GitHub
Repositories", NDSS 2019
([page](https://www.ndss-symposium.org/ndss-paper/how-bad-can-it-git-characterizing-secret-leakage-in-public-github-repositories/),
[PDF](https://www.ndss-symposium.org/wp-content/uploads/2019/02/ndss2019_04B-3_Meli_paper.pdf)).
**Empirical.**

- Leaks affect over 100,000 repositories, with thousands of new unique secrets every day.
  133,934 valid unique secrets came from the Search API over nearly 6 months.
- **Distinct structure is what makes detection reliable.** The study limited itself to 15 API key
  types and 4 private-key types "that have distinct signatures" (AWS `AKIA…` etc.). Its regexes
  reached **99.29% accuracy**. Entropy-only or weak-regex tools such as TruffleHog caught only
  about 25% of the same secrets.
- Discovery is near-instant: **median 20 seconds** from push to visibility through the search API.
- Developers rarely clean up: only about 6% of secrets are removed within an hour and 19% within
  16 days, so **81% stay**. Rewriting history does not help, because deleted commits remained
  reachable by SHA. The only real mitigation is to **revoke and reissue**.

[RFC 8959](https://www.rfc-editor.org/rfc/rfc8959.html) (January 2021, informational) registers
the `secret-token:` URI scheme. Its stated purpose is to make tokens unambiguously identifiable,
so that CI can warn, repositories can refuse them and scanners can find them. An identifiable
prefix is the same idea, and the industry has converged on it.

### 5.2 Hashing high-entropy tokens

- NIST SP 800-63B-4 §3.1.2.2 (look-up secrets): "All look-up secrets SHALL be stored in a hashed
  form using an approved hashing function." Only secrets "shorter than the minimum security
  strength" (112 bits) "SHALL be stored in a salted and hashed form using a suitable password
  hashing scheme". §4.2 applies the same "approved one-way function" rule to recovery codes.
  **Normative by analogy.** NIST does not address API tokens directly, but the logic carries over:
  slow hashing exists to resist guessing low-entropy secrets, and a 256-bit random secret cannot
  be guessed.
- So **SHA-256 over a ≥128-bit (better 256-bit) CSPRNG secret is consistent with NIST**. Salt
  adds nothing at that entropy. A keyed HMAC (pepper) only protects against offline verification
  if the DB leaks *and* the token was also exposed, so it is optional.

### 5.3 Expiry and least privilege

- RFC 9700 §2.3: privileges "SHOULD be restricted to the minimum required"; audience-restrict
  tokens.
- Saltzer & Schroeder, "The Protection of Information in Computer Systems", Proc. IEEE 63(9),
  1975, [doi:10.1109/PROC.1975.9939](https://doi.org/10.1109/PROC.1975.9939): least privilege and
  fail-safe defaults.
- Expiry bounds the window of the 81% of leaks that are never cleaned up. That is a direct
  reading of Meli et al.

### Implications

- **Keep** `harp_<prefix>_<secret>`. Make the literal part distinctive enough for a scanner regex
  with near-zero false positives (Meli: distinct structure → 99% precision). `harp_` alone is
  short.
- **Open:** add a checksum suffix, so scanners can reject random matches offline, and register
  the pattern with GitHub secret scanning. The industry exploration covers the mechanics.
- **Keep SHA-256** of the secret part. Make the secret ≥128 bits (prefer 256) from `secrets`.
  Look up by `prefix` (indexed, non-secret), then compare hashes in constant time
  (`hmac.compare_digest`). Or look up directly by the hash, which also removes timing concerns.
- **Keep** `expiry` with a finite **default** (e.g. 90 days) and allow "no expiry" only
  explicitly. **Keep** `revoked_at`. Add `last_used_at` (and maybe last source IP) so stale or
  leaked tokens are visible.
- **Show the full token once**, at creation. Store only the prefix and hash.
- **Never log** the token. Log the prefix or token id (OWASP Logging, section 7).
- **Strip** `Authorization: Bearer harp_…` before proxying upstream (section 3).

---

## 6. Access control model

### 6.1 Sources

- Sandhu, Coyne, Feinstein, Youman, "Role-Based Access Control Models", IEEE Computer 29(2), 1996,
  [doi:10.1109/2.485845](https://doi.org/10.1109/2.485845)
  ([preprint](https://csrc.nist.gov/CSRC/media/Projects/Role-Based-Access-Control/documents/sandhu96.pdf)).
  It defines the RBAC0 to RBAC3 family: flat roles, role hierarchies, constraints, and both
  combined.
- Ferraiolo & Kuhn 1992 and Sandhu, Ferraiolo, Kuhn 2000 ("The NIST Model for RBAC"), unified
  into ANSI INCITS 359-2004, now INCITS 359-2012
  ([NIST RBAC project](https://csrc.nist.gov/projects/role-based-access-control)): a reference
  model plus a functional specification.
- NIST SP 800-162, *Guide to ABAC*, 2014 updated 2019,
  [doi:10.6028/NIST.SP.800-162](https://doi.org/10.6028/NIST.SP.800-162): decisions computed from
  subject, object, operation and environment attributes against policies. It targets
  cross-organisation sharing with many attribute combinations.
- Hardy, "The Confused Deputy", ACM SIGOPS OSR 22(4), 1988,
  [doi:10.1145/54289.871709](https://doi.org/10.1145/54289.871709): a program acting with its own
  authority on behalf of a less-privileged caller.
- Birgisson et al., "Macaroons", NDSS 2014,
  [doi:10.14722/ndss.2014.23212](https://doi.org/10.14722/ndss.2014.23212): bearer credentials
  that holders can *attenuate* with caveats (time, target, purpose) without contacting the
  issuer. This is the formal version of "a token can only be weaker than its issuer".

**Guidance and formal models.** No empirical study we found says when fixed roles stop being
enough. The literature frames it as complexity: ABAC pays off when the policy depends on
attributes of the *object* (which proxy, which endpoint, which tenant) and not only on who the
subject is.

### Implications

- **Keep** three fixed, linearly ordered roles (viewer < operator < admin). That is RBAC with a
  linear hierarchy (RBAC1 in Sandhu et al. 1996), the simplest model the standards recognise, and
  HARP's permission space (read dashboards, operate proxy controls, administer users and settings)
  does not depend on object attributes today.
- **Change:** compute "role capped by owner" **at request time**, as
  `effective = min(token.role, owner.role)`, with owner disabled meaning token invalid. Checking
  only at creation leaves a demoted admin's tokens at admin level: a confused-deputy pattern and
  a least-privilege violation. The draft already reads the role from the DB per request, so this
  is free.
- **Open:** per-proxy or per-endpoint scoping of tokens (e.g. a CI token that can only read one
  proxy). That is the point where an attribute (resource) enters the decision. A small `scopes`
  column, interpreted as an attenuation in the macaroon sense (intersection, never extension),
  covers it without a full ABAC engine. Defer until a use case asks for it.
- `kind = service | system`: service users own automation tokens. Least privilege suggests
  service users default to `viewer` and cannot log in interactively (no local identity). `system`
  should be impossible to authenticate as from outside.

---

## 7. Audit logging (brief; a separate exploration covers audit)

- **OWASP Logging Cheat Sheet**
  ([link](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)). Always log:
  authentication successes and failures, authorization failures, session management failures,
  and higher-risk actions (user administration, including adding or deleting tokens, privilege
  changes, use of admin accounts). **Never record** session ids, access tokens, passwords or keys;
  hash them if correlation is needed. Each event records when, where, who and what. Detect
  tampering, move logs to read-only storage quickly, and restrict and audit access to the logs.
  **Guidance.**
- **NIST SP 800-92** (2006, [doi:10.6028/NIST.SP.800-92](https://doi.org/10.6028/NIST.SP.800-92))
  and its Rev. 1 initial public draft, *Cybersecurity Log Management Planning Guide*, October 2023
  ([doi:10.6028/NIST.SP.800-92r1.ipd](https://doi.org/10.6028/NIST.SP.800-92r1.ipd)): a planning
  playbook covering generation, transport, storage, access and disposal, with no auth-specific
  requirements. **Guidance.**
- **Tamper evidence.**
  - Schneier & Kelsey, "Secure Audit Logs to Support Computer Forensics", ACM TISSEC 1(3), 1999
    ([page](https://www.schneier.com/academic/archives/1999/05/secure_audit_logs_to.html)):
    entries written before a compromise cannot be read, or altered undetected, by the attacker
    who takes the machine.
  - Crosby & Wallach, "Efficient Data Structures for Tamper-Evident Logging", USENIX Security 2009
    ([PDF](https://www.usenix.org/legacy/event/sec09/tech/full_papers/crosby.pdf)): history trees
    give logarithmic membership and consistency proofs. The model needs **auditors outside the
    logger** holding past commitments.

  **Formal.** The lesson that carries over: a hash chain inside the same database an attacker
  controls gives tamper *evidence* only if its head is anchored somewhere else (exported, signed,
  or shipped to syslog or an external sink).

### Implications

- Auth events to emit from day one: login success and failure (with reason, without the
  password), logout, epoch bump (and why), password change, identity link and unlink, role
  change, disable and enable, token create, use (sampled or `last_used_at`) and revoke.
- Store the actor's user id and the token prefix or id, never the secret.
- **Open:** a hash-chained audit table is cheap but only meaningful with an external anchor. Leave
  that decision to the audit exploration.

---

## Summary of verdicts

| # | Item | Verdict | Main source |
|---|---|---|---|
| 1 | PHC string, Argon2id for new hashes, rehash on login | Keep | RFC 9106, OWASP |
| 1 | Argon2id about 19–64 MiB, bounded concurrency | Change (add semaphore) | OWASP, Tippe & Berner 2025 |
| 1 | Min 15 chars without MFA, ≥64 accepted, blocklist, no composition, no expiry, rate limit ≤100 | Change (policy to encode) | NIST 800-63B-4 §3.1.1.2, Tan et al. 2020 |
| 1 | Migrate passlib basic-auth users; drop plaintext-class algorithms | Change | OWASP |
| 2 | Stateless cookie + epoch: logout must invalidate server-side | Change or accept "logout everywhere" | NIST §5.1, OWASP |
| 2 | Server-enforced idle and absolute timeouts in the signed payload | Change | NIST §5.2 |
| 2 | `__Host-`, Secure, HttpOnly, SameSite; plain-HTTP fallback | Keep / Open | NIST §5, Zheng 2015 |
| 3 | Identity key = issuer + sub, never email | Change (issuer explicit) | OIDC Core §5.7, NIST 800-63C §3.4 |
| 3 | Code + PKCE S256 + nonce + state; mix-up defense via `iss` or per-provider callback | Keep (specify) | RFC 9700, RFC 9207, Fett 2016 |
| 3 | Strip HARP credentials before proxying upstream | Change | MCP spec (token passthrough) |
| 3 | MCP: RFC 9728 metadata yes, own AS no (first iteration) | Open | MCP 2025-11-25, RFC 9728 |
| 4 | No auto-link by email; link only from an authenticated session or admin pre-binding | Change | Sudhodanan & Paverd 2022, NIST 800-63C §3.8.1 |
| 4 | Epoch bump on reset, unlink, disable | Keep | Sudhodanan & Paverd §6.2.2 |
| 5 | Distinct prefix, SHA-256 over ≥128-bit secret, default expiry, `last_used_at` | Keep / Change | Meli 2019, NIST §3.1.2.2, RFC 8959 |
| 6 | Three fixed roles; cap computed at request time | Keep / Change | Sandhu 1996, Saltzer & Schroeder 1975 |
| 7 | Log auth and critical events; no secrets; external anchor for tamper evidence | Open | OWASP Logging, Crosby & Wallach 2009 |
