#!/bin/sh
# Sobe o sistema Iris via Docker Compose num único terminal, sempre
# reconstruindo as imagens e liberando antes as portas usadas caso algo já
# esteja rodando nelas. Build e serviços de apoio (redis, celery, extension)
# ficam silenciosos; só os logs de server e client aparecem no terminal.

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

log() { printf "${CYAN}[iris]${NC} %s\n" "$1"; }
ok()  { printf "${GREEN}[iris]${NC} %s\n" "$1"; }
err() { printf "${RED}[iris]${NC} %s\n" "$1"; }

if ! command -v docker >/dev/null 2>&1; then
  err "Docker não encontrado no PATH."
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE="docker-compose"
else
  err "Docker Compose não encontrado."
  exit 1
fi

BUILD_LOG="$(mktemp)"
cleanup() { $COMPOSE down --remove-orphans >/dev/null 2>&1; }
trap cleanup INT TERM

log "INICIANDO..."
$COMPOSE down --remove-orphans >/dev/null 2>&1

# Rede de segurança: remove à força qualquer container deste projeto que o
# down acima não tenha pego (ex: renomeado, órfão de um docker-compose.yml antigo).
docker ps -aq --filter "label=com.docker.compose.project=chinalink-iris" 2>/dev/null | xargs -r docker rm -f >/dev/null 2>&1

for port in 6379 8000 5173; do
  pid="$(lsof -ti tcp:"$port" 2>/dev/null || fuser -n tcp "$port" 2>/dev/null | tr -d ':')"
  [ -n "$pid" ] && kill -9 $pid 2>/dev/null
done

log "CONSTRUINDO imagens..."
if ! $COMPOSE build >"$BUILD_LOG" 2>&1; then
  err "Build falhou:"
  cat "$BUILD_LOG"
  rm -f "$BUILD_LOG"
  exit 1
fi
rm -f "$BUILD_LOG"

$COMPOSE up -d redis celery extension >/dev/null 2>&1
ok "PRONTO. Iniciando server e client..."

$COMPOSE up server client

cleanup
