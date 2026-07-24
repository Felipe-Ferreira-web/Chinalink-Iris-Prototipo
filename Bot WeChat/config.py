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
    test_message: str
    debug: bool
    wechat_storage_root: str


def load_config() -> Config:
    return Config(
        test_message=_get("TEST_MESSAGE", "teste automação"),
        debug=_get("DEBUG", "FALSE").upper() == "TRUE",
        # Específico de máquina/conta — reconfirmar (Settings > Storage
        # location no WeChat) se trocar de servidor ou for pra produção.
        wechat_storage_root=_get(
            "WECHAT_STORAGE_ROOT",
            r"C:\Users\fsantos\Documents\xwechat_files",
        ),
    )


class _ColorFormatter(logging.Formatter):
    """Colore a linha pelo nível: INFO neutro, WARNING amarelo, ERROR+ vermelho."""

    _COLORS = {
        logging.WARNING: "\033[33m",
        logging.ERROR: "\033[31m",
        logging.CRITICAL: "\033[31m",
    }
    _RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        line = super().format(record)
        color = self._COLORS.get(record.levelno)
        return f"{color}{line}{self._RESET}" if color else line


def setup_logging(debug: bool) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(
        _ColorFormatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S")
    )
    logging.basicConfig(level=logging.INFO if debug else logging.WARNING, handlers=[handler])
