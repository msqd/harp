# Configuration
SPHINXOPTS ?=
SPHINXBUILD ?= sphinx-build
SOURCEDIR = .
BUILDDIR = _build
WORKDIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

dev:
	sphinx-autobuild "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) --ignore $(WORKDIR)/_tags $(O)

diagrams:
	pyreverse harp.config.events -A -o dot --ignore tests
	dot -Tsvg classes.dot -o core/events.config.svg

	pyreverse harp.asgi.events -A -o dot --ignore tests
	dot -Tsvg classes.dot -o core/events.asgi.svg

	-@rm -f *.dot

.PHONY: help Makefile diagrams dev

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
