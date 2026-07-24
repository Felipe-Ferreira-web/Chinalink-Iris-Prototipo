"""Constantes e seletores confirmados via dump real (ver docs/README.md).
Usadas por wechat/__init__.py."""

import re

TITLE_NEEDLES = ("Weixin", "WeChat", "微信")
FALSE_POSITIVE_CLASS_PREFIXES = ("Chrome_WidgetWin",)  # classes de outro app, nunca o WeChat real
MESSAGE_TEXT_CLASS = "mmui::ChatTextItemView"
SESSION_ITEM_PREFIX = "session_item_"
CURRENT_CHAT_LABEL_SUFFIX = "current_chat_name_label"
ADD_CONTACTS_MENU_TEXT = "Add Contacts"
ADD_CONTACTS_WINDOW_TITLE = ("Add Contacts",)
SEND_FRIEND_REQUEST_WINDOW_TITLE = ("Send Friend Request",)
USER_NOT_FOUND_TEXT = "User not found"
CLOSE_BUTTON_TEXT = "Disable"  # rótulo real do botão de fechar diálogo
WEIXIN_TAB_TEXT = "Weixin"
CONTACTS_TAB_TEXT = "Contacts"
MESSAGES_BUTTON_TEXT = "Messages"
CONTACT_ITEM_CLASS = "mmui::ContactsCellItemView"
REMARK_VALUE_CLASS = "mmui::ProfileDetailValueRemarkView"
START_GROUP_CHAT_MENU_TEXT = "Start Group Chat"
START_GROUP_CHAT_WINDOW_TITLE = ("Start Group Chat",)
GROUP_CONTACT_ROW_CLASS = "mmui::SPSelectionContactRow"  # lista completa, sem busca
GROUP_SEARCH_RESULT_ROW_CLASS = "mmui::SearchContactCellView"  # resultado após digitar na busca
GROUP_DIALOG_WRAPPER_CLASS = "mmui::XView"  # container geral do diálogo de grupo
GROUP_DETAIL_VIEW_CLASS = "mmui::SPDetailView"  # painel com contatos escolhidos + Cancel/Finish
GROUP_CANDIDATES_VIEW_CLASSES = ("mmui::SPMasterView", "mmui::SearchContactNewChatView")  # lista de candidatos
GROUP_CANCEL_BTN_ID = "cancel_btn"
GROUP_CONFIRM_BTN_ID = "confirm_btn"
SEND_FILE_BUTTON_TEXT = "Send File"
SELECT_FILE_WINDOW_TITLE = ("Select File",)
FILE_NAME_FIELD_LABEL = "File name:"  # rótulo igual em abrir/salvar, mais estável que auto_id
DIALOG_PRIMARY_BUTTON_ID = "1"  # botão de ação primária, mesmo id nos dois diálogos
FILE_BUBBLE_CLASS = "mmui::ChatBubbleItemView"
NOT_DOWNLOADED_MARKER = "Not Downloaded"
UNREAD_MARKER_RE = re.compile(r"^\[(\d+)\]$")  # contagem de não lidas vem como linha de texto
FIND_TIMEOUT_SECONDS = 15.0  # generoso pq o servidor é lento pra chamadas UIA
FIND_POLL_INTERVAL_SECONDS = 0.5
FIND_RETRIES = 5  # tentativas com FIND_POLL_INTERVAL_SECONDS entre elas, sem timeout de tempo
