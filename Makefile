.DEFAULT_GOAL := help

.PHONY: help
help:
	@printf "Available commands:\n"
	@printf "  make start:worker         Start worker with uv\n"
	@printf "  make stack:up             Run docker compose up in stack\n"
	@printf "  make stack:up:background  Run docker compose up -d in stack\n"
	@printf "  make linting              Run Ruff linting\n"
	@printf "  make todo                 List TODO, FIXME, NOTE, HACK, and BUG markers\n"

.PHONY: start\:worker
start\:worker:
	uv run worker.py

.PHONY: stack\:up
stack\:up:
	cd stack && docker compose up

.PHONY: stack\:up\:background
stack\:up\:background:
	cd stack && docker compose up -d

.PHONY: linting
linting:
	uv run ruff check .

.PHONY: todo
todo:
	rg --line-number --heading "TODO|FIXME|NOTE|HACK|BUG"
