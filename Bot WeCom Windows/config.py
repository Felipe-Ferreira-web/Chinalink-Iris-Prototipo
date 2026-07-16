"""Carrega e valida a configuração a partir de variáveis de ambiente (.env)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Config:
    target_chat_name: str
    test_message: str
    listen_duration_seconds: float
    log_level: str
    sourcing_server_url: str
    sync_interval_seconds: float
    test_phone: str
    wechat_welcome_message: str


def load_config() -> Config:
    config = Config(
        target_chat_name=_get("TARGET_CHAT_NAME", "File Transfer"),
        test_message=_get("TEST_MESSAGE", "teste automação"),
        listen_duration_seconds=float(_get("LISTEN_DURATION_SECONDS", "30")),
        log_level=_get("LOG_LEVEL", "INFO").upper(),
        sourcing_server_url=_get("SOURCING_SERVER_URL", "http://localhost:8000"),
        sync_interval_seconds=float(_get("SYNC_INTERVAL_SECONDS", "30")),
        test_phone=_get("TEST_PHONE", ""),
        wechat_welcome_message=_get(
            "WECHAT_WELCOME_MESSAGE",
            "Olá! Somos da Chinalink, temos interesse nos seus produtos.",
        ),
    )
    if not config.target_chat_name:
        raise RuntimeError(
            "TARGET_CHAT_NAME não definido. Copie .env.example para .env e preencha."
        )
    return config


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
