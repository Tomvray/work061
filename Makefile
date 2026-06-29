SHELL := /bin/bash

.PHONY: help build up down run restart logs ps shell clean psql

help:
	@echo "Available targets:"
	@echo "  build    Build Docker images"
	@echo "  up       Start containers in detached mode"
	@echo "  down     Stop and remove containers"
	@echo "  run      Build and start containers"
	@echo "  restart  Restart containers"
	@echo "  logs     Follow container logs"
	@echo "  ps       Show running containers"
	@echo "  shell    Open shell in app container (set SERVICE=name)"
	@echo "  clean    Remove containers, images, and volumes"
	@echo "  psql     Connect to PostgreSQL database"

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

run: build up

restart: down up

logs:
	docker compose logs -f

ps:
	docker compose ps

shell:
	docker compose exec $${SERVICE:-app} sh

clean:
	docker compose down -v --rmi all

psql:
	docker exec -it docker-db-1 psql -U postgres -d patents_db
