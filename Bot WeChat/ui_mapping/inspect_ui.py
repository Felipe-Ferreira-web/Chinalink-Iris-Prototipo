"""Dump da árvore real de controles do WeChat, via pywinauto (UI Automation).
Sem efeito colateral — só lê, nunca clica. Porquê no docs/README.md.

Uso (de qualquer diretório):
    python ui_mapping/inspect_ui.py                  # janela principal
    python ui_mapping/inspect_ui.py --title "Add Contact"  # outra janela
                                                             # (diálogos)

Dumps sempre vão pra ui_mapping/dumps/, nunca pro diretório atual.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path

from pywinauto import Desktop

# Script vive em ui_mapping/; config.py está um nível acima.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import load_config, setup_logging

log = logging.getLogger("inspect_ui")

DUMPS_DIR = Path(__file__).resolve().parent / "dumps"
DEFAULT_OUTPUT_FILE = "ui_dump.txt"
TITLE_NEEDLES = ("Weixin", "WeChat", "微信")
# Classes de janela de outros apps que só coincidem no título (ex.: uma aba
# do navegador com "微信" no texto) — nunca é a janela real do WeChat. Só se
# aplica na busca padrão (sem --title); um diálogo pedido explicitamente por
# título não precisa desse filtro.
FALSE_POSITIVE_CLASS_PREFIXES = ("Chrome_WidgetWin",)
# Árvore UIA é finita (sem ciclos) — isso não é um corte esperado, é só uma
# rede de segurança contra recursão descontrolada caso algo esteja errado.
SANITY_DEPTH_LIMIT = 200


def find_windows(title_needles: tuple[str, ...], filter_false_positives: bool) -> list:
    desktop = Desktop(backend="uia")
    candidates = []
    for window in desktop.windows():
        try:
            title = window.window_text()
            class_name = window.element_info.class_name
        except Exception:
            continue
        if not any(needle in title for needle in title_needles):
            continue
        if filter_false_positives and any(
            class_name.startswith(prefix) for prefix in FALSE_POSITIVE_CLASS_PREFIXES
        ):
            continue
        candidates.append(window)
    # Janelas com classe "mmui::*" são o app real (Qt interno da Tencent) —
    # prioriza essas se houver mais de uma candidata restante.
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

    if depth >= SANITY_DEPTH_LIMIT:
        # Não é um corte esperado — árvore UIA é finita. Se isso disparar,
        # tem algo errado (loop/ciclo), não falta de profundidade.
        out.write(f"{indent}  !!! limite de segurança ({SANITY_DEPTH_LIMIT}) atingido, parando aqui\n")
        return
    try:
        children = wrapper.children()
    except Exception as exc:
        out.write(f"{indent}  (erro ao listar filhos: {exc})\n")
        return
    for child in children:
        dump_node(child, depth + 1, out)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--title",
        help="Substring do título da janela a inspecionar (ex.: 'Add Contact', "
        "'Send Friend Request'). Sem isso, procura a janela principal do WeChat.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config()
    setup_logging(config.debug)

    if args.title:
        title_needles = (args.title,)
        filter_false_positives = False
        output_file = f"ui_dump_{re.sub(r'[^A-Za-z0-9]+', '_', args.title).strip('_').lower()}.txt"
    else:
        title_needles = TITLE_NEEDLES
        filter_false_positives = True
        output_file = DEFAULT_OUTPUT_FILE

    log.info("Procurando janela com título contendo %r...", title_needles)
    candidates = find_windows(title_needles, filter_false_positives)

    if not candidates:
        log.error("Nenhuma janela encontrada com título contendo %r. Está aberta?", title_needles)
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
    DUMPS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DUMPS_DIR / output_file
    log.info(
        "Usando a candidata 0 (%r, class=%s). Dumpando árvore de controles em %s...",
        window.window_text(),
        window.element_info.class_name,
        output_path,
    )
    with open(output_path, "w", encoding="utf-8") as out:
        dump_node(window, 0, out)
    log.info("Pronto. Abra %s e procura pelos elementos relevantes.", output_path)


if __name__ == "__main__":
    main()
