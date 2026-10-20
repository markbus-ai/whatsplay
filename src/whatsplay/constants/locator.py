# ==============================
# State locators
# ==============================
# Login screen (verified live 2026-10-20, Spanish and English UI): the QR
# canvas sits in data-testid="link-device-qr-code" and its aria-label is
# English in every UI language, so the test ids are used instead of text.
AUTH = '[data-testid="link-device-qr-code"], [data-testid^="link_device_"]'
QR_CODE = '[data-testid="link-device-qr-code"] canvas'
# Shown on top of the canvas when the QR expires ("Selecciona para actualizar
# el código QR"); the old "refresh-large" test id no longer exists.
QR_REFRESH_BUTTON = '[data-testid="link_device_qr_expired_refresh_button"]'
INVALID_NUMBER_WARNING = (
    "//div[contains(text(), 'invalid') or contains(text(), 'no es válido') or contains(text(), 'no está en WhatsApp')]"
)

# Banner inferior de cifrado (cambió el data-icon a 'lock-outline' en algunos builds)
LOADING = "//div[@data-testid='wa-web-loading-screen'] | //span[@data-icon='lock-outline' or @data-icon='lock-refreshed']/ancestor::div[contains(., 'End-to-end encrypted') or contains(., 'Cifrado de extremo a extremo')]"
LOADING_CHATS = "//div[contains(normalize-space(text()), 'Loading your chats') or contains(normalize-space(text()), 'Cargando tus chats')]"
# The wordmark is also on the QR page; only the chat list proves a session
# (verified live: absent on the QR page, present once logged in).
LOGGED_IN = "[data-testid='chat-list']"

# A modal dialog (e.g. "Novedades en WhatsApp Web") intercepts every click
# until it is closed. Only its X button is ever used to dismiss it (verified
# live in the Spanish UI); other buttons such as "Continuar" are never clicked.
BLOCKING_DIALOG = 'div[role="dialog"][aria-modal="true"]'
DIALOG_CLOSE_BUTTON = 'div[role="dialog"][aria-modal="true"] [aria-label="Cerrar"]'

# ==============================
# Navigation buttons
# ==============================
CHATS_BUTTON = "//button[@aria-label='Chats' or @aria-label='Chat' or @aria-label='Chats de WhatsApp' or @aria-label='Conversaciones']"
STATUS_BUTTON = "//button[@aria-label='Status' or @aria-label='Estados']"
CHANNELS_BUTTON = "//button[@aria-label='Channels' or @aria-label='Canales']"
COMMUNITIES_BUTTON = "//button[@aria-label='Communities' or @aria-label='Comunidades']"

# ==============================
# Chat filter buttons (tabs)
# ==============================
ALL_CHATS_BUTTON = "//button[@role='tab'][contains(., 'All') or contains(., 'Todos')]"
UNREAD_CHATS_BUTTON = "//button[@role='tab'][contains(., 'Unread') or contains(., 'No leídos')]"
FAVOURITES_CHATS_BUTTON = "//button[@role='tab'][contains(., 'Favourites') or contains(., 'Favoritos')]"
GROUPS_CHATS_BUTTON = "//button[@role='tab'][contains(., 'Groups') or contains(., 'Grupos')]"
# Selectores semánticos por role (más estables)
ALL_CHATS_ROLE = "button[role='tab']:has-text('All'), button[role='tab']:has-text('Todos')"
UNREAD_CHATS_ROLE = "button[role='tab']:has-text('Unread'), button[role='tab']:has-text('No leídos')"
GROUPS_CHATS_ROLE = "button[role='tab']:has-text('Groups'), button[role='tab']:has-text('Grupos')"
ADDITIONAL_FILTERS_BUTTON = "button#additional-filters"

# ==============================
# Sidebar / Chat list (NUEVO DOM)
# ==============================
# Contenedor del panel lateral
CHAT_LIST_PANE = "//div[@id='pane-side']"
# Grilla virtualizada de chats
CHAT_LIST_GRID = f"{CHAT_LIST_PANE}//div[@role='grid']"
# Filas (cada chat)
CHAT_LIST_ROWS = f"{CHAT_LIST_GRID}//div[@role='row']"
# Badge/indicador de "no leído" (ES/EN)
UNREAD_BADGE = ".//span[@data-testid='icon-unread-count'] | .//span[contains(@aria-label, 'unread') or contains(@aria-label, 'mensaje no leído') or contains(@aria-label, 'mensajes no leídos')]"
# Texto visible de no leidos (nuevo DOM 2026: span inline dentro de cell-frame-title)
UNREAD_BADGE_TEXT = ".//div[@data-testid='cell-frame-title']/span[contains(., 'mensaje') or contains(., 'unread') or contains(., 'message')]"
# Título del chat (estable)
SPAN_TITLE = ".//span[@title]"
# Celda con la hora (en tu build es esta clase semántica, pero la referenciamos por rol de gridcell si cambia)
ROW_TIME = ".//div[@role='gridcell' and @aria-colindex='2']/following-sibling::div[contains(@class,'_ak8i')][1] | .//div[contains(@class,'_ak8i')][1]"

# ==============================
# Search related locators
# ==============================
# Search (verified live 2026-10-20): the side pane has exactly one text input,
# both idle and while searching. Its aria-label ("Buscar un chat o iniciar uno
# nuevo" / "Search or start a new chat") becomes "" while it holds a query, so
# it is located by position and role, not by label.
SEARCH_INPUT = '#side input[type="text"][role="textbox"]'
SEARCH_BUTTON = [SEARCH_INPUT]  # kept for API compatibility

SEARCH_TEXT_BOX = [SEARCH_INPUT]

# Clear-query button shown while searching (label verified live, Spanish UI).
SEARCH_CLOSE_BUTTON = ['#side [aria-label="End icon button"]']

# The side-pane grid: "Lista de chats" idle, "Resultados de la búsqueda." while
# searching (verified live). Messages of the open chat are role=row too, so
# rows must be scoped to this grid.
SEARCH_RESULT = '#pane-side [role="grid"]'
SEARCH_ITEM = '#pane-side [role="grid"] [role="row"]'
# Partes del resultado: columna de título/preview
SEARCH_ITEM_COMPONENTS = ".//div[@role='gridcell' and @aria-colindex='2']/parent::div/div"
# Contador 'unread' dentro del ítem
SEARCH_ITEM_UNREAD_MESSAGES = ".//span[contains(@aria-label, 'unread') or contains(@aria-label, 'mensaje no leído') or contains(@aria-label, 'mensajes no leídos')]"

# ==============================
# Chat interface elements
# ==============================
# (Consolidado; antes duplicado)
# Current WA Web composer is a Lexical contenteditable (role=textbox,
# data-lexical-editor). The aria-placeholder attribute stopped matching on
# newer builds, so the stable contenteditable markers come first and the
# legacy aria-placeholder/title variants stay as back-compat fallbacks.
CHAT_INPUT_BOX = (
    "//div[@contenteditable='true' and @role='textbox']"
    " | //div[@data-lexical-editor='true']"
    " | //div[@aria-label='Type a message' or @aria-label='Escribe un mensaje']"
    " | //div[@aria-placeholder='Type a message' or @aria-placeholder='Escribe un mensaje' or @title='Type a message']"
)
# The composer of the chat that is actually open. Scoped to #main so it can
# never resolve to the search box or to another pane (verified live 2026-10-20).
ACTIVE_CHAT_COMPOSER = '#main footer div[contenteditable="true"][role="textbox"]'
# Fallback source for the open chat's title when the composer has no label.
ACTIVE_CHAT_HEADER_TITLE = '#main header span[dir="auto"]'
# The composer's aria-label names its chat: "Escribir un mensaje para +54 9 …",
# "Escribir un mensaje para el grupo Cliente". (kind, prefix) pairs, group
# first. Spanish and English verified live 2026-10-20 (the UI language follows
# the phone, not the browser). In any other language the library refuses to
# write rather than guess.
COMPOSER_LABEL_PREFIXES = (
    ("group", "Escribir un mensaje para el grupo "),
    ("chat", "Escribir un mensaje para "),
    ("group", "Type a message to group "),
    ("chat", "Type a message to "),
)
# Titles of the chats listed in the side pane.
CHAT_LIST_TITLES = (
    "//div[@id='pane-side']//div[@role='grid']//div[@role='row']"
    "//div[@data-testid='cell-frame-title']//span[@title]"
)
CHAT_DIV = "//div[@role='application']"
UNREAD_CHAT_DIV = "//div[@aria-label='Chat list' or @aria-label='Lista de chats' or @id='pane-side']"

# ==============================
# Message elements
# ==============================
CHAT_COMPONENT = ".//div[@role='row']"
CHAT_MESSAGE = ".//div[@data-pre-plain-text]"  # estable para burbujas
CHAT_MESSAGE_QUOTE = ".//div[@aria-label='Quoted message' or @aria-label='Mensaje citado']"
CHAT_MESSAGE_IMAGE = ".//div[@aria-label='Open picture' or @aria-label='Abrir imagen']"
CHAT_MESSAGE_IMAGE_ELEMENT = ".//img[starts-with(@src, 'blob:https://web.whatsapp.com')]"
MESSAGE_CONTAINER = 'div[data-testid^="conv-msg-"]'

# Descarga de archivos (audio como ejemplo + fallback genérico por data-icon)
ANY_DOWNLOAD_ICON = "//span[@data-icon='audio-download' or @data-icon='download' or @data-icon='download-outline']"

# Document file icons (WhatsApp Web 2026)
DOCUMENT_ICON = "span[data-icon='document-PDF-icon']"
DOCUMENT_ICON_GENERIC = "span[data-icon*='document']"
FILE_ICONS = f"span[data-icon='audio-download'], {DOCUMENT_ICON}, span[data-icon*='document']"

# ==============================
# Composer / acciones
# ==============================
ATTACH_BUTTON = "css=button[aria-label='Adjuntar'], button[aria-label='Attach'], span[data-icon='plus-rounded']"
SEND_BUTTON = "css=div[role='button'][aria-label*='Enviar']"
FILE_INPUT = "css=input[type='file']"

# ==============================
# Crear nuevo chat / grupo
# ==============================
NEW_CHAT_BUTTON = 'xpath=//span[@data-icon="new-chat-outline" or @data-icon="chat-new-outline"]'
NEW_GROUP_BUTTON = 'xpath=//div[@aria-label="New group" or @aria-label="Nuevo grupo" and @role="button"]'
INPUT_MEMBERS_GROUP = 'xpath=//input[@placeholder="Search name or number" or @placeholder="Buscar un nombre o número"]'
ENTER_GROUP_NAME = 'xpath=//div[@aria-label="Group subject (optional)" or @aria-label="Asunto del grupo (opcional)"]'
# Header button that opens the chat/contact info panel. WhatsApp Web renamed it
# to "Información del perfil" (verified live 2026-10-20). The titles are grouped
# so role=button applies to every alternative (it used to bind to the last one).
GROUP_INFO_BUTTON = (
    'xpath=//div[(@title="Información del perfil"'
    ' or @title="Detalles del perfil" or @title="Profile details") and @role="button"]'
)
ADD_MEMBERS_BUTTON = 'xpath=//span[@data-icon="person-add-filled-refreshed" or @data-icon="person-add"]'
CONFIRM_ADD_MEMBERS_BUTTON = 'xpath=//span[(@aria-label="Confirm" or @aria-label="Confirmar") and (@data-icon="checkmark-medium" or @data-icon="checkmark")]'
REMOVE_MEMBER_BUTTON = 'xpath=//span[@data-icon="clear-refreshed" or @data-icon="x-rounded"]'

# ==============================
# Message status (para control de flujo y race conditions)
# ==============================
# Usamos aria-label*= (contains) porque WA Web a veces incluye espacios
# leading/trailing en el aria-label que Meta puede cambiar en cualquier build
MSG_STATUS_PENDING = "css=span[aria-label*='Pendiente'], span[aria-label*='Pending']"
MSG_STATUS_SENT = "css=span[aria-label*='Enviado'], span[aria-label*='Sent']"
MSG_STATUS_DELIVERED = "css=span[aria-label*='Entregado'], span[aria-label*='Delivered']"
MSG_STATUS_READ = "css=span[aria-label*='Leído'], span[aria-label*='Read']"
MSG_STATUS_CONFIRMED = "css=span[aria-label*='Enviado'], span[aria-label*='Sent'], span[aria-label*='Entregado'], span[aria-label*='Delivered'], span[aria-label*='Leído'], span[aria-label*='Read']"
