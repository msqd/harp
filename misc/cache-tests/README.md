# RFC 9111 compliance suite

HARP's HTTP cache is measured against [cache-tests](https://github.com/http-tests/cache-tests), the
suite that produces the numbers published on [cache-tests.fyi](https://cache-tests.fyi/) for squid,
varnish, nginx, apache and the rest. It sends requests through HARP to its own origin server and
checks what HARP did with them, one behaviour per test.

```bash
make test-e2e-cache
```

That is the whole setup. No database to create, no server to start beforehand.

## What the numbers mean

**This is a baseline, not a target.** HARP scores 56.7%, which sits between nginx (55.9%) and caddy
(57.5%), with squid at 71.8% at the top of the published table. The 158 failures are the state of the
cache as measured, not a defect introduced by anything, and not a release blocker.

What the suite is here for is the *next* run. A test that passes today and fails tomorrow is a
regression somebody introduced, and that is what `make test-e2e-cache` fails on.

## What it compares, and what it will not

The suite emits one verdict per test id, and the comparison is per test id. It never compares
percentages, because a percentage cannot tell a regression from upstream changing the suite:

| in the baseline | in this run | the gate |
|---|---|---|
| passed | fails, in two consecutive runs | **fails**, naming the tests |
| passed | fails in one run, passes in the other | reports it as flaky, does not fail |
| passed | HARP returned a proxy error | reports it as **unobserved**, does not fail |
| passed | upstream deleted the test | reports it, does not fail |
| not in the baseline | fails | reports it as new upstream, does not fail |
| failed | passes | reports the improvement, does not fail |

**A test HARP failed to serve was never measured.** HARP emits roughly fourteen proxy errors per run,
on both backends and on 0.9.1 as well, and when one lands on a test's setup request that test never
reached the cache. Its verdict says nothing about compliance, so it is reported under `unobserved` and
takes no part in the comparison. Watch that count: if it grows, HARP's reliability changed.

**Regressions have to survive two runs.** Over sixteen measured runs no test failed twice in a row,
while five of every seven consecutive pairs disagreed about *something*. The second run only happens
when the first one found something, so a clean run still costs about a minute.

**The baseline never moves on its own**, and it is recorded from **three runs**, not one. A test that
moved while it was being recorded is written down as failing: it can then produce a spurious
improvement, which is an invitation to look, but never a spurious regression, which is a false alarm
that gets the gate switched off. Moving the baseline is a separate command, and it records why:

```bash
make test-e2e-cache-baseline REASON='cache rewrite, see #1234'
```

Baselines live in `baselines/<backend>.json`, carry the conditions they were measured under, and say
how many runs back them. `CACHE_TESTS_BASELINE_RUNS` changes that count.

## Storage backends are not interchangeable

`baselines/sqlite.json` and `baselines/postgresql.json` are two different measurements of the same
suite, and the gate refuses to compare a run against a baseline from the other backend rather than
reporting a difference that means nothing.

**The default is a file-backed SQLite database** under `results/`, deleted before each run so every
run starts with a cold cache. It needs nothing installed and reproduces the PostgreSQL score: measured
over eight runs each, both land on 206 to 208 of 365 and move about one test per run. Neither is
meaningfully flakier than the other.

**Release validation runs against PostgreSQL**, because that is the production path, and because a
storage-layer defect can hide from SQLite entirely: SQLite does not enforce column widths, which is
how a 40-character `blobs.id` survived into 0.10.

```bash
CACHE_TESTS_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/cachetests make test-e2e-cache
```

> **Do not point this at HARP's default `:memory:` storage.** With `sqlite+aiosqlite:///:memory:`
> the cache mostly does not store anything and the suite scores about 40% instead of 56.7%, varying
> by several tests between runs. That is HARP's default when `storage.url` is unset, which is why
> `config.yml` here sets it explicitly.

| variable | default | |
|---|---|---|
| `CACHE_TESTS_DATABASE_URL` | file-backed SQLite under `results/` | storage DSN, and the backend label is read from its scheme |
| `CACHE_TESTS_PROXY_PORT` | 4000 | port HARP listens on |
| `CACHE_TESTS_ORIGIN_PORT` | 8000 | port the suite's origin server listens on |

## Reading the output

The report the target prints is the output: the score, the backend it was measured on, and every test
that changed verdict since the baseline. A score without its backend is not a result, so the two are
always printed together.

The raw verdicts land in `results/<backend>.json`, alongside `harp.log` and `origin.log` from the run.
Everything in `results/` is git-ignored and written **outside** the submodule, so a run leaves both
repositories clean.

The suite ships an HTML viewer that compares implementations, but it reads a registry inside the
submodule listing Chrome, Firefox, nginx and so on. Adding HARP to it means editing a file that the
next submodule update discards, so **the viewer is not for us** and there is no script here to open
it. The JSON and the printed report are the output.

## Running it by hand

```bash
# once
git submodule update --init --recursive misc/cache-tests/cache-tests
(cd misc/cache-tests/cache-tests && npm install)

# origin server
(cd misc/cache-tests/cache-tests && npm run server --port=8000)

# harp, in another terminal
cd misc/cache-tests
uv run harp-proxy server --file config.yml \
    --applications http_client,http_cache,proxy,storage \
    --endpoint cache-tests=4000:http://localhost:8000/ \
    --set storage.url=sqlite+aiosqlite:///$PWD/results/storage.db

# the suite, in a third
(cd misc/cache-tests/cache-tests && npm run --silent cli --base=http://localhost:4000)
```

> **Comparing against another HARP version?** Install it in its own virtualenv and check
> `harp.__file__`, not `harp.__version__`. Run from this checkout and the working directory wins on
> `sys.path`, so `import harp` reports the version you are standing next to rather than the one you
> installed, and every number in the comparison is silently the wrong version's.

`--applications` is a command line flag and not a `config.yml` key on purpose: in a configuration file
`applications:` only *adds* to the default set, it never restricts it. The endpoint is passed on the
command line for the same kind of reason: declaring it in `config.yml` as well makes HARP refuse to
start with `Endpoint «cache-tests» already exists`.

## When it fails

The target fails, loudly and with the step named, when the submodule is missing, when a port it needs
is taken, when the origin server or HARP does not come up, when HARP comes up but does not reach the
origin, when the suite produces nothing parseable, and when tests that passed in the baseline fail
twice in a row.

It used to exit 0 for every one of those. See
[#990](https://github.com/msqd/harp/issues/990) and
[ADR-0003](../../docs/adr/0003-cache-compliance-compared-per-test-against-a-pinned-baseline.md).

## Related

- **cache-tests**: https://github.com/http-tests/cache-tests
- **RFC 9111**: https://www.rfc-editor.org/rfc/rfc9111.html
- **HARP caching docs**: `docs/apps/http_cache/`
