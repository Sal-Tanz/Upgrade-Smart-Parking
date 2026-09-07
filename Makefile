.PHONY: all build run test clean export-ui export-models rebuild

all: build

export-ui:
	@echo "==> Building Next.js static export..."
	cd web && npm run build
	@echo "==> Preparing embedded assets for Go binary..."
	rm -rf internal/assets/dist
	cp -r web/out internal/assets/dist

export-models:
	@echo "==> Preparing embedded ML model weights for Go binary..."
	mkdir -p internal/assets/models
	@if [ -f ml/models/best.pt ]; then cp ml/models/best.pt internal/assets/models/best.pt; fi
	@if [ -f yolov8n.pt ]; then cp yolov8n.pt internal/assets/models/yolov8n.pt; fi
	@if [ -f yolo26n.pt ]; then cp yolo26n.pt internal/assets/models/yolo26n.pt; fi

build: export-models
	@if [ ! -d internal/assets/dist ]; then $(MAKE) export-ui; fi
	@echo "==> Compiling standalone Go binary (smartparking)..."
	go build -ldflags="-s -w" -o smartparking ./cmd/smartparking
	@echo "==> Build completed successfully: ./smartparking"

rebuild: export-ui export-models
	@echo "==> Compiling standalone Go binary (smartparking)..."
	go build -ldflags="-s -w" -o smartparking ./cmd/smartparking
	@echo "==> Build completed successfully: ./smartparking"

run:
	./smartparking run

test:
	./smartparking test

clean:
	rm -f smartparking .smartparking.pid
	rm -rf internal/assets/dist internal/assets/models
