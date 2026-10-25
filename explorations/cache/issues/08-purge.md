# http_cache: PURGE as an invalidation

**Problem**

#801 (0.13) adds `PURGE /path` behind an IP allow-list on today's store. The new store must keep it working as a ban.

**Acceptance criteria**

- Once #801 is on main and merged into this branch, `PURGE` appends an exact-key ban (or a prefix ban if #801's successor allows it), hard by default, with #801's responses and allow-list unchanged.
- A PURGE is traffic, kept by the transaction record; it is not an audit event (explore/audit decision 10).

**Out of scope**

Changing #801's contract.
