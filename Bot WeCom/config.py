"""Carrega e valida a configuração a partir de variáveis de ambiente (.env)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _get(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.environ.get(name, default)
    if required and not value:
        raise RuntimeError(
            f"Variável de ambiente obrigatória não definida: {name}. "
            f"Copie .env.example para .env e preencha."
        )
    return value or ""


@dataclass(frozen=True)
class Config:
    window_name: str
    target_chat_name: str
    log_level: str
    sourcing_server_url: str
    wechat_welcome_message: str
    sync_interval_seconds: float


def load_config() -> Config:
    return Config(
        # Título da janela principal do wechat-bin — varia entre sessões
        # ("Weixin" numa, "WeChat" noutra, confirmado ao vivo); ver
        # utils.buscar_janela para o porquê de usar "|" e _NET_CLIENT_LIST
        # em vez de WM_CLASS ou xdotool search.
        window_name=_get("WECHAT_WINDOW_NAME", "WeChat|Weixin"),
        target_chat_name=_get("TARGET_CHAT_NAME", ""),
        log_level=_get("LOG_LEVEL", "INFO").upper(),
        sourcing_server_url=_get("SOURCING_SERVER_URL", "http://localhost:8000"),
        wechat_welcome_message=_get(
            "WECHAT_WELCOME_MESSAGE",
            "Olá! Somos da Chinalink, temos interesse nos seus produtos.",
        ),
        sync_interval_seconds=float(_get("SYNC_INTERVAL_SECONDS", "30")),
    )


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
