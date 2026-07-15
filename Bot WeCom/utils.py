"""Wrappers finos sobre `xdotool`/`xclip` (automação X11) + sleep/jitter.

O WeChat desktop (wechat-bin) roda como cliente X11 via XWayland
(QT_QPA_PLATFORM=xcb, confirmado no sandbox config) — por isso ferramentas
X11 alcançam a janela mesmo numa sessão Wayland.
"""

from __future__ import annotations

import logging
import random
import re
import subprocess
import time

logger = logging.getLogger(__name__)


def dormir(segundos: float) -> None:
    time.sleep(segundos)


def aleatorio(minimo: float, maximo: float) -> float:
    return minimo + random.random() * (maximo - minimo)


def _run(cmd: list[str]) -> str:
    resultado = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return resultado.stdout.strip()


def buscar_janela(window_name: str) -> str | None:
    """Retorna o id (decimal) da janela de topo cujo título contém
    `window_name` (case-insensitive) — ou, se `window_name` tiver `|`,
    qualquer uma das alternativas —, ou None se não encontrar.

    O título da janela principal do wechat-bin varia entre sessões ("Weixin"
    numa, "WeChat" noutra, confirmado ao vivo) — por isso o valor padrão em
    `config.py` é "WeChat|Weixin".

    Nem `xdotool search --class` nem `--name` são confiáveis aqui: --class
    "wechat" casa com sub-janelas minúsculas (tooltip, ícone de bandeja —
    confirmado ao vivo, uma de 223x208 veio antes da janela real de
    1309x650); e --name com regex livre casa "WeChat" dentro de
    "WeChatAppEx" (janela auxiliar de mini-programas) e ainda pode achar
    mais de uma janela com título idêntico (o título mudou de "Weixin" pra
    "WeChat" entre uma sessão e outra do mesmo app — não é estável).

    Por isso filtramos pelas janelas listadas em `_NET_CLIENT_LIST` da raiz
    — só janelas de topo de verdade, gerenciadas pelo window manager,
    excluindo tooltips/popups/janelas auxiliares — e comparamos o título
    exato dessas.
    """
    try:
        saida_raiz = _run(["xprop", "-root", "_NET_CLIENT_LIST"])
    except subprocess.CalledProcessError:
        return None

    ids_hex = re.findall(r"0x[0-9a-fA-F]+", saida_raiz)
    alvos = [alt.lower() for alt in window_name.split("|") if alt]
    for id_hex in ids_hex:
        try:
            saida_nome = _run(["xprop", "-id", id_hex, "_NET_WM_NAME"])
        except subprocess.CalledProcessError:
            continue
        nome_lower = saida_nome.lower()
        if any(alvo in nome_lower for alvo in alvos):
            return str(int(id_hex, 16))
    return None


def titulo_janela(window_id: str) -> str:
    """Título (_NET_WM_NAME) da janela — usado só pra diagnóstico/aviso
    (ex: confirmar que a janela ativa capturada é mesmo o WeChat e não o
    terminal/IDE, ver calibrate_add_contact.py)."""
    try:
        saida = _run(["xprop", "-id", window_id, "_NET_WM_NAME"])
    except subprocess.CalledProcessError:
        return ""
    return saida.partition("=")[2].strip().strip('"')


def buscar_janela_por_nome(padrao: str) -> str | None:
    """Acha uma janela pelo NOME via `xdotool search --name` — diferente de
    `buscar_janela` (que só olha `_NET_CLIENT_LIST`, isto é, janelas
    gerenciadas pelo window manager como top-level de verdade).

    Necessário pra diálogos do WeChat tipo "Add Contacts" e "Send Friend
    Request": são janelas de verdade (têm geometria própria, título
    próprio), mas não aparecem em `_NET_CLIENT_LIST` — confirmado ao vivo,
    o método antigo simplesmente não as via, fazendo a automação tratar
    tudo como se fosse desenhado dentro da janela principal do WeChat, o
    que é falso.

    Se mais de uma janela casar com `padrao`, devolve a ÚLTIMA da lista
    (heurística: costuma ser a mais recente/a que acabou de abrir).
    """
    try:
        saida = _run(["xdotool", "search", "--name", padrao])
    except subprocess.CalledProcessError:
        return None
    ids = [linha for linha in saida.splitlines() if linha.strip()]
    return ids[-1] if ids else None


def geometria_janela(window_id: str) -> dict:
    """Retorna {"x":..,"y":..,"width":..,"height":..} da janela via xdotool."""
    saida = _run(["xdotool", "getwindowgeometry", "--shell", window_id])
    dados = {}
    for linha in saida.splitlines():
        chave, _, valor = linha.partition("=")
        if chave in ("X", "Y", "WIDTH", "HEIGHT"):
            dados[chave.lower()] = int(valor)
    return dados


def focar_janela(window_id: str) -> None:
    # Sem "--sync": no KWin/Wayland esse flag pode nunca receber a
    # confirmação esperada e travar indefinidamente (visto ao vivo). Um
    # `dormir()` curto depois de chamar essa função é suficiente.
    _run(["xdotool", "windowactivate", window_id])


def mover_mouse(x: int, y: int) -> None:
    # `xdotool mousemove` não move o ponteiro de verdade aqui (bloqueio do
    # Wayland/KWin ao warp via XTest, confirmado ao vivo). `ydotool` (uinput)
    # contorna isso — exige `ydotoold` rodando e o usuário no grupo `input`.
    #
    # NOTA: uma tentativa de correção por delta relativo em malha fechada
    # (usando `xdotool getmouselocation` como leitura de posição atual) foi
    # testada e descartada — a leitura não é confiável nesse setup
    # (XWayland/multi-monitor), e o loop acabou perseguindo um alvo errado
    # e jogando o cursor pra fora da tela. Voltamos ao absoluto simples,
    # sem malha de correção, até validar isso com mais cuidado.
    _run(["ydotool", "mousemove", "--absolute", "-x", str(x), "-y", str(y)])


def clicar(x: int, y: int) -> None:
    mover_mouse(x, y)
    dormir(0.1)
    _run(["ydotool", "click", "0xC0"])


def colar_texto(texto: str) -> None:
    """Copia `texto` pro clipboard (via xclip) e cola com Ctrl+V — mais
    confiável que `xdotool type` pra acentos/unicode.
    """
    subprocess.run(
        ["xclip", "-selection", "clipboard"],
        input=texto,
        text=True,
        check=True,
    )
    _run(["xdotool", "key", "ctrl+v"])


def tecla(nome: str) -> None:
    _run(["xdotool", "key", nome])


def janela_ativa() -> str | None:
    """Id da janela em foco agora (o popup mais recente, se um estiver
    aberto). Usada pra ancorar cliques na janela certa mesmo quando ela
    aparece em posição variável na tela — ver wechat_client.py.

    `xdotool getactivewindow` às vezes devolve um id de janela "fantasma"
    com geometria degenerada (visto ao vivo: x=-1, y=-1, 1x1 — provavelmente
    algum overlay/proxy interno do KWin, não a janela real em foco). Usar
    essa geometria pra calcular posição de clique quebra tudo (recorte de
    imagem com coordenadas fora dos limites). Por isso validamos a
    geometria aqui e devolvemos None (o chamador cai no fallback pra
    `window_id` conhecido) se ela parecer bogus.
    """
    try:
        candidato = _run(["xdotool", "getactivewindow"])
    except subprocess.CalledProcessError:
        return None
    try:
        geom = geometria_janela(candidato)
    except subprocess.CalledProcessError:
        return None
    if geom.get("width", 0) <= 1 or geom.get("height", 0) <= 1:
        return None
    return candidato


def posicao_mouse() -> tuple[int, int]:
    """Posição absoluta do cursor na tela (x, y) — usado pela calibração
    interativa (ver `calibrate_add_contact.py`): o usuário só move o mouse até
    o elemento e pede pra registrar, sem precisar clicar nem adivinhar
    coordenada de cabeça.
    """
    saida = _run(["xdotool", "getmouselocation", "--shell"])
    dados = {}
    for linha in saida.splitlines():
        chave, _, valor = linha.partition("=")
        if chave in ("X", "Y"):
            dados[chave] = int(valor)
    return dados["X"], dados["Y"]
