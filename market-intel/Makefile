.PHONY: help demo test api pipeline clean fresh lint
DB ?= sqlite:///data/dev.db
PORT ?= 8787

help:
	@grep -E '^[a-z-]+:.*?##' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n",$$1,$$2}'

demo: ## migrate + ingest fixtures + tag + signal + score (offline, no network)
	MI_OFFLINE=1 python3 pipelines/run_pipeline.py --tickers NVDA --db "$(DB)"

pipeline: ## live SEC ingest (needs MI_USER_AGENT and outbound HTTPS)
	python3 pipelines/run_pipeline.py --tickers $(TICKERS) --db "$(DB)" --live

api: ## dev server: API + stock page
	python3 apps/api/server.py --db "$(DB)" --port $(PORT)

test: ## 69 offline tests
	python3 tests/test_all.py

lint: ## byte-compile everything (no linter installed in this env)
	python3 -m compileall -q apps packages collectors pipelines tests && echo "compile OK"

clean: ## remove the dev database
	rm -f data/*.db data/*.db-wal data/*.db-shm

fresh: clean demo ## rebuild the demo database from scratch
