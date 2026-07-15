"""Fecha o loop entre o server Django (Busca de Suppliers) e o WeChat: a cada
tick, consulta fornecedores com status=contato_extraido, busca o telefone no
WeChat, envia pedido de amizade com mensagem fixa e marca
contato_wechat_enviado no server (pra não repetir depois).

Pré-requisito: `python calibrate_add_contact.py` já rodado (gera
ui_dump/add_contact_coords.json) — ver esse script e
`wechat_client.search_and_add_contact` pro porquê.

Uso:
    python sync_suppliers.py                  # loop normal, consultando o server
    python sync_suppliers.py --test-phone      # testa uma vez com TEST_PHONE, sem server/loop
"""

from __future__ import annotations

import argparse
import logging

from config import load_config, setup_logging
from server_client import buscar_suppliers_aguardando_contato, marcar_contato_wechat_enviado
from utils import buscar_janela, dormir
from wechat_client import search_and_add_contact

logger = logging.getLogger(__name__)

# Número usado só pra testar o fluxo do WeChat isoladamente (--test-phone),
# sem precisar do server rodando nem esperar o loop.
TEST_PHONE = "8613572087030"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--test-phone",
        action="store_true",
        help=f"Testa uma tentativa única contra {TEST_PHONE}, sem consultar o server.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config()
    setup_logging(config.log_level)

    if not buscar_janela(config.window_name):
        raise RuntimeError(
            f"Janela '{config.window_name}' não encontrada. O WeChat está aberto?"
        )

    if args.test_phone:
        logger.info("Teste único contra %s (sem server/loop)...", TEST_PHONE)
        search_and_add_contact(config.window_name, TEST_PHONE, config.wechat_welcome_message)
        logger.info("Teste concluído.")
        return

    logger.info("Loop de sincronização iniciado (a cada %.0fs). Ctrl+C para sair.", config.sync_interval_seconds)
    try:
        while True:
            suppliers = buscar_suppliers_aguardando_contato(config.sourcing_server_url)
            if not suppliers:
                logger.debug("Nenhum fornecedor aguardando contato.")

            for supplier in suppliers:
                logger.info("Contatando %s (%s) via WeChat...", supplier.name, supplier.contact_phone)
                try:
                    search_and_add_contact(
                        config.window_name, supplier.contact_phone, config.wechat_welcome_message
                    )
                    marcar_contato_wechat_enviado(config.sourcing_server_url, supplier.id)
                    logger.info("Contato enviado e marcado para %s.", supplier.name)
                except Exception:
                    logger.exception(
                        "Falha ao contatar %s (%s) — não marcado como enviado, tenta de novo no próximo tick.",
                        supplier.name, supplier.contact_phone,
                    )

            dormir(config.sync_interval_seconds)
    except KeyboardInterrupt:
        logger.info("Encerrando.")


if __name__ == "__main__":
    main()
