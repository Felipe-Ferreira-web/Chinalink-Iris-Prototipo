"""Caracterização de add_contact_by_phone — trava o comportamento
confirmado ao vivo em 2026-07-20: abre o diálogo "Add Contacts", digita
o telefone direto por keystrokes (não por clipboard/Ctrl+V — esse campo
especificamente não reagia a paste), decide found/not-found, e manda o
pedido de amizade com ou sem mensagem customizada. pywinauto é todo
mockado aqui; a verificação real é manual, no servidor, contra o WeChat
de verdade (ver README).
"""

from contextlib import ExitStack
from unittest.mock import MagicMock, patch

from wechat import wechat


def _text_mock(text, auto_id=""):
    element = MagicMock()
    element.window_text.return_value = text
    element.element_info.automation_id = auto_id
    return element


def _find_one_by_label(mapping):
    def _side_effect(window, error_label, *args, **kwargs):
        return mapping[error_label]
    return _side_effect


def _patch_wechat_internals(stack):
    # Patch em wechat.wechat (não wechat.X): é o módulo onde as funções
    # foram definidas, e é lá que o nome é resolvido em tempo de chamada.
    return {
        "find_window_by_title": stack.enter_context(patch("wechat.wechat.find_window_by_title")),
        "set_clipboard_text": stack.enter_context(patch("wechat.wechat._set_clipboard_text")),
        "random_delay": stack.enter_context(patch("wechat.wechat._random_delay")),
        "focus_window": stack.enter_context(patch("wechat.wechat._focus_window")),
        "find_one": stack.enter_context(patch("wechat.wechat._find_one")),
        "open_add_contact_dialog": stack.enter_context(patch("wechat.wechat.open_add_contact_dialog")),
    }


def test_found_without_custom_message():
    with ExitStack() as stack:
        mocks = _patch_wechat_internals(stack)

        dialog = MagicMock()
        search_field = MagicMock()
        search_button = MagicMock()
        ok_button = MagicMock()
        add_button = MagicMock()
        close_button = MagicMock()

        mocks["open_add_contact_dialog"].return_value = dialog
        mocks["find_one"].side_effect = _find_one_by_label({
            "Campo de busca": search_field,
            "Botão 'Search'": search_button,
            "Botão 'OK'": ok_button,
            "Botão de fechar": close_button,
        })
        mocks["find_window_by_title"].return_value = MagicMock()
        dialog.descendants.side_effect = lambda **kwargs: (
            [add_button] if kwargs.get("title") == "Add to Contacts"
            else [_text_mock("Felipe", auto_id="display_name_text")]
        )

        result = wechat.add_contact_by_phone(MagicMock(), "5513981496004")

        assert result == "Felipe"
        search_field.type_keys.assert_any_call("5513981496004", pause=0.05)
        assert search_field.click_input.call_count == 2
        search_button.click_input.assert_called_once()
        add_button.click_input.assert_called_once()
        ok_button.click_input.assert_called_once()
        close_button.click_input.assert_called_once()
        mocks["set_clipboard_text"].assert_not_called()


def test_found_with_custom_message():
    with ExitStack() as stack:
        mocks = _patch_wechat_internals(stack)

        dialog = MagicMock()
        search_field = MagicMock()
        search_button = MagicMock()
        message_field = MagicMock()
        ok_button = MagicMock()
        add_button = MagicMock()
        close_button = MagicMock()

        mocks["open_add_contact_dialog"].return_value = dialog
        mocks["find_one"].side_effect = _find_one_by_label({
            "Campo de busca": search_field,
            "Botão 'Search'": search_button,
            "Campo de mensagem do pedido": message_field,
            "Botão 'OK'": ok_button,
            "Botão de fechar": close_button,
        })
        mocks["find_window_by_title"].return_value = MagicMock()
        dialog.descendants.side_effect = lambda **kwargs: (
            [add_button] if kwargs.get("title") == "Add to Contacts"
            else [_text_mock("Felipe", auto_id="display_name_text")]
        )

        result = wechat.add_contact_by_phone(
            MagicMock(), "5513981496004", message="Oi, tudo bem?"
        )

        assert result == "Felipe"
        message_field.type_keys.assert_any_call("^a", pause=0.05)
        message_field.type_keys.assert_any_call("^v", pause=0.05)
        mocks["set_clipboard_text"].assert_any_call("Oi, tudo bem?")
        ok_button.click_input.assert_called_once()
        close_button.click_input.assert_called_once()


def test_not_found_returns_none():
    with ExitStack() as stack:
        mocks = _patch_wechat_internals(stack)

        dialog = MagicMock()
        search_field = MagicMock()
        search_button = MagicMock()
        close_button = MagicMock()

        mocks["open_add_contact_dialog"].return_value = dialog
        mocks["find_one"].side_effect = _find_one_by_label({
            "Campo de busca": search_field,
            "Botão 'Search'": search_button,
            "Botão de fechar": close_button,
        })
        dialog.descendants.side_effect = lambda **_kwargs: [_text_mock("User not found")]

        result = wechat.add_contact_by_phone(MagicMock(), "0000000000000")

        assert result is None
        mocks["find_window_by_title"].assert_not_called()
        close_button.click_input.assert_called_once()
