"""Caracterização de download_last_document: sem clicar em nada,
localiza arquivo já auto-baixado por busca recursiva. pywinauto
mockado; Path/disco reais via tmp_path (ver docs/README.md)."""

from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pytest

from wechat import wechat


def _patch_wechat_internals(stack):
    # Patch em wechat.wechat (não wechat.X): é o módulo onde as funções
    # foram definidas, e é lá que o nome é resolvido em tempo de chamada.
    return {
        "open_chat": stack.enter_context(patch("wechat.wechat.open_chat")),
        "find_one": stack.enter_context(patch("wechat.wechat._find_one")),
    }


def _file_bubble(text):
    bubble = MagicMock()
    bubble.window_text.return_value = text
    bubble.element_info.class_name = wechat.FILE_BUBBLE_CLASS
    return bubble


def test_finds_file_saved_with_wechat_duplicate_suffix(tmp_path):
    storage_root = tmp_path / "xwechat_files"
    target_dir = storage_root / "wxid_x_1234" / "msg" / "file" / "2026-07"
    target_dir.mkdir(parents=True)
    saved_file = target_dir / "arquivo(2).txt"
    saved_file.write_text("conteudo")

    with ExitStack() as stack:
        mocks = _patch_wechat_internals(stack)
        window = MagicMock()
        message_list = MagicMock()
        message_list.children.return_value = [_file_bubble("File\narquivo.txt\n3.8K")]
        mocks["find_one"].return_value = message_list

        result = wechat.download_last_document(window, "Felipe", str(storage_root))

        assert result == str(saved_file)
        mocks["open_chat"].assert_called_once_with(window, "Felipe")


def test_not_downloaded_raises(tmp_path):
    with ExitStack() as stack:
        mocks = _patch_wechat_internals(stack)
        window = MagicMock()
        message_list = MagicMock()
        message_list.children.return_value = [
            _file_bubble("File\narquivo_grande.zip\n50.0MB\nNot Downloaded")
        ]
        mocks["find_one"].return_value = message_list

        with pytest.raises(RuntimeError):
            wechat.download_last_document(window, "Felipe", str(tmp_path))


def test_no_file_message_raises(tmp_path):
    with ExitStack() as stack:
        mocks = _patch_wechat_internals(stack)
        window = MagicMock()
        message_list = MagicMock()
        message_list.children.return_value = []
        mocks["find_one"].return_value = message_list

        with pytest.raises(RuntimeError):
            wechat.download_last_document(window, "Felipe", str(tmp_path))
