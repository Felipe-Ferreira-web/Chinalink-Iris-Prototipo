"""Dump da árvore real de controles do WeChat, via pywinauto (UI Automation).

Sem efeito colateral: não clica em nada, só lê e salva a árvore de
controles da janela do WeChat já aberta. Serve pra descobrir os nomes,
classes e tipos REAIS dos elementos (caixa de busca, lista de conversas
na sidebar, campo de digitar mensagem, botão de enviar) antes de escrever
qualquer automação em cima disso — em vez de confiar nos nomes "chutados"
pelo fork wxauto4 (gerado por IA a partir só da documentação, nunca
testado contra o app de verdade — ver README).

Uso:
    python inspect_ui.py
"""

from __future__ import annotations

import logging

from pywinauto import Desktop

from config import load_config, setup_logging

log = logging.getLogger("inspect_ui")

OUTPUT_FILE = "ui_dump.txt"
TITLE_NEEDLES = ("Weixin", "WeChat", "微信")


def find_wechat_windows() -> list:
    desktop = Desktop(backend="uia")
    candidates = []
    for window in desktop.windows():
        try:
            title = window.window_text()
        except Exception:
            continue
        if any(needle in title for needle in TITLE_NEEDLES):
            candidates.append(window)
    return candidates


def main() -> None:
    config = load_config()
    setup_logging(config.log_level)

    log.info("Procurando janelas do WeChat na área de trabalho...")
    candidates = find_wechat_windows()

    if not candidates:
        log.error(
            "Nenhuma janela com 'Weixin'/'WeChat'/'微信' no título. O WeChat está aberto?"
        )
        log.info("Janelas de nível superior encontradas, pra conferência manual:")
        for window in Desktop(backend="uia").windows():
            try:
                log.info(
                    "  - %r (class=%s)",
                    window.window_text(),
                    window.element_info.class_name,
                )
            except Exception:
                continue
        return

    for i, window in enumerate(candidates):
        log.info(
            "Candidata %d: %r (class=%s)",
            i,
            window.window_text(),
            window.element_info.class_name,
        )

    window = candidates[0]
    log.info("Usando a candidata 0. Dumpando árvore de controles em %s...", OUTPUT_FILE)
    window.print_control_identifiers(filename=OUTPUT_FILE)
    log.info(
        "Pronto. Abra %s e procura pelos elementos: caixa de busca, lista de "
        "conversas na sidebar, campo de digitar mensagem, botão de enviar.",
        OUTPUT_FILE,
    )


if __name__ == "__main__":
    main()
