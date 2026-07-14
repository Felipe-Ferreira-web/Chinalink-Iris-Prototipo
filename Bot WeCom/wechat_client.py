"""Leitura e envio de mensagens no WeChat desktop (Linux) via coordenadas de
tela + OCR (Caminho B — confirmado com `explore_ui.py`: a árvore AT-SPI vem
vazia pra esse app, então não dá pra automatizar de forma semântica).

Coordenadas calibradas contra a janela real (1309x650, ver
`ui_dump/chat_aberto.png` da sessão de calibração) — são RELATIVAS à janela
(somadas a `geometria_janela()["x"/"y"]` pra virar coordenada absoluta de
tela), não a pixels fixos da tela. Se o WeChat mudar de layout/tamanho de
janela, essas constantes precisam ser recalibradas (rodar `explore_ui.py` de
novo e inspecionar o screenshot).
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytesseract
from PIL import Image

from utils import buscar_janela, clicar, colar_texto, dormir, focar_janela, geometria_janela

logger = logging.getLogger(__name__)

TICK_SCREENSHOT = Path("ui_dump/_tick.png")

SIDEBAR_WIDTH = 272

# Caixa de texto de composição — ponto central de uma área ampla e sempre
# vazia (funciona independente do tamanho do texto já digitado).
INPUT_BOX_REL = (700, 550)

# Botão "Send(S)", canto inferior direito do painel de mensagens.
SEND_BUTTON_REL = (1240, 625)

# Área do painel de mensagens (exclui sidebar, cabeçalho do chat e a caixa
# de composição) — usada pra OCR de leitura.
MESSAGE_AREA_REL = (SIDEBAR_WIDTH, 70, 1309, 495)

# Área do título do chat aberto (nome do contato/grupo, topo do painel).
CHAT_TITLE_AREA_REL = (SIDEBAR_WIDTH, 15, 700, 55)

OCR_LANGS = "eng+por"


@dataclass
class IncomingMessage:
    chat_name: str
    text: str


def _capturar_janela(window_id: str) -> Image.Image:
    focar_janela(window_id)
    dormir(0.3)
    TICK_SCREENSHOT.parent.mkdir(exist_ok=True)
    subprocess.run(
        ["spectacle", "-b", "-n", "-a", "-o", str(TICK_SCREENSHOT.resolve())],
        check=True,
        capture_output=True,
    )
    return Image.open(TICK_SCREENSHOT)


def _ocr_texto(imagem: Image.Image, caixa: tuple[int, int, int, int]) -> str:
    recorte = imagem.crop(caixa)
    return pytesseract.image_to_string(recorte, lang=OCR_LANGS).strip()


def _localizar_texto_na_sidebar(imagem: Image.Image, alvo: str) -> tuple[int, int] | None:
    """OCR na sidebar procurando `alvo`; devolve o centro (x,y) relativo à
    janela da linha de texto que contém esse nome, ou None se não achar.

    Tesseract devolve uma palavra por item — nomes com espaço (ex. "File
    Transfer") vêm em itens separados. Por isso agrupamos por linha
    (block_num/par_num/line_num) e comparamos a linha inteira, não palavra a
    palavra.
    """
    sidebar = imagem.crop((0, 0, SIDEBAR_WIDTH, imagem.height))
    dados = pytesseract.image_to_data(sidebar, lang=OCR_LANGS, output_type=pytesseract.Output.DICT)

    linhas: dict[tuple[int, int, int], list[int]] = {}
    for i, texto in enumerate(dados["text"]):
        if not texto.strip():
            continue
        chave = (dados["block_num"][i], dados["par_num"][i], dados["line_num"][i])
        linhas.setdefault(chave, []).append(i)

    # Contém, não igualdade exata: o ícone da conversa às vezes é lido como
    # um caractere-lixo colado antes do nome (ex. ". File Transfer").
    alvo_lower = alvo.lower()
    for indices in linhas.values():
        texto_linha = " ".join(dados["text"][i] for i in indices).strip()
        if alvo_lower in texto_linha.lower():
            esquerda = min(dados["left"][i] for i in indices)
            direita = max(dados["left"][i] + dados["width"][i] for i in indices)
            topo = min(dados["top"][i] for i in indices)
            baixo = max(dados["top"][i] + dados["height"][i] for i in indices)
            return (esquerda + direita) // 2, (topo + baixo) // 2
    return None


def send_message(window_class_name: str, chat_name: str, text: str) -> None:
    """Efeito colateral conhecido: como não há isolamento de sessão (é a
    tela real do colaborador), qualquer clique/foco do usuário no meio da
    sequência pode roubar o foco entre um passo e outro — confirmado ao vivo
    (um `colar_texto` acabou colando no VS Code em vez do WeChat porque o
    usuário estava com o mouse/teclado ativo em outra janela naquele
    instante). Por isso refocamos a janela do WeChat imediatamente antes de
    CADA ação (clique/colagem), não só uma vez no início — reduz a janela de
    corrida, mesmo sem eliminá-la por completo.
    """
    window_id = buscar_janela(window_class_name)
    if not window_id:
        raise RuntimeError(f"Janela '{window_class_name}' não encontrada.")

    geom = geometria_janela(window_id)
    imagem = _capturar_janela(window_id)

    # Causa raiz confirmada ao vivo de um bug bem confuso de debugar: clicar
    # na conversa na sidebar quando ela JÁ é a conversa aberta a FECHA (é um
    # toggle) — daí o clique seguinte na caixa de texto caía no painel vazio
    # (sem chat aberto) e a colagem/envio não iam a lugar nenhum, sem
    # nenhum erro. Por isso é essencial checar o título do chat já aberto
    # (`CHAT_TITLE_AREA_REL`) e só clicar na sidebar se for de fato preciso
    # trocar de conversa. Isso importa ainda mais quando o bot precisar
    # alternar entre várias conversas em sequência — nunca assumir qual
    # conversa está aberta, sempre confirmar antes de agir.
    chat_ja_aberto = _ocr_texto(imagem, CHAT_TITLE_AREA_REL)
    precisa_trocar_de_conversa = chat_name.lower() not in chat_ja_aberto.lower()

    if precisa_trocar_de_conversa:
        posicao = _localizar_texto_na_sidebar(imagem, chat_name)
        if posicao is None:
            raise RuntimeError(
                f"Conversa '{chat_name}' não encontrada na sidebar via OCR. "
                f"Ela está visível na lista sem precisar rolar?"
            )
        focar_janela(window_id)
        dormir(0.3)
        clicar(geom["x"] + posicao[0], geom["y"] + posicao[1])
        dormir(0.8)

    focar_janela(window_id)
    dormir(0.3)
    clicar(geom["x"] + INPUT_BOX_REL[0], geom["y"] + INPUT_BOX_REL[1])
    dormir(0.5)

    focar_janela(window_id)
    dormir(0.3)
    colar_texto(text)
    dormir(0.6)

    focar_janela(window_id)
    dormir(0.3)
    clicar(geom["x"] + SEND_BUTTON_REL[0], geom["y"] + SEND_BUTTON_REL[1])


def read_new_messages(window_class_name: str, ja_vistas: set[str]) -> list[IncomingMessage]:
    """Faz OCR do painel de mensagens do chat atualmente aberto e devolve as
    linhas que ainda não estão em `ja_vistas` (o chamador deve persistir esse
    set entre chamadas — ver main.py).

    Limitação conhecida: não distingue remetente nem detecta troca de chat
    aberto além do título; é uma comparação de linhas de texto, não uma
    leitura estruturada (não temos DOM nem AT-SPI aqui).
    """
    window_id = buscar_janela(window_class_name)
    if not window_id:
        return []

    imagem = _capturar_janela(window_id)
    chat_name = _ocr_texto(imagem, CHAT_TITLE_AREA_REL) or "?"
    texto_bruto = _ocr_texto(imagem, MESSAGE_AREA_REL)

    novas = []
    for linha in texto_bruto.splitlines():
        linha = linha.strip()
        if not linha or linha in ja_vistas:
            continue
        ja_vistas.add(linha)
        novas.append(IncomingMessage(chat_name=chat_name, text=linha))
    return novas
