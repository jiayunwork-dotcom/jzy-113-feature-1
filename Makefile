.PHONY: help run test docker-build docker-run

help:
	@echo "make run           本地启动服务 (uvicorn :8000)"
	@echo "make test          运行全部测试"
	@echo "make docker-build  构建 Docker 镜像"
	@echo "make docker-run    构建并运行容器 (映射 8000)"

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000

test:
	pytest

docker-build:
	docker build -t flat-rolling-force .

docker-run: docker-build
	docker run --rm -p 8000:8000 flat-rolling-force
