"""Listener de mensagens do WeChat via wxauto4 (AddListenChat), + envio opcional.

Testa o mecanismo de "ler mensagem nova em tempo real" que ficou em
aberto na pasta antiga (`Bot WeCom`, que dependia de OCR comparando linhas
de texto sem saber o remetente de verdade). Aqui a lib despacha um
callback por thread pool interno assim que detecta mensagem nova — não é
polling manual.

Uso:
    python main.py                  # escuta TARGET_CHAT_NAME por LISTEN_DURATION_SECONDS
    python main.py --test-reply     # além de escutar, envia TEST_MESSAGE (do .env) uma vez no início
    python main.py --test-reply "oi"  # envia esse texto específico em vez de TEST_MESSAGE
"""

from __future__ import annotations

import argparse
import logging
import time

from config import load_config, setup_logging

log = logging.getLogger("main")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--test-reply",
        nargs="?",
        const="__use_config__",
        default=None,
        help="Envia uma mensagem de teste para TARGET_CHAT_NAME antes de escutar. "
        "Sem valor, usa TEST_MESSAGE do .env.",
    )
    return parser.parse_args()


def on_message(msg, chat) -> None:
    log.info("[%s] %s: %s", msg.type, getattr(msg, "sender", "?"), msg.content)


def main() -> None:
    args = parse_args()
    config = load_config()
    setup_logging(config.log_level)

    from wxauto4 import WeChat

    wx = WeChat(debug=True)
    log.info("Conectado. nickname=%s", wx.nickname)

    if args.test_reply is not None:
        text = config.test_message if args.test_reply == "__use_config__" else args.test_reply
        log.info("Enviando mensagem de teste para %s: %r", config.target_chat_name, text)
        response = wx.SendMsg(text, who=config.target_chat_name)
        if not response.is_success:
            raise RuntimeError(f"Falha ao enviar mensagem: {response.get('message')}")
        log.info("Envio confirmado.")

    log.info(
        "Escutando %s por %.0fs (Ctrl+C para sair antes)...",
        config.target_chat_name,
        config.listen_duration_seconds,
    )
    wx.AddListenChat(config.target_chat_name, on_message)
    try:
        end_time = time.monotonic() + config.listen_duration_seconds
        while time.monotonic() < end_time:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Interrompido pelo usuário.")
    finally:
        wx.StopListening()
        log.info("Encerrado.")


if __name__ == "__main__":
    main()
