"""Caracterização de start_group_chat: seleciona candidatos por nome
via children() (evita o ciclo UIA de sp_choice_contact_list), cancela
se algum nome não existir. pywinauto mockado — verificação real é
manual (ver docs/README.md)."""

from contextlib import ExitStack
from unittest.mock import MagicMock, patch

from wechat import wechat


def _find_direct_child_by_class_by_label(mapping):
    def _side_effect(window, error_label, *args, **kwargs):
        return mapping[error_label]
    return _side_effect


def _find_direct_child_by_auto_id_by_label(mapping):
    def _side_effect(window, error_label, *args, **kwargs):
        return mapping[error_label]
    return _side_effect


def _patch_wechat_internals(stack):
    # Patch em wechat.wechat (não wechat.X): é o módulo onde as funções
    # foram definidas, e é lá que o nome é resolvido em tempo de chamada.
    return {
        "open_start_group_chat_dialog": stack.enter_context(
            patch("wechat.wechat.open_start_group_chat_dialog")
        ),
        "find_direct_child_by_class": stack.enter_context(
            patch("wechat.wechat._find_direct_child_by_class")
        ),
        "find_direct_child_by_auto_id": stack.enter_context(
            patch("wechat.wechat._find_direct_child_by_auto_id")
        ),
        "find_group_candidate": stack.enter_context(patch("wechat.wechat._find_group_candidate")),
        "find_one": stack.enter_context(patch("wechat.wechat._find_one")),
        "get_current_chat_name": stack.enter_context(patch("wechat.wechat.get_current_chat_name")),
        "set_clipboard_text": stack.enter_context(patch("wechat.wechat._set_clipboard_text")),
        "random_delay": stack.enter_context(patch("wechat.wechat._random_delay")),
        "focus_window": stack.enter_context(patch("wechat.wechat._focus_window")),
    }


def test_creates_group_with_two_existing_contacts():
    with ExitStack() as stack:
        mocks = _patch_wechat_internals(stack)
        window = MagicMock()

        dialog = MagicMock()
        wrapper = MagicMock()
        detail_view = MagicMock()
        search_field = MagicMock()
        usuario1_candidate = MagicMock()
        usuario2_candidate = MagicMock()
        finish_button = MagicMock()

        mocks["open_start_group_chat_dialog"].return_value = dialog
        mocks["find_direct_child_by_class"].side_effect = _find_direct_child_by_class_by_label({
            "Wrapper do diálogo": wrapper,
            "Painel de detalhe do grupo": detail_view,
        })
        mocks["find_one"].return_value = search_field
        mocks["find_group_candidate"].side_effect = [usuario1_candidate, usuario2_candidate]
        mocks["find_direct_child_by_auto_id"].side_effect = _find_direct_child_by_auto_id_by_label({
            "Botão 'Finish'": finish_button,
        })
        mocks["get_current_chat_name"].return_value = "Group Chat"

        result = wechat.start_group_chat(window, ["Usuario1", "Usuario2"])

        assert result == "Group Chat"
        mocks["find_group_candidate"].assert_any_call(wrapper, "Usuario1")
        mocks["find_group_candidate"].assert_any_call(wrapper, "Usuario2")
        usuario1_candidate.click_input.assert_called_once()
        usuario2_candidate.click_input.assert_called_once()
        finish_button.click_input.assert_called_once()


def test_cancels_when_a_name_is_not_found():
    with ExitStack() as stack:
        mocks = _patch_wechat_internals(stack)
        window = MagicMock()

        dialog = MagicMock()
        wrapper = MagicMock()
        detail_view = MagicMock()
        search_field = MagicMock()
        usuario1_candidate = MagicMock()
        cancel_button = MagicMock()

        mocks["open_start_group_chat_dialog"].return_value = dialog
        mocks["find_direct_child_by_class"].side_effect = _find_direct_child_by_class_by_label({
            "Wrapper do diálogo": wrapper,
            "Painel de detalhe do grupo": detail_view,
        })
        mocks["find_one"].return_value = search_field
        # "Usuario1" acha, "Teste" (inexistente) não acha -> cancela.
        mocks["find_group_candidate"].side_effect = [usuario1_candidate, None]
        mocks["find_direct_child_by_auto_id"].side_effect = _find_direct_child_by_auto_id_by_label({
            "Botão 'Cancel'": cancel_button,
        })

        result = wechat.start_group_chat(window, ["Usuario1", "Teste"])

        assert result is None
        cancel_button.click_input.assert_called_once()
        mocks["get_current_chat_name"].assert_not_called()
