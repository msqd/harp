POETRY ?= $(shell which poetry || echo poetry)

.PHONY: start install test


start: install
	$(POETRY) run harp server{% if cookiecutter.create_application %} --enable {{cookiecutter.__pkg_name}}{% endif %}{% if cookiecutter.create_config %} --file config.yml{% endif %}

install:
	$(POETRY) install

test: install
	$(RUN) pytest
