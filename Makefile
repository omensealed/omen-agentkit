.PHONY: check test smoke install-smoke install uninstall

check:
	./scripts/check.sh

test:
	python3 -m unittest discover -s tests -v

smoke:
	./scripts/smoke-test.sh

install-smoke:
	./scripts/install-smoke-test.sh

install:
	./install.sh

uninstall:
	./uninstall.sh
