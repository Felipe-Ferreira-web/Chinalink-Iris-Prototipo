"""Fecha o loop entre o server Django (Busca de Suppliers) e o WeChat: a cada
tick, consulta fornecedores com status=contato_extraido, adiciona o telefone
como contato novo no WeChat, tenta mandar a mensagem de boas-vindas e marca
contato_wechat_enviado no server (pra não repetir depois).

Acha a janela do WeChat UMA VEZ SÓ, fora do loop — é o passo mais lento
confirmado ao vivo (chegou a levar 1 minuto), não faz sentido repetir a
cada iteração.

Aviso importante (não é bug, é como o WeChat funciona): depois do pedido
de amizade, a outra pessoa precisa ACEITAR antes de existir conversa pra
mandar mensagem. Pra um fornecedor recém adicionado, `send_message` pode
falhar até o pedido ser aceito — nesse caso o status NÃO é marcado como
enviado, e a próxima iteração tenta de novo.

Uso:
    python sync_suppliers.py                # loop real, consultando o server
    python sync_suppliers.py --once          # roda 1 passada real (server + WeChat) e sai, sem loop
    python sync_suppliers.py --test-phone    # testa 1 tentativa isolada contra TEST_PHONE, sem server/loop
"""

from __future__ import annotations

import argparse
import logging
import time

import wechat
from config import load_config, setup_logging
from server_client import buscar_suppliers_aguardando_contato, marcar_contato_wechat_enviado

log = logging.getLogger("sync_suppliers")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--test-phone",
        action="store_true",
        help="Testa uma tentativa única contra TEST_PHONE (do .env), sem consultar o server.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Roda uma única passada real (consulta o server, processa quem estiver "
        "pendente, marca enviado) e sai — sem loop.",
    )
    return parser.parse_args()


def _contatar(window, name: str, phone: str, welcome_message: str) -> bool:
    log.info("Adicionando %s (%s) como contato novo no WeChat...", name, phone)
    # O apelido (nickname) real do WeChat quase nunca bate com `name` (nome
    # do fornecedor no Django) ou com `phone` — é ele que fica na sidebar
    # depois (session_item_<apelido>), não o nome/telefone que a gente tinha.
    nickname = wechat.add_contact_by_phone(window, phone, message=welcome_message)
    if not nickname:
        log.warning("Telefone %s não corresponde a nenhum contato do WeChat.", phone)
        return False

    log.info(
        "Pedido de amizade enviado (apelido no WeChat: %r). Tentando mandar a "
        "mensagem de boas-vindas...",
        nickname,
    )
    try:
        wechat.send_message(window, nickname, welcome_message)
    except Exception:
        log.warning(
            "Não deu pra mandar mensagem pra %s (%s) ainda — provavelmente o pedido "
            "de amizade não foi aceito. Tenta de novo no próximo tick.",
            name,
            nickname,
        )
        return False

    log.info("Contato adicionado e mensagem enviada para %s.", name)
    return True


def _processar_pendentes(window, config) -> None:
    suppliers = buscar_suppliers_aguardando_contato(config.sourcing_server_url)
    if not suppliers:
        log.info("Nenhum fornecedor aguardando contato.")
        return

    for supplier in suppliers:
        try:
            sucesso = _contatar(
                window, supplier.name, supplier.contact_phone, config.wechat_welcome_message
            )
            if sucesso:
                marcar_contato_wechat_enviado(config.sourcing_server_url, supplier.id)
                log.info("Marcado contato_wechat_enviado para %s.", supplier.name)
        except Exception:
            log.exception(
                "Falha ao contatar %s (%s) — não marcado como enviado, "
                "tenta de novo no próximo tick.",
                supplier.name,
                supplier.contact_phone,
            )


def main() -> None:
    args = parse_args()
    config = load_config()
    setup_logging(config.log_level)

    log.info("Procurando janela do WeChat...")
    window = wechat.find_wechat_window()
    log.info("Conectado: %r", window.window_text())

    if args.test_phone:
        if not config.test_phone:
            raise RuntimeError("--test-phone requer TEST_PHONE configurado no .env")
        log.info("Teste único contra %s (sem server/loop)...", config.test_phone)
        _contatar(window, config.test_phone, config.test_phone, config.wechat_welcome_message)
        log.info("Teste concluído.")
        return

    if args.once:
        log.info("Passada única (server + WeChat), sem loop...")
        _processar_pendentes(window, config)
        log.info("Concluído.")
        return

    log.info(
        "Loop de sincronização iniciado (a cada %.0fs). Ctrl+C para sair.",
        config.sync_interval_seconds,
    )
    try:
        while True:
            _processar_pendentes(window, config)
            time.sleep(config.sync_interval_seconds)
    except KeyboardInterrupt:
        log.info("Encerrando.")


if __name__ == "__main__":
    main()
