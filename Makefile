.PHONY: all build run test clean export-ui

all: build

export-ui:
	@echo "==> Building Next.js static export..."
	cd web && npm run build
	@echo "==> Preparing embedded assets for Go binary..."
	rm -rf internal/assets/dist
	cp -r web/out internal/assets/dist

build: export-ui
	@echo "==> Compiling standalone Go binary (smartparking)..."
	go build -ldflags="-s -w" -o smartparking ./cmd/smartparking
	@echo "==> Build completed successfully: ./smartparking"

run:
	./smartparking run

test:
	./smartparking test

clean:
	rm -f smartparking .smartparking.pid
	rm -rf internal/assets/dist
