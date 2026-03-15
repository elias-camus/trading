PYTHON ?= python3

.PHONY: test run-paper summarize

test:
	$(PYTHON) -m unittest discover -s tests -t . -v

run-paper:
	PYTHONPATH=src $(PYTHON) -m trading_bot run-paper-bot --config bots/cex_swing/config.example.json

summarize:
	PYTHONPATH=src $(PYTHON) -m trading_bot summarize-records --root data/runtime/records --bot paper-cex-swing
