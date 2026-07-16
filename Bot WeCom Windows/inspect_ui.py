"""Dump da árvore real de controles do WeChat, via pywinauto (UI Automation).

Sem efeito colateral: não clica em nada, só lê e salva a árvore de
controles da janela do WeChat já aberta. Serve pra descobrir os nomes,
classes e tipos REAIS dos elementos (caixa de busca, lista de conversas
na sidebar, campo de digitar mensagem, botão de enviar) antes de escrever
qualquer automação em cima disso — em vez de confiar nos nomes "chutados"
pelo fork wxauto4 (gerado por IA a partir só da documentação, nunca
testado contra o app de verdade — ver README).

Dump implementado na mão (não usa print_control_identifiers) porque esse
método só existe em WindowSpecification (via Application().connect()),
não nos objetos crus que Desktop().windows() devolve.

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
# Classes de janela de outros apps que só coincidem no título (ex.: uma aba
# do navegador com "微信" no texto) — nunca é a janela real do WeChat.
FALSE_POSITIVE_CLASS_PREFIXES = ("Chrome_WidgetWin",)
MAX_DEPTH = 30


def find_wechat_windows() -> list:
    desktop = Desktop(backend="uia")
    candidates = []
    for window in desktop.windows():
        try:
            title = window.window_text()
            class_name = window.element_info.class_name
        except Exception:
            continue
        if not any(needle in title for needle in TITLE_NEEDLES):
            continue
        if any(class_name.startswith(prefix) for prefix in FALSE_POSITIVE_CLASS_PREFIXES):
            continue
        candidates.append(window)
    # Janelas com classe "mmui::*" são o WeChat de verdade (Qt interno da
    # Tencent) — prioriza essas se houver mais de uma candidata restante.
    candidates.sort(key=lambda w: 0 if w.element_info.class_name.startswith("mmui") else 1)
    return candidates


def dump_node(wrapper, depth: int, out) -> None:
    indent = "  " * depth
    try:
        text = wrapper.window_text()
    except Exception:
        text = "<erro ao ler texto>"
    class_name = wrapper.element_info.class_name
    control_type = getattr(wrapper.element_info, "control_type", None)
    automation_id = getattr(wrapper.element_info, "automation_id", None)
    try:
        rect = wrapper.rectangle()
    except Exception:
        rect = None

    out.write(
        f"{indent}[{control_type}] class={class_name!r} auto_id={automation_id!r} "
        f"text={text!r} rect={rect}\n"
    )

    if depth >= MAX_DEPTH:
        return
    try:
        children = wrapper.children()
    except Exception as exc:
        out.write(f"{indent}  (erro ao listar filhos: {exc})\n")
        return
    for child in children:
        dump_node(child, depth + 1, out)


def main() -> None:
    config = load_config()
    setup_logging(config.log_level)

    log.info("Procurando janelas do WeChat na área de trabalho...")
    candidates = find_wechat_windows()

    if not candidates:
        log.error(
            "Nenhuma janela real do WeChat encontrada (título com "
            "'Weixin'/'WeChat'/'微信', excluindo abas de navegador). Está aberto?"
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
    log.info(
        "Usando a candidata 0 (%r, class=%s). Dumpando árvore de controles em %s...",
        window.window_text(),
        window.element_info.class_name,
        OUTPUT_FILE,
    )
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        dump_node(window, 0, out)
    log.info(
        "Pronto. Abra %s e procura pelos elementos: caixa de busca, lista de "
        "conversas na sidebar, campo de digitar mensagem, botão de enviar.",
        OUTPUT_FILE,
    )


if __name__ == "__main__":
    main()
