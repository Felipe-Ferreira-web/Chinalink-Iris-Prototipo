@echo off
setlocal enabledelayedexpansion

rem Sobe o sistema Iris via Docker Compose num unico terminal, sempre
rem reconstruindo as imagens e liberando antes as portas usadas caso algo ja
rem esteja rodando nelas. Build e servicos de apoio (redis, celery, extension)
rem ficam silenciosos; so os logs de server e client aparecem no terminal.

for /f %%a in ('echo prompt $E ^| cmd') do set "ESC=%%a"
set "RED=%ESC%[0;31m"
set "GREEN=%ESC%[0;32m"
set "CYAN=%ESC%[0;36m"
set "NC=%ESC%[0m"

cd /d "%~dp0"

where docker >nul 2>nul
if errorlevel 1 (
  echo %RED%[iris]%NC% Docker nao encontrado no PATH.
  exit /b 1
)

set "COMPOSE=docker compose"
docker compose version >nul 2>nul
if errorlevel 1 (
  where docker-compose >nul 2>nul
  if errorlevel 1 (
    echo %RED%[iris]%NC% Docker Compose nao encontrado.
    exit /b 1
  )
  set "COMPOSE=docker-compose"
)

set "BUILD_LOG=%TEMP%\iris-build.log"

echo %CYAN%[iris]%NC% INICIANDO...
%COMPOSE% down --remove-orphans >nul 2>nul

rem Rede de seguranca: remove a forca qualquer container deste projeto que o
rem down acima nao tenha pego (ex: renomeado, orfao de um docker-compose.yml antigo).
for /f %%i in ('docker ps -aq --filter "label=com.docker.compose.project=chinalink-iris"') do docker rm -f %%i >nul 2>nul

for %%p in (6379 8000 5173) do call :kill_port %%p

echo %CYAN%[iris]%NC% CONSTRUINDO imagens...
%COMPOSE% build >"%BUILD_LOG%" 2>&1
if errorlevel 1 (
  echo %RED%[iris]%NC% Build falhou:
  type "%BUILD_LOG%"
  del "%BUILD_LOG%" >nul 2>nul
  exit /b 1
)
del "%BUILD_LOG%" >nul 2>nul

%COMPOSE% up -d redis celery extension >nul 2>nul
echo %GREEN%[iris]%NC% PRONTO. Iniciando server e client...

%COMPOSE% up server client

%COMPOSE% down --remove-orphans >nul 2>nul
goto :eof

:kill_port
set "PORT=%1"
set "PID="
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%PORT%" ^| findstr "LISTENING"') do (
  set "PID=%%a"
)
if defined PID taskkill /F /PID %PID% >nul 2>nul
goto :eof
