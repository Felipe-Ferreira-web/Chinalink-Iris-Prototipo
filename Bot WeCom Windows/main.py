"""Testa envio + leitura de mensagem via pywinauto (ver wechat.py).

Substitui a versão antiga baseada no wxauto4 (abandonado — ver README).

Uso:
    python main.py                     # só lê e imprime as mensagens de TARGET_CHAT_NAME
    python main.py --test-reply        # além de ler, manda TEST_MESSAGE (do .env) antes
    python main.py --test-reply "oi"   # manda esse texto específico em vez de TEST_MESSAGE
"""

from __future__ import annotations

import argparse
import logging

import wechat
from config import load_config, setup_logging

log = logging.getLogger("main")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--test-reply",
        nargs="?",
        const="__use_config__",
        default=None,
        help="Envia uma mensagem de teste para TARGET_CHAT_NAME antes de ler. "
        "Sem valor, usa TEST_MESSAGE do .env.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config()
    setup_logging(config.log_level)

    log.info("Procurando janela do WeChat...")
    window = wechat.find_wechat_window()
    log.info("Conectado: %r", window.window_text())

    if args.test_reply is not None:
        text = config.test_message if args.test_reply == "__use_config__" else args.test_reply
        log.info("Enviando mensagem de teste para %s: %r", config.target_chat_name, text)
        wechat.send_message(window, config.target_chat_name, text)
        log.info("Enviado.")

    log.info("Lendo mensagens de '%s'...", config.target_chat_name)
    messages = wechat.read_messages(window, config.target_chat_name)
    log.info("%d mensagens de texto encontradas:", len(messages))
    for text in messages:
        log.info("  %s", text)


if __name__ == "__main__":
    main()
