"""Testa as funções básicas do WeChat mapeadas em wechat.py.

Substitui a versão antiga baseada no wxauto4 (abandonado — ver README).

Uso:
    python main.py                     # só lê e imprime as mensagens de TARGET_CHAT_NAME
    python main.py --test-reply        # além de ler, manda TEST_MESSAGE (do .env) antes
    python main.py --test-reply "oi"   # manda esse texto específico em vez de TEST_MESSAGE
    python main.py --echo-last         # lê a última mensagem de TARGET_CHAT_NAME e reenvia ela mesma
    python main.py --test-add-contact <telefone>          # testa add_contact_by_phone, usa TEST_MESSAGE
    python main.py --test-add-contact <telefone> "texto"  # idem, com mensagem específica
    python main.py --test-start-chat <nome>                # testa find_or_start_chat com um contato já existente
    python main.py --test-start-group <nome1> <nome2> ...  # testa start_group_chat com 2+ contatos já existentes
    python main.py --test-send-file <nome> <caminho>        # testa send_file com um arquivo local
    python main.py --watch-reply                            # vigia todas as conversas, responde mensagem nova com TEST_MESSAGE
    python main.py --watch-reply "texto"                    # idem, com texto específico
    python main.py --test-download-last-file <nome> <pasta>  # testa download_last_document
"""

from __future__ import annotations

import argparse
import logging
import time

import wechat
from config import load_config, setup_logging

WATCH_POLL_INTERVAL_SECONDS = 5

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
    parser.add_argument(
        "--test-start-chat",
        metavar="NOME",
        help="Testa find_or_start_chat: abre conversa com um contato já existente "
        "chamado NOME (com ou sem sessão na sidebar ainda).",
    )
    parser.add_argument(
        "--test-start-group",
        nargs="+",
        metavar="NOME",
        help="Testa start_group_chat: cria grupo com os NOME(s) informados "
        "(contatos já existentes; precisa de 2+ pra virar grupo de verdade).",
    )
    parser.add_argument(
        "--test-send-file",
        nargs=2,
        metavar=("NOME", "CAMINHO"),
        help="Testa send_file: manda o arquivo em CAMINHO (local, caminho completo) "
        "pra conversa NOME.",
    )
    parser.add_argument(
        "--watch-reply",
        nargs="?",
        const="__use_config__",
        default=None,
        help="Vigia todas as conversas (list_unread_sessions) e responde mensagem "
        "nova com esse texto (ou TEST_MESSAGE do .env, se omitido). Loop contínuo, "
        "Ctrl+C pra sair.",
    )
    parser.add_argument(
        "--test-download-last-file",
        nargs=2,
        metavar=("NOME", "PASTA"),
        help="Testa download_last_document: baixa o arquivo mais recente de NOME "
        "pra dentro de PASTA.",
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

    if args.test_start_chat is not None:
        log.info("Abrindo conversa com %r...", args.test_start_chat)
        chat_name = wechat.find_or_start_chat(window, args.test_start_chat)
        if not chat_name:
            log.warning("%r não encontrado nos contatos.", args.test_start_chat)
            return
        log.info("Conversa aberta: %r", chat_name)
        return

    if args.test_start_group is not None:
        log.info("Criando grupo com %r...", args.test_start_group)
        chat_name = wechat.start_group_chat(window, args.test_start_group)
        if not chat_name:
            log.warning(
                "Algum nome em %r não foi encontrado nos contatos — diálogo cancelado.",
                args.test_start_group,
            )
            return
        log.info("Conversa de grupo aberta: %r", chat_name)
        return

    if args.test_send_file is not None:
        chat_name, filepath = args.test_send_file
        log.info("Mandando %r pra %r...", filepath, chat_name)
        wechat.send_file(window, chat_name, filepath)
        log.info("Enviado.")
        return

    if args.test_download_last_file is not None:
        chat_name, save_dir = args.test_download_last_file
        log.info("Baixando arquivo mais recente de %r pra %r...", chat_name, save_dir)
        save_path = wechat.download_last_document(window, chat_name, save_dir)
        log.info("Salvo em: %s", save_path)
        return

    if args.watch_reply is not None:
        text = config.test_message if args.watch_reply == "__use_config__" else args.watch_reply
        log.info(
            "Vigiando todas as conversas (a cada %ds). Ctrl+C pra sair.",
            WATCH_POLL_INTERVAL_SECONDS,
        )
        seen_counts: dict[str, int] = {}
        try:
            while True:
                for chat_name in wechat.list_unread_sessions(window):
                    messages = wechat.read_messages(window, chat_name)
                    seen = seen_counts.get(chat_name, 0)
                    new_messages = messages[seen:]
                    seen_counts[chat_name] = len(messages)
                    if new_messages:
                        log.info("Mensagem(ns) nova(s) em %r: %r", chat_name, new_messages)
                        wechat.send_message(window, chat_name, text)
                        log.info("Respondido em %r.", chat_name)
                time.sleep(WATCH_POLL_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            log.info("Encerrando.")
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
