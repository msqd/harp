import re
import time
import uuid
from collections.abc import AsyncIterator
from typing import Optional

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from harp import get_logger

from .base import (
    Ban,
    BanKind,
    BanMode,
    CacheRecords,
    EndpointStats,
    Reclaimed,
    StoredVariant,
    VariantRecord,
    ban_prefixes,
    covered_ranges,
    endpoint_of,
)

logger = get_logger(__name__)

#: Every key of the cache starts with it: the Redis database may be shared with other applications.
DEFAULT_PREFIX = "harp:cache:"

#: Seconds a body is kept after a record last referred to it (see :class:`RedisCacheRecords`).
DEFAULT_RETENTION = 30 * 86400

#: Variants (or members of the key index) a script looks at in one call: a script blocks Redis while it runs.
SCAN_PAGE = 500

#: Bodies looked at in one run of :meth:`RedisCacheRecords.reclaim_orphans`.
ORPHAN_PAGE = 1000

#: ``PEXPIREAT … GT`` came with Redis 7.
MINIMUM_VERSION = (7, 0)


class UnsuitableRedis(Exception):
    """The Redis server cannot hold the cache without breaking its promises."""


# What every script shares. ``ARGV[1]`` is the prefix of the keys, which the scripts build themselves: Redis Cluster is
# out of scope, so a script is free to touch keys it was not given.
#
#   <p>v:<entry id>    hash, a variant record
#   <p>r:<cache key>   hash, a resource record: variant -> entry id
#   <p>i:<endpoint>    sorted set, all scores 0: the cache keys of an endpoint, in bytewise order
#   <p>endpoints       sorted set, all scores 0: the endpoints that hold a key
#   <p>b:<digest>      string, a body, and <p>x:<digest> the set of the entry ids that refer to it
#   <p>age, <p>size    sorted sets of entry ids, by the instant they were stored and by the size of their body
#   <p>size:<endpoint> the same, for one endpoint
#   <p>stats:*         hashes, endpoint -> count: entries, bytes, refused
#   <p>bans            hash, '<mode>|<kind>|<prefix>' -> '<seq>|<created at>': the newest ban of each
#   <p>counter, floor  strings, the number of the last ban and the floor under the stamps of new fills
#
# Nothing but bodies and their sets expire: records, indexes and bans are never evicted by a volatile-* policy.
_PRELUDE = """
local P = ARGV[1]
local function vkey(id) return P .. 'v:' .. id end
local function rkey(key) return P .. 'r:' .. key end
local function ikey(endpoint) return P .. 'i:' .. endpoint end
local function bodykey(digest) return P .. 'b:' .. digest end
local function refskey(digest) return P .. 'x:' .. digest end
local AGE, SIZE, ENDPOINTS, BANS = P .. 'age', P .. 'size', P .. 'endpoints', P .. 'bans'
local ENTRIES, BYTES = P .. 'stats:entries', P .. 'stats:bytes'

-- The number of the last ban, among these '<mode>|<kind>|<prefix>' fields of the bans hash. 0 when none.
local function newest(fields)
    local seq = 0
    if #fields == 0 then return 0 end
    for _, value in ipairs(redis.call('HMGET', BANS, unpack(fields))) do
        if value then
            local n = tonumber(string.match(value, '^(%d+)|'))
            if n > seq then seq = n end
        end
    end
    return seq
end

-- Keep a key at least until this instant (milliseconds). A key with no expiry is infinite to GT, and takes one first.
local function extend(key, at)
    if redis.call('PTTL', key) == -1 then
        redis.call('PEXPIREAT', key, at)
    else
        redis.call('PEXPIREAT', key, at, 'GT')
    end
end

-- The variant, and what only it held: its place in the indexes, its counters, its body when no other variant has it.
local function remove_variant(id)
    local f = redis.call('HMGET', vkey(id), 'key', 'variant', 'endpoint', 'body_digest', 'body_size')
    if not f[1] then return false end
    local key, variant, endpoint, digest, size = f[1], f[2], f[3], f[4], tonumber(f[5])
    redis.call('DEL', vkey(id))
    if redis.call('HGET', rkey(key), variant) == id then
        redis.call('HDEL', rkey(key), variant)
        if redis.call('EXISTS', rkey(key)) == 0 then
            redis.call('ZREM', ikey(endpoint), key)
            if redis.call('EXISTS', ikey(endpoint)) == 0 then redis.call('ZREM', ENDPOINTS, endpoint) end
        end
    end
    redis.call('ZREM', AGE, id)
    redis.call('ZREM', SIZE, id)
    redis.call('ZREM', P .. 'size:' .. endpoint, id)
    redis.call('SREM', refskey(digest), id)
    if redis.call('EXISTS', refskey(digest)) == 0 then redis.call('DEL', bodykey(digest)) end
    local entries = redis.call('HINCRBY', ENTRIES, endpoint, -1)
    redis.call('HINCRBY', BYTES, endpoint, -size)
    if entries <= 0 then
        redis.call('HDEL', ENTRIES, endpoint)
        redis.call('HDEL', BYTES, endpoint)
    end
    return true
end
"""

# ARGV: prefix, entry id, key, variant, endpoint, stamp, stored at, body digest, body size, keep, replaces ('' for none),
# expiry of the body (milliseconds), body, number of ban fields, the ban fields, then the fields of the variant record.
_PUT = """
local id, key, variant, endpoint = ARGV[2], ARGV[3], ARGV[4], ARGV[5]
local stamp, stored_at, digest, size = tonumber(ARGV[6]), ARGV[7], ARGV[8], tonumber(ARGV[9])
local keep, replaces, expire_at, body = tonumber(ARGV[10]), ARGV[11], ARGV[12], ARGV[13]
local nbans = tonumber(ARGV[14])
local fields = {}
for i = 1, nbans do fields[i] = ARGV[14 + i] end

if newest(fields) > stamp then return 0 end
if replaces == '' and stamp < (tonumber(redis.call('GET', P .. 'floor')) or 0) then return 0 end
if replaces ~= '' then
    if redis.call('EXISTS', vkey(replaces)) == 0 then return 0 end
    remove_variant(replaces)
end
local existing = redis.call('HGET', rkey(key), variant)
if existing then remove_variant(existing) end

redis.call('SET', bodykey(digest), body, 'NX')
extend(bodykey(digest), expire_at)
redis.call('SADD', refskey(digest), id)
extend(refskey(digest), expire_at)

local record = {}
for i = 15 + nbans, #ARGV do record[#record + 1] = ARGV[i] end
redis.call('HSET', vkey(id), unpack(record))
redis.call('HSET', rkey(key), variant, id)
redis.call('ZADD', ikey(endpoint), 'NX', 0, key)
redis.call('ZADD', ENDPOINTS, 'NX', 0, endpoint)
redis.call('ZADD', AGE, stored_at, id)
redis.call('ZADD', SIZE, size, id)
redis.call('ZADD', P .. 'size:' .. endpoint, size, id)
redis.call('HINCRBY', ENTRIES, endpoint, 1)
redis.call('HINCRBY', BYTES, endpoint, size)

local rows = {}
for _, other in ipairs(redis.call('HVALS', rkey(key))) do
    local f = redis.call('HMGET', vkey(other), 'stored_at', 'variant')
    if f[1] then rows[#rows + 1] = {tonumber(f[1]), f[2], other} end
end
table.sort(rows, function(a, b)
    if a[1] ~= b[1] then return a[1] < b[1] end
    return a[2] < b[2]
end)
local excess = #rows
if keep > 0 then excess = #rows - keep end
for i = 1, excess do remove_variant(rows[i][3]) end
return 1
"""

# ARGV: prefix, key, number of hard ban fields, the hard ban fields, then the soft ban fields.
_GET_VARIANTS = """
local key, nhard = ARGV[2], tonumber(ARGV[3])
local hard, soft = {}, {}
for i = 1, nhard do hard[i] = ARGV[3 + i] end
for i = 4 + nhard, #ARGV do soft[#soft + 1] = ARGV[i] end
local hard_seq, soft_seq = newest(hard), newest(soft)

local out = {}
for _, id in ipairs(redis.call('HVALS', rkey(key))) do
    local flat = redis.call('HGETALL', vkey(id))
    if #flat > 0 then
        local record = {}
        for i = 1, #flat, 2 do record[flat[i]] = flat[i + 1] end
        local stamp = tonumber(record.stamp)
        if hard_seq <= stamp then
            local body = redis.call('GET', bodykey(record.body_digest))
            if body then
                out[#out + 1] = {flat, body, soft_seq > stamp and 1 or 0}
            else
                -- the body was evicted or expired: nothing to serve, and nothing worth keeping
                remove_variant(id)
            end
        end
    end
end
return out
"""

# ARGV: prefix, field of the bans hash, created at. Gives the ban the next number.
_BAN = """
local seq = redis.call('INCR', P .. 'counter')
redis.call('HSET', BANS, ARGV[2], seq .. '|' .. ARGV[3])
return seq
"""

# ARGV: prefix, field of the bans hash, number. Retires the ban unless a newer one took its place.
_RETIRE = """
local value = redis.call('HGET', BANS, ARGV[2])
if value and tonumber(string.match(value, '^(%d+)|')) == tonumber(ARGV[3]) then
    redis.call('HDEL', BANS, ARGV[2])
    return 1
end
return 0
"""

# ARGV: prefix, number.
_RAISE_FLOOR = """
if tonumber(ARGV[2]) > (tonumber(redis.call('GET', P .. 'floor')) or 0) then
    redis.call('SET', P .. 'floor', ARGV[2])
end
"""

# ARGV: prefix, instant, limit.
_DELETE_STORED_BEFORE = """
local removed = 0
for _, id in ipairs(redis.call('ZRANGEBYSCORE', AGE, '-inf', '(' .. ARGV[2], 'LIMIT', 0, tonumber(ARGV[3]))) do
    if remove_variant(id) then removed = removed + 1 end
end
return removed
"""

# ARGV: prefix, key.
_DELETE_KEY = """
local removed = 0
for _, id in ipairs(redis.call('HVALS', rkey(ARGV[2]))) do
    if remove_variant(id) then removed = removed + 1 end
end
return removed
"""

# ARGV: prefix, entry id.
_DELETE_ENTRY = """
if remove_variant(ARGV[2]) then return 1 end
return 0
"""

# One page of the keys of an endpoint within a range of keys, looking for the variants stamped below a ban. ARGV: prefix,
# endpoint, lowest key, highest key (both as for ZRANGEBYLEX), key to continue after ('' for none), number of the ban,
# keys to look at, variants to delete at most, 'delete' or 'probe'.
# Returns {deleted, last key looked at, state}: 0 the range is done, 1 more of it to look at, 2 more variants to delete
# than allowed, 3 a probe found one.
_COVERED = """
local endpoint, low, high, after = ARGV[2], ARGV[3], ARGV[4], ARGV[5]
local seq, page, limit, probe = tonumber(ARGV[6]), tonumber(ARGV[7]), tonumber(ARGV[8]), ARGV[9] == 'probe'
if after ~= '' then low = '(' .. after end

local keys = redis.call('ZRANGEBYLEX', ikey(endpoint), low, high, 'LIMIT', 0, page)
local deleted = 0
for _, key in ipairs(keys) do
    for _, id in ipairs(redis.call('HVALS', rkey(key))) do
        local stamp = tonumber(redis.call('HGET', vkey(id), 'stamp'))
        if stamp and stamp < seq then
            if probe then return {0, '', 3} end
            if deleted >= limit then return {deleted, key, 2} end
            remove_variant(id)
            deleted = deleted + 1
        end
    end
end
if #keys < page then return {deleted, '', 0} end
return {deleted, keys[#keys], 1}
"""

# ARGV: prefix, digests. Deletes the bodies no variant refers to.
_DELETE_UNREFERENCED_BODIES = """
local deleted = 0
for i = 2, #ARGV do
    if redis.call('EXISTS', refskey(ARGV[i])) == 0 then deleted = deleted + redis.call('DEL', bodykey(ARGV[i])) end
end
return deleted
"""


def _fields(key: str, mode: BanMode) -> list[str]:
    """The fields of the bans hash that cover a key, for one mode."""
    return [_ban_field(BanKind.EXACT, key, mode), *(_ban_field(BanKind.PREFIX, p, mode) for p in ban_prefixes(key))]


def _ban_field(kind: BanKind, prefix: str, mode: BanMode) -> str:
    return f"{mode.value}|{kind.value}|{prefix}"


def _glob_escape(text: str) -> str:
    return re.sub(r"([\\*?\[\]])", r"\\\1", text)


def _text(value) -> str:
    return value.decode() if isinstance(value, bytes) else value


def _record(flat: list, *, stale: bool = False) -> VariantRecord:
    fields = {_text(flat[i]): flat[i + 1] for i in range(0, len(flat), 2)}
    text = {name: _text(value) for name, value in fields.items() if name != "head"}
    return VariantRecord(
        key=text["key"],
        variant=text["variant"],
        entry_id=uuid.UUID(text["entry_id"]),
        endpoint=text["endpoint"],
        stamp=int(text["stamp"]),
        status=int(text["status"]),
        vary=text.get("vary"),
        body_digest=text["body_digest"],
        body_size=int(text["body_size"]),
        created_at=float(text["created_at"]),
        stored_at=float(text["stored_at"]),
        head=fields["head"],
        query=text.get("query"),
        stale=stale,
    )


class RedisCacheRecords(CacheRecords):
    """The records in Redis, shared by every instance of HARP (ADR-0014). Redis Cluster is not supported.

    Records are hashes, and the keys of an endpoint a sorted set whose members all have the same score, so that it is
    ordered bytewise and read by ranges of keys. Every operation is one script: Redis runs it alone, so it needs none of
    the locks and retries the SQL records do.

    Bodies are strings by content digest. They are what makes the cache big, so they are what Redis may evict, and they
    are kept for ``retention`` seconds: each variant stored, or freshened, extends their expiry (``PEXPIREAT … GT``)
    to that long from then. A variant whose body is gone is no longer served, and is deleted when it is found. A set of
    the entry ids that refer to a body deletes it with the last one; it expires with the body, and is rebuilt as
    variants are stored, so that a lost reference costs a body at worst, never a record. Records, indexes, counters and
    the invalidation log never expire, so a ``volatile-*`` eviction policy does not touch them (see :meth:`ready`).
    """

    def __init__(self, client: Redis, *, prefix: str = DEFAULT_PREFIX, retention: float = DEFAULT_RETENTION):
        if client.connection_pool.connection_kwargs.get("decode_responses"):
            raise ValueError("The cache stores bytes: the Redis client must not decode responses.")
        self.client = client
        self.prefix = prefix
        self.retention = retention
        self._orphan_cursor = 0

        def script(body: str):
            return client.register_script(_PRELUDE + body)

        self._put = script(_PUT)
        self._get_variants = script(_GET_VARIANTS)
        self._ban = script(_BAN)
        self._retire = script(_RETIRE)
        self._raise_floor = script(_RAISE_FLOOR)
        self._delete_stored_before = script(_DELETE_STORED_BEFORE)
        self._delete_key = script(_DELETE_KEY)
        self._delete_entry = script(_DELETE_ENTRY)
        self._covered = script(_COVERED)
        self._delete_unreferenced_bodies = script(_DELETE_UNREFERENCED_BODIES)

    async def ready(self) -> None:
        """Refuse a Redis that would break the cache: too old, or evicting what the invalidation log needs.

        Under an ``allkeys-*`` policy Redis evicts any key to make room, bans included, and the entries they invalidated
        come back. A ``volatile-*`` policy evicts only keys with an expiry, which are the bodies, and ``noeviction``
        evicts nothing.

        Raises:
            UnsuitableRedis: with what to change.
        """
        version = (await self.client.info("server"))["redis_version"]
        if tuple(int(part) for part in str(version).split(".")[:2]) < MINIMUM_VERSION:
            raise UnsuitableRedis(
                f"The cache needs Redis {'.'.join(map(str, MINIMUM_VERSION))} or later (found {version})."
            )
        try:
            policy = _text((await self.client.config_get("maxmemory-policy"))["maxmemory-policy"])
        except ResponseError:
            logger.warning(
                "Redis does not tell its maxmemory-policy (CONFIG is refused): make sure it is not allkeys-*."
            )
            return
        if not (policy == "noeviction" or policy.startswith("volatile-")):
            raise UnsuitableRedis(
                f"The cache keeps its invalidation log in Redis, which evicts any key under maxmemory-policy "
                f"{policy!r} and would drop it: entries invalidated would be served again. "
                f"Set maxmemory-policy to a volatile-* policy (volatile-lru, for one) or to noeviction."
            )

    async def get_variants(self, key: str) -> list[StoredVariant]:
        found = await self._get_variants(
            args=[
                self.prefix,
                key,
                len(hard := _fields(key, BanMode.HARD)),
                *hard,
                *_fields(key, BanMode.SOFT),
            ]
        )
        variants = [StoredVariant(_record(flat, stale=bool(stale)), body) for flat, body, stale in found]
        return sorted(variants, key=lambda v: (v.record.stored_at, v.record.variant))

    async def get_by_id(self, entry_id: uuid.UUID) -> Optional[VariantRecord]:
        flat = await self.client.hgetall(f"{self.prefix}v:{entry_id}")
        return _record([item for pair in flat.items() for item in pair]) if flat else None

    async def counter(self) -> int:
        return int(await self.client.get(f"{self.prefix}counter") or 0)

    async def ban(self, kind: BanKind, prefix: str, mode: BanMode) -> Ban:
        created_at = time.time()
        seq = await self._ban(args=[self.prefix, _ban_field(kind, prefix, mode), repr(created_at)])
        return Ban(seq, kind, prefix, mode, created_at)

    async def bans(self) -> list[Ban]:
        bans = []
        for field, value in (await self.client.hgetall(f"{self.prefix}bans")).items():
            mode, kind, prefix = _text(field).split("|", 2)
            seq, created_at = _text(value).split("|")
            bans.append(Ban(int(seq), BanKind(kind), prefix, BanMode(mode), float(created_at)))
        return sorted(bans, key=lambda ban: ban.seq)

    async def put(self, record: VariantRecord, body: bytes, *, keep: int, replaces: Optional[uuid.UUID] = None) -> bool:
        stored = {
            "key": record.key,
            "variant": record.variant,
            "entry_id": str(record.entry_id),
            "endpoint": record.endpoint,
            "stamp": record.stamp,
            "status": record.status,
            "body_digest": record.body_digest,
            "body_size": record.body_size,
            "created_at": repr(record.created_at),
            "stored_at": repr(record.stored_at),
            "head": record.head,
        }
        if record.vary is not None:
            stored["vary"] = record.vary
        if record.query is not None:
            stored["query"] = record.query
        bans = [*_fields(record.key, BanMode.HARD), *_fields(record.key, BanMode.SOFT)]
        return bool(
            await self._put(
                args=[
                    self.prefix,
                    str(record.entry_id),
                    record.key,
                    record.variant,
                    record.endpoint,
                    record.stamp,
                    repr(record.stored_at),
                    record.body_digest,
                    record.body_size,
                    keep,
                    str(replaces) if replaces else "",
                    int((time.time() + self.retention) * 1000),
                    body,
                    len(bans),
                    *bans,
                    *(item for pair in stored.items() for item in pair),
                ]
            )
        )

    async def reclaim(self, *, older_than: float, bans: int, entries: int) -> Reclaimed:
        old = [ban for ban in await self.bans() if ban.created_at < older_than]
        all_hard = [ban for ban in old if ban.mode is BanMode.HARD]
        # every soft ban is checked, stuck ones included: they must not hide the ones behind them
        hard, soft = all_hard[:bans], [ban for ban in old if ban.mode is BanMode.SOFT]
        if hard or soft:
            # before anything is deleted or retired: no new fill stamped below these bans (fills are scripts, so none is
            # in flight)
            await self._raise_floor(args=[self.prefix, max(ban.seq for ban in hard + soft)])

        retired = deleted = 0
        pending = len(all_hard) > bans
        for ban in hard:
            done, count = await self._drain(ban, entries - deleted)
            deleted += count
            if not done:
                pending = True
                continue
            retired += await self._retire_ban(ban)
        for ban in soft:
            if not (await self._drain(ban, 0, probe=True))[0]:
                continue  # one is still stale
            retired += await self._retire_ban(ban)
        return Reclaimed(retired, deleted, pending)

    async def _retire_ban(self, ban: Ban) -> int:
        return await self._retire(args=[self.prefix, _ban_field(ban.kind, ban.prefix, ban.mode), ban.seq])

    async def _ranges(self, ban: Ban) -> AsyncIterator[tuple[str, str, str]]:
        """The ranges of keys a ban covers, as ``(endpoint, lowest, highest)`` for ``ZRANGEBYLEX``."""
        endpoints = [endpoint_of(ban.prefix)] if ban.prefix else await self._endpoints()
        for endpoint in endpoints:
            for low, high in covered_ranges(ban.kind, ban.prefix):
                yield endpoint, "[" + low if low else "-", "+" if high is None else "(" + high

    async def _endpoints(self) -> list[str]:
        return [_text(endpoint) for endpoint in await self.client.zrangebylex(f"{self.prefix}endpoints", "-", "+")]

    async def _drain(self, ban: Ban, limit: int, *, probe: bool = False) -> tuple[bool, int]:
        """Delete at most ``limit`` of the variants a ban covers, stamped below it. Tells whether that was all of them,
        and how many went. With ``probe``, delete nothing, and tell whether none is left."""
        deleted = 0
        async for endpoint, low, high in self._ranges(ban):
            after = ""
            while True:
                count, after_key, state = await self._covered(
                    args=[
                        self.prefix,
                        endpoint,
                        low,
                        high,
                        after,
                        ban.seq,
                        SCAN_PAGE,
                        limit - deleted,
                        "probe" if probe else "delete",
                    ]
                )
                deleted += count
                if state in (2, 3):
                    return False, deleted
                if state == 0:
                    break
                after = _text(after_key)
        return True, deleted

    async def reclaim_orphans(self, *, limit: int) -> int:
        """Delete the bodies no variant refers to, looking at one page of the bodies at a time, and the next page next
        time. A resource is deleted with its last variant, and a variant is one script: none is ever orphaned."""
        self._orphan_cursor, keys = await self.client.scan(
            self._orphan_cursor, match=_glob_escape(self.prefix) + "b:*", count=ORPHAN_PAGE
        )
        digests = [_text(key).removeprefix(self.prefix + "b:") for key in keys[:limit]]
        if not digests:
            return 0
        return await self._delete_unreferenced_bodies(args=[self.prefix, *digests])

    async def delete_entry(self, entry_id: uuid.UUID) -> bool:
        return bool(await self._delete_entry(args=[self.prefix, str(entry_id)]))

    async def delete_key(self, key: str) -> int:
        return await self._delete_key(args=[self.prefix, key])

    async def delete_stored_before(self, cutoff: float, *, limit: int) -> int:
        return await self._delete_stored_before(args=[self.prefix, repr(cutoff), limit])

    async def list_keys(
        self, *, endpoint: Optional[str] = None, after: Optional[str] = None, limit: int = 100
    ) -> list[str]:
        after_endpoint = endpoint_of(after) if after is not None else None
        endpoints = [endpoint] if endpoint is not None else await self._endpoints()
        keys: list[str] = []
        for name in endpoints:
            if after_endpoint is not None and name < after_endpoint:
                continue
            low = "(" + after if after_endpoint == name else "-"
            page = await self.client.zrangebylex(f"{self.prefix}i:{name}", low, "+", start=0, num=limit - len(keys))
            keys += [_text(key) for key in page]
            if len(keys) >= limit:
                break
        return keys

    async def stats(self) -> list[EndpointStats]:
        async with self.client.pipeline(transaction=False) as pipe:
            for name in ("entries", "bytes", "refused"):
                pipe.hgetall(f"{self.prefix}stats:{name}")
            entries, size, refused = [{_text(k): int(v) for k, v in h.items()} for h in await pipe.execute()]
        return [
            EndpointStats(endpoint, entries.get(endpoint, 0), size.get(endpoint, 0), refused.get(endpoint, 0))
            for endpoint in sorted(entries.keys() | refused.keys())
        ]

    async def count_refused(self, endpoint: str, count: int = 1) -> None:
        await self.client.hincrby(f"{self.prefix}stats:refused", endpoint, count)

    async def largest(self, *, endpoint: Optional[str] = None, limit: int = 10) -> list[VariantRecord]:
        index = f"{self.prefix}size" if endpoint is None else f"{self.prefix}size:{endpoint}"
        ids = await self.client.zrevrange(index, 0, limit - 1)
        async with self.client.pipeline(transaction=False) as pipe:
            for entry_id in ids:
                pipe.hgetall(f"{self.prefix}v:{_text(entry_id)}")
            found = await pipe.execute()
        return [_record([item for pair in flat.items() for item in pair]) for flat in found if flat]

    async def body_digests(self) -> set[str]:
        stem = self.prefix + "b:"
        return {
            _text(key).removeprefix(stem)
            async for key in self.client.scan_iter(match=_glob_escape(stem) + "*", count=ORPHAN_PAGE)
        }
