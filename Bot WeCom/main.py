"""Loop de leitura + envio no WeChat desktop (sem IA — ver README.md).

Cada tick: (a) janela do WeChat existe? senão avisa e espera; (b) OCR do
painel de mensagens do chat atualmente aberto, imprime linhas novas; (c) se
`--test-reply` foi passado, envia essa mensagem pra TARGET_CHAT_NAME uma
única vez (pra validar o envio); (d) senão espera o próximo tick.

Uso:
    python main.py                       # só lê e imprime mensagens novas do chat aberto
    python main.py --test-reply "oi"     # também envia essa msg pra TARGET_CHAT_NAME uma vez
"""

from __future__ import annotations

import argparse
import logging

from config import load_config, setup_logging
from utils import buscar_janela, dormir
from wechat_client import read_new_messages, send_message

logger = logging.getLogger(__name__)

TICK_SECONDS = 4.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--test-reply",
        help="Envia esse texto para TARGET_CHAT_NAME uma única vez, para validar o envio.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config()
    setup_logging(config.log_level)

    if args.test_reply and not config.target_chat_name:
        raise RuntimeError("--test-reply requer TARGET_CHAT_NAME configurado no .env")

    if not buscar_janela(config.window_name):
        raise RuntimeError(
            f"Janela '{config.window_name}' não encontrada. O WeChat está aberto?"
        )

    ja_vistas: set[str] = set()
    ja_testou_envio = False
    logger.info("Loop iniciado. Ctrl+C para sair.")
    try:
        while True:
            for msg in read_new_messages(config.window_name, ja_vistas):
                print(f"[{msg.chat_name}] {msg.text}")

            if args.test_reply and not ja_testou_envio:
                logger.info("Enviando mensagem de teste para %s", config.target_chat_name)
                send_message(config.window_name, config.target_chat_name, args.test_reply)
                ja_testou_envio = True

            dormir(TICK_SECONDS)
    except KeyboardInterrupt:
        logger.info("Encerrando.")


if __name__ == "__main__":
    main()
