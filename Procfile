back: PYTHONUNBUFFERED=1 watchfiles --filter python --sigint-timeout 1 "bash -c \"lsof -i tcp:4080 | tail -n 1 | awk '{print \$2}' | xargs kill; python harp/examples/basic.py\"" harp
front: (cd frontend; pnpm dev)
doc: (cd docs; sphinx-autobuild . _build/html)
ui: (cd vendors/mkui; pnpm serve)
