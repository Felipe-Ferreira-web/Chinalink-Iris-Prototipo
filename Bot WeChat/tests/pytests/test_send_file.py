"""Caracterização de send_file: anexa via diálogo nativo "Select File"
(aninhado, não no desktop), confirma e clica Send. pywinauto mockado —
verificação real é manual (ver docs/README.md)."""

from contextlib import ExitStack
from unittest.mock import MagicMock, patch

from wechat import wechat


def _find_one_by_label(mapping):
    def _side_effect(window, error_label, *args, **kwargs):
        return mapping[error_label]
    return _side_effect


def _patch_wechat_internals(stack):
    # Patch em wechat.wechat (não wechat.X): é o módulo onde as funções
    # foram definidas, e é lá que o nome é resolvido em tempo de chamada.
    return {
        "open_chat": stack.enter_context(patch("wechat.wechat.open_chat")),
        "find_nested_window_by_title": stack.enter_context(
            patch("wechat.wechat._find_nested_window_by_title")
        ),
        "set_clipboard_text": stack.enter_context(patch("wechat.wechat._set_clipboard_text")),
        "random_delay": stack.enter_context(patch("wechat.wechat._random_delay")),
        "focus_window": stack.enter_context(patch("wechat.wechat._focus_window")),
        "find_one": stack.enter_context(patch("wechat.wechat._find_one")),
    }


def test_sends_file_successfully():
    with ExitStack() as stack:
        mocks = _patch_wechat_internals(stack)
        window = MagicMock()

        send_file_button = MagicMock()
        dialog = MagicMock()
        filename_field = MagicMock()
        open_button = MagicMock()
        send_button = MagicMock()

        mocks["find_nested_window_by_title"].return_value = dialog
        mocks["find_one"].side_effect = _find_one_by_label({
            "Botão 'Send File'": send_file_button,
            "Campo de nome de arquivo": filename_field,
            "Botão 'Open'": open_button,
            "Botão 'Send'": send_button,
        })

        wechat.send_file(window, "Felipe", "C:\\arquivo.txt")

        mocks["open_chat"].assert_called_once_with(window, "Felipe")
        send_file_button.click_input.assert_called_once()
        filename_field.type_keys.assert_any_call("^a", pause=0.05)
        filename_field.type_keys.assert_any_call("^v", pause=0.05)
        mocks["set_clipboard_text"].assert_any_call("C:\\arquivo.txt")
        open_button.click_input.assert_called_once()
        send_button.click_input.assert_called_once()
