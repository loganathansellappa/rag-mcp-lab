# Caching Strategies

## Why Cache

A cache keeps a copy of expensive results close to where they are needed. It lowers latency, reduces load on the database and lets a service survive traffic spikes. The price is that cached data can be stale.

## Cache Aside

The application checks the cache first. On a miss it reads from the database, stores the result in the cache and returns it. Writes go to the database and then delete the cached entry. This is the most common pattern because the cache only holds data that was actually requested.

## Write Through and Write Back

Write through updates the cache and the database together, so reads are always fresh but writes are slower. Write back updates only the cache and flushes to the database later. It is fast but you can lose data if the cache fails before the flush.

## Expiry and Eviction

A time to live, or TTL, removes entries after a fixed time and bounds how stale data can get. When memory is full the cache evicts entries, most often the least recently used one, known as LRU.

## Cache Invalidation

Invalidation means removing or updating entries when the source data changes. It is hard because many keys may depend on one record. Use short TTLs, versioned keys or explicit delete on write, and always measure the hit ratio to see whether the cache helps.
