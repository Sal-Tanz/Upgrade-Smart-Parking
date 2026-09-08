.PHONY: all build run test clean export-ui export-models export-python rebuild release-build

all: build

export-ui:
	@echo "==> Building Next.js static export..."
	cd web && npm run build
	@echo "==> Preparing embedded Web UI assets for Go binary..."
	rm -rf internal/assets/dist
	cp -r web/out internal/assets/dist

export-models:
	@echo "==> Preparing embedded ML model weights for Go binary..."
	mkdir -p internal/assets/models
	@if [ -f ml/models/best.pt ]; then cp ml/models/best.pt internal/assets/models/best.pt; fi
	@if [ -f yolov8n.pt ]; then cp yolov8n.pt internal/assets/models/yolov8n.pt; fi
	@if [ -f yolo26n.pt ]; then cp yolo26n.pt internal/assets/models/yolo26n.pt; fi

export-python:
	@echo "==> Preparing embedded Python backend and ML modules for Go binary..."
	mkdir -p internal/assets/python
	rm -rf internal/assets/python/*
	touch internal/assets/python/.gitkeep
	@if [ -d api ]; then cp -r api internal/assets/python/; fi
	@if [ -d logic ]; then cp -r logic internal/assets/python/; fi
	@if [ -d ml ]; then \
		mkdir -p internal/assets/python/ml; \
		cp -r ml/alpr internal/assets/python/ml/ 2>/dev/null || true; \
		cp -r ml/slot_detection internal/assets/python/ml/ 2>/dev/null || true; \
		cp -r ml/training internal/assets/python/ml/ 2>/dev/null || true; \
		cp -r ml/models internal/assets/python/ml/ 2>/dev/null || true; \
		if [ -f ml/__init__.py ]; then cp ml/__init__.py internal/assets/python/ml/; fi; \
	fi
	@if [ -f gate_detection.py ]; then cp gate_detection.py internal/assets/python/; fi
	@if [ -f test_detection.py ]; then cp test_detection.py internal/assets/python/; fi
	@if [ -f test_video_detection.py ]; then cp test_video_detection.py internal/assets/python/; fi
	@if [ -f test_yolo_video_detection.py ]; then cp test_yolo_video_detection.py internal/assets/python/; fi
	@if [ -f test_yolo-ocr_detection_video.py ]; then cp test_yolo-ocr_detection_video.py internal/assets/python/; fi
	@if [ -f run.py ]; then cp run.py internal/assets/python/; fi
	@if [ -f requirements.txt ]; then cp requirements.txt internal/assets/python/; fi
	@if [ -f .env.example ]; then cp .env.example internal/assets/python/; fi

build: export-models export-python
	@if [ ! -d internal/assets/dist ]; then $(MAKE) export-ui; fi
	@echo "==> Compiling standalone Go binary (smartparking)..."
	CGO_ENABLED=0 go build -ldflags="-s -w" -o smartparking ./cmd/smartparking
	@echo "==> Build completed successfully: ./smartparking"

rebuild: export-ui export-models export-python
	@echo "==> Compiling standalone Go binary (smartparking)..."
	CGO_ENABLED=0 go build -ldflags="-s -w" -o smartparking ./cmd/smartparking
	@echo "==> Build completed successfully: ./smartparking"

release-build: export-models export-python
	@if [ ! -d internal/assets/dist ]; then $(MAKE) export-ui; fi
	@echo "==> Building cross-platform release binaries..."
	mkdir -p bin
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags="-s -w" -o bin/smartparking-linux-amd64 ./cmd/smartparking
	CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -ldflags="-s -w" -o bin/smartparking-linux-arm64 ./cmd/smartparking
	CGO_ENABLED=0 GOOS=darwin GOARCH=amd64 go build -ldflags="-s -w" -o bin/smartparking-darwin-amd64 ./cmd/smartparking
	CGO_ENABLED=0 GOOS=darwin GOARCH=arm64 go build -ldflags="-s -w" -o bin/smartparking-darwin-arm64 ./cmd/smartparking
	CGO_ENABLED=0 GOOS=windows GOARCH=amd64 go build -ldflags="-s -w" -o bin/smartparking-windows-amd64.exe ./cmd/smartparking
	@echo "==> Release binaries built in ./bin"

run:
	./smartparking run

test:
	./smartparking test

clean:
	rm -f smartparking .smartparking.pid
	rm -rf internal/assets/dist internal/assets/models internal/assets/python/*
	touch internal/assets/python/.gitkeep
