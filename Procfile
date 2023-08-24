back: PYTHONUNBUFFERED=1 watchfiles --filter python --sigint-timeout 10 'python harp/examples/basic.py' harp
front: (cd frontend; pnpm dev)
doc: (cd docs; sphinx-autobuild . _build/html)
ui: (cd vendors/mkui; pnpm serve)
