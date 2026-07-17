"""Testa as funções básicas do WeChat mapeadas em wechat.py.

Substitui a versão antiga baseada no wxauto4 (abandonado — ver README).

Uso:
    python main.py                     # só lê e imprime as mensagens de TARGET_CHAT_NAME
    python main.py --test-reply        # além de ler, manda TEST_MESSAGE (do .env) antes
    python main.py --test-reply "oi"   # manda esse texto específico em vez de TEST_MESSAGE
    python main.py --echo-last         # lê a última mensagem de TARGET_CHAT_NAME e reenvia ela mesma
    python main.py --test-add-contact <telefone>          # testa add_contact_by_phone, usa TEST_MESSAGE
    python main.py --test-add-contact <telefone> "texto"  # idem, com mensagem específica
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
    parser.add_argument(
        "--echo-last",
        action="store_true",
        help="Lê a última mensagem de TARGET_CHAT_NAME e reenvia ela mesma "
        "(teste de leitura, não só de envio).",
    )
    parser.add_argument(
        "--test-add-contact",
        nargs="+",
        metavar=("TELEFONE", "MENSAGEM"),
        help="Testa add_contact_by_phone: adiciona TELEFONE como contato novo "
        "e manda MENSAGEM (ou TEST_MESSAGE do .env, se omitida).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config()
    setup_logging(config.log_level)

    log.info("Procurando janela do WeChat...")
    window = wechat.find_wechat_window()
    log.info("Conectado: %r", window.window_text())

    if args.test_add_contact is not None:
        phone = args.test_add_contact[0]
        text = args.test_add_contact[1] if len(args.test_add_contact) > 1 else config.test_message
        log.info("Adicionando %s como contato novo no WeChat...", phone)
        nickname = wechat.add_contact_by_phone(window, phone, message=text)
        if not nickname:
            log.warning("Telefone %s não corresponde a nenhum contato do WeChat.", phone)
            return
        log.info("Pedido de amizade enviado (apelido no WeChat: %r). Tentando mandar mensagem...", nickname)
        wechat.send_message(window, nickname, text)
        log.info("Mensagem enviada para %s.", nickname)
        return

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

    if args.echo_last:
        if not messages:
            raise RuntimeError(
                f"Nenhuma mensagem encontrada em '{config.target_chat_name}' pra ecoar."
            )
        last_message = messages[-1]
        log.info("Reenviando a última mensagem lida: %r", last_message)
        wechat.send_message(window, config.target_chat_name, last_message)
        log.info("Ecoado.")


if __name__ == "__main__":
    main()
