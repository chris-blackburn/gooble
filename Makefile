# For kicks and giggles

SRCS := $(wildcard gooble/*.py)

compile: $(SRCS)
	python3 -m compileall $^
.PHONY: compile

env:
	python3 -m venv $@
	@source $@/bin/activate && pip install -r requirements.txt
	@echo \'source $@/bin/activate\' to enter virtual environment

run:
	@PYTHONDONTWRITEBYTECODE=1 python3 -m "gooble"
.PHONY: run

init: env
.PHONY: init

clean:
	rm -rf ./**/__pycache__ ./**/*.pyc
.PHONY: compile
