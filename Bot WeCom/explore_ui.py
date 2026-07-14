"""Ferramenta de diagnóstico — NÃO é o bot final.

Localiza a janela do WeChat (X11/XWayland), tenta dumpar a árvore de
acessibilidade (AT-SPI) e sempre salva um screenshot da janela. O objetivo é
decidir, com dados reais, se a automação vai ser "semântica" (AT-SPI —
Caminho A) ou "por pixel" (screenshot + OCR — Caminho B), em vez de chutar.

Uso:
    python explore_ui.py

Saída em ui_dump/:
    janela.txt       — id/geometria da janela encontrada
    atspi_dump.txt    — árvore de acessibilidade (se disponível)
    screenshot.png     — captura da janela
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from config import load_config, setup_logging
from utils import buscar_janela, focar_janela, geometria_janela, dormir

logger = logging.getLogger(__name__)

DUMP_DIR = Path("ui_dump")

MAX_NODES = 4000
MAX_DEPTH = 40


def salvar_info_janela(window_id: str) -> None:
    geom = geometria_janela(window_id)
    conteudo = f"window_id={window_id}\ngeometria={geom}\n"
    (DUMP_DIR / "janela.txt").write_text(conteudo, encoding="utf-8")
    logger.info("Janela: %s", conteudo.replace("\n", " "))


def salvar_screenshot(window_id: str) -> None:
    """Captura a janela via `spectacle` (portal do KDE), não via `import`
    (ImageMagick): `import -window <id>` retorna imagem vazia neste setup —
    confirmado ao vivo — porque captura X11 legada de janela específica é
    bloqueada pelo compositor Wayland (KWin). `spectacle -a` (janela ativa)
    passa pelo portal e funciona, mas exige que a janela esteja focada antes.
    """
    destino = DUMP_DIR / "screenshot.png"
    focar_janela(window_id)
    dormir(0.5)
    try:
        subprocess.run(
            ["spectacle", "-b", "-n", "-a", "-o", str(destino.resolve())],
            check=True,
            capture_output=True,
        )
        logger.info("Screenshot salvo em %s", destino)
    except subprocess.CalledProcessError as exc:
        logger.warning("Falha ao capturar screenshot: %s", exc.stderr.decode(errors="replace"))


def _dump_atspi_node(no, linhas: list[str], profundidade: int, contador: list[int]) -> None:
    if contador[0] >= MAX_NODES or profundidade > MAX_DEPTH:
        return
    contador[0] += 1
    try:
        nome = no.get_name() or ""
        role = no.get_role_name() or ""
    except Exception as exc:
        linhas.append(f"{'  ' * profundidade}<erro lendo nó: {exc}>")
        return

    texto = ""
    try:
        iface_texto = no.get_text_iface()
        if iface_texto is not None:
            texto = iface_texto.get_text(0, -1) or ""
    except Exception:
        pass

    resumo = f"{'  ' * profundidade}[{role}] name={nome!r}"
    if texto and texto != nome:
        resumo += f" text={texto[:120]!r}"
    linhas.append(resumo)

    try:
        n_filhos = no.get_child_count()
    except Exception:
        return
    for i in range(n_filhos):
        if contador[0] >= MAX_NODES:
            linhas.append(f"{'  ' * (profundidade + 1)}<... limite de {MAX_NODES} nós atingido>")
            return
        try:
            filho = no.get_child_at_index(i)
        except Exception:
            continue
        if filho is not None:
            _dump_atspi_node(filho, linhas, profundidade + 1, contador)


def tentar_dump_atspi(window_class: str) -> bool:
    """Retorna True se conseguiu montar uma árvore não-vazia."""
    try:
        import gi

        gi.require_version("Atspi", "2.0")
        from gi.repository import Atspi
    except Exception as exc:
        logger.warning("gi/Atspi não disponível (%s) — Caminho A inviável.", exc)
        (DUMP_DIR / "atspi_dump.txt").write_text(
            f"gi/Atspi não disponível: {exc}\n", encoding="utf-8"
        )
        return False

    desktop = Atspi.get_desktop(0)
    linhas: list[str] = []
    apps_encontrados = []
    try:
        n_apps = desktop.get_child_count()
    except Exception as exc:
        logger.warning("Não consegui listar apps no desktop AT-SPI (%s).", exc)
        (DUMP_DIR / "atspi_dump.txt").write_text(f"Erro no desktop AT-SPI: {exc}\n", encoding="utf-8")
        return False

    for i in range(n_apps):
        try:
            app = desktop.get_child_at_index(i)
            nome_app = (app.get_name() or "").lower() if app else ""
        except Exception:
            continue
        if app is None:
            continue
        apps_encontrados.append(nome_app)
        if window_class.lower() in nome_app or "wechat" in nome_app or "weixin" in nome_app:
            linhas.append(f"=== App AT-SPI: {nome_app!r} ===")
            _dump_atspi_node(app, linhas, 0, [0])

    if not linhas:
        conteudo = (
            f"Nenhum app AT-SPI encontrado casando com '{window_class}'/'wechat'/'weixin'.\n"
            f"Apps visíveis no desktop AT-SPI: {apps_encontrados}\n"
        )
        (DUMP_DIR / "atspi_dump.txt").write_text(conteudo, encoding="utf-8")
        logger.warning("Árvore AT-SPI vazia para o WeChat. Apps vistos: %s", apps_encontrados)
        return False

    (DUMP_DIR / "atspi_dump.txt").write_text("\n".join(linhas), encoding="utf-8")
    logger.info("Dump AT-SPI salvo com %d linhas.", len(linhas))
    return True


def main() -> None:
    config = load_config()
    setup_logging(config.log_level)
    DUMP_DIR.mkdir(exist_ok=True)

    window_id = buscar_janela(config.window_name)
    if not window_id:
        logger.error(
            "Janela com título '%s' não encontrada. O WeChat está aberto?",
            config.window_name,
        )
        return

    salvar_info_janela(window_id)
    salvar_screenshot(window_id)
    atspi_util = tentar_dump_atspi(config.window_name)

    print()
    if atspi_util:
        print("=> AT-SPI parece viável (Caminho A). Ver ui_dump/atspi_dump.txt.")
    else:
        print(
            "=> AT-SPI não trouxe nada útil (ver ui_dump/atspi_dump.txt). "
            "Caminho B (screenshot + OCR) é o fallback — ver ui_dump/screenshot.png."
        )


if __name__ == "__main__":
    main()
