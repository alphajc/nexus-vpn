.PHONY: clean build test-upload upload install dev help

help:
	@echo "nexus-vpn 构建与发布命令"
	@echo ""
	@echo "  make clean       - 清理构建产物"
	@echo "  make build       - 构建 sdist 和 wheel"
	@echo "  make test-upload - 上传到 TestPyPI"
	@echo "  make upload      - 上传到 PyPI"
	@echo "  make install     - 本地安装"
	@echo "  make dev         - 开发模式安装"

clean:
	rm -rf build/ dist/ *.egg-info nexus_vpn.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

build: clean
	python3 -m build

test-upload: build
	python3 -m twine upload --repository testpypi dist/*

upload: build
	python3 -m twine upload dist/*

install: build
	pip install dist/*.whl

dev:
	pip install -e .
