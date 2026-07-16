"""Automação mínima do WeChat via pywinauto, em cima de seletores REAIS
inspecionados com inspect_ui.py (ver ui_dump.txt) — não adivinhados.

Cobre só o que o Iris precisa: abrir uma conversa, enviar mensagem, ler
mensagens. Não tenta replicar a API inteira de um "wxauto" (ver README,
seção "Tentativa abandonada").

Seletores confirmados no dump real:
- Item de conversa na sidebar: auto_id='session_item_<Nome>', dentro da
  lista auto_id='session_list'.
- Campo de digitar mensagem: auto_id='chat_input_field' (Edit).
- Botão de enviar: text='Send' (classe mmui::XOutlineButton).
- Lista de mensagens: auto_id='chat_message_list'; itens de texto são
  class='mmui::ChatTextItemView' (outros tipos, ex. ChatItemView, são só
  separador de horário, sem conteúdo de mensagem).
"""

from __future__ import annotations

import time

import win32clipboard
import win32con
from pywinauto import Desktop

TITLE_NEEDLES = ("Weixin", "WeChat", "微信")
# Classes de janela de outros apps que só coincidem no título (ex.: uma aba
# do navegador com "微信" no texto) — nunca é a janela real do WeChat.
FALSE_POSITIVE_CLASS_PREFIXES = ("Chrome_WidgetWin",)
MESSAGE_TEXT_CLASS = "mmui::ChatTextItemView"
SESSION_ITEM_PREFIX = "session_item_"


def find_wechat_window():
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
    candidates.sort(key=lambda w: 0 if w.element_info.class_name.startswith("mmui") else 1)
    if not candidates:
        raise RuntimeError("Janela do WeChat não encontrada. O WeChat está aberto?")
    return candidates[0]


def _find_one(window, error_label: str, auto_id: str | None = None, **kwargs):
    # pywinauto 0.6.9 não aceita auto_id= como filtro direto em
    # descendants()/children() (só class_name/title/control_type são
    # repassados pra build_condition) — filtra auto_id na mão em Python.
    matches = window.descendants(**kwargs)
    if auto_id is not None:
        matches = [m for m in matches if m.element_info.automation_id == auto_id]
    if not matches:
        raise RuntimeError(f"{error_label} não encontrado (auto_id={auto_id!r}, {kwargs}).")
    return matches[0]


def _set_clipboard_text(text: str) -> None:
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
    finally:
        win32clipboard.CloseClipboard()


def list_sessions(window) -> list[str]:
    session_list = _find_one(window, "Lista de conversas", auto_id="session_list")
    names = []
    for item in session_list.children(control_type="ListItem"):
        auto_id = item.element_info.automation_id
        if auto_id.startswith(SESSION_ITEM_PREFIX):
            names.append(auto_id[len(SESSION_ITEM_PREFIX):])
    return names


def open_chat(window, chat_name: str) -> None:
    item = _find_one(
        window,
        f"Conversa '{chat_name}' na sidebar",
        auto_id=f"session_item_{chat_name}",
    )
    item.click_input()
    time.sleep(0.3)


def send_message(window, chat_name: str, text: str) -> None:
    open_chat(window, chat_name)
    input_field = _find_one(window, "Campo de mensagem", auto_id="chat_input_field")
    input_field.click_input()
    _set_clipboard_text(text)
    input_field.type_keys("^v", pause=0.05)
    time.sleep(0.2)
    send_button = _find_one(window, "Botão 'Send'", title="Send", control_type="Button")
    send_button.click_input()


def read_messages(window, chat_name: str | None = None) -> list[str]:
    if chat_name:
        open_chat(window, chat_name)
    message_list = _find_one(window, "Lista de mensagens", auto_id="chat_message_list")
    texts = []
    for item in message_list.children(control_type="ListItem"):
        if item.element_info.class_name == MESSAGE_TEXT_CLASS:
            texts.append(item.window_text())
    return texts
