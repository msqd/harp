# kernel: a controller that delegates to an ASGI application

**Problem**

The MCP SDK is an ASGI application. HARP's kernel can let a controller answer in raw ASGI (`AlreadyHandledHttpResponse`, `harp/asgi/kernel.py:66`), but only the dashboard's static assets do it, through a workaround marked "XXX todo fix" that builds a partial scope by hand (`harp_apps/dashboard/controllers/__init__.py:127-142`).

**Acceptance criteria**

- A controller type in the core mounts an ASGI application under a path prefix, passing it the original scope (path rewritten under the prefix, `root_path` set), `receive` and `send`. Streaming responses pass through (test with a streaming ASGI app).
- The dashboard's static assets use it, and the workaround goes (tests for the dashboard UI routes unchanged).
- Lifespan of the mounted application is started and stopped with HARP's own.

**Out of scope**

Websockets.
