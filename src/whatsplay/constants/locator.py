# ==============================
# State locators
# ==============================
AUTH = "//div[contains(., 'Steps to log in') or contains(., 'Pasos para iniciar sesión')]"
QR_CODE = "//canvas[@aria-label='Scan this QR code to link a device!' or @aria-label='Escaneá este código QR para vincular un dispositivo']"
INVALID_NUMBER_WARNING = "//div[contains(text(), 'invalid') or contains(text(), 'no es válido') or contains(text(), 'no está en WhatsApp')]"

# Banner inferior de cifrado (cambió el data-icon a 'lock-outline' en algunos builds)
LOADING = "//span[@data-icon='lock-outline' or @data-icon='lock-refreshed']/ancestor::div[contains(., 'End-to-end encrypted') or contains(., 'Cifrado de extremo a extremo')]"
LOADING_CHATS = "//div[normalize-space(text())='Loading your chats' or normalize-space(text())='Cargando tus chats']"
LOGGED_IN = "//span[@data-icon='wa-wordmark-refreshed' or @data-icon='whatsapp-logo']"

# ==============================
# Navigation buttons
# ==============================
CHATS_BUTTON = "//div[@aria-label='Chats' or @aria-label='Chat' or @aria-label='Chats de WhatsApp' or @aria-label='Conversaciones']"
STATUS_BUTTON = "//div[@aria-label='Status' or @aria-label='Estados']"
CHANNELS_BUTTON = "//div[@aria-label='Channels' or @aria-label='Canales']"
COMMUNITIES_BUTTON = "//div[@aria-label='Communities' or @aria-label='Comunidades']"

# ==============================
# Chat filter buttons (tabs)
# ==============================
ALL_CHATS_BUTTON = "//span[normalize-space(text())='All' or normalize-space(text())='Todos']"
UNREAD_CHATS_BUTTON = "//span[normalize-space(text())='Unread' or normalize-space(text())='No leídos']"
FAVOURITES_CHATS_BUTTON = "//span[normalize-space(text())='Favourites' or normalize-space(text())='Favoritos']"
GROUPS_CHATS_BUTTON = "//span[normalize-space(text())='Groups' or normalize-space(text())='Grupos']"

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
UNREAD_BADGE = ".//span[contains(@aria-label, 'unread') or contains(@aria-label, 'mensaje no leído') or contains(@aria-label, 'mensajes no leídos')]"
# Título del chat (estable)
SPAN_TITLE = ".//span[@title]"
# Celda con la hora (en tu build es esta clase semántica, pero la referenciamos por rol de gridcell si cambia)
ROW_TIME = ".//div[@role='gridcell' and @aria-colindex='2']/following-sibling::div[contains(@class,'_ak8i')][1] | .//div[contains(@class,'_ak8i')][1]"

# ==============================
# Search related locators
# ==============================
SEARCH_BUTTON = [
    # Nuevo botón de búsqueda (2024)
    "css=button[aria-label='Search'], button[aria-label='Buscar']",
    # Legacy selectores
    "//div[@aria-label='Search input textbox']",
    "//button[@aria-label='Search' or @aria-label='Buscar']",
    "//button[@title='Search' or @title='Buscar']",
    "//button[@aria-label='Search or start new chat' or @aria-label='Buscar o crear chat']",
    "//div[@role='button' and (@title='Search input textbox' or @aria-label='Search input textbox')]",
    "//span[@data-icon='search' or @data-testid='search']/parent::button",
]

SEARCH_TEXT_BOX = [
    "//div[@contenteditable='true' and @role='textbox']",
    "//div[contains(@class, 'lexical-rich-text-input')]//div[@contenteditable='true']",
    "//div[@role='textbox'][@contenteditable='true']",
    "//div[contains(@class, '_13NKt')]"
]

# Contenedor de resultados de búsqueda (en builds nuevos es un grid también)
SEARCH_RESULT = "//div[@aria-label='Search results.' or @aria-label='Resultados de búsqueda.'] | //div[@role='grid' and ancestor::div[@id='pane-side']]"
# Ítem de resultado (usa las mismas filas de la grilla)
SEARCH_ITEM = "//div[@role='row']"
# Partes del resultado: columna de título/preview
SEARCH_ITEM_COMPONENTS = ".//div[@role='gridcell' and @aria-colindex='2']/parent::div/div"
# Contador 'unread' dentro del ítem
SEARCH_ITEM_UNREAD_MESSAGES = ".//span[contains(@aria-label, 'unread') or contains(@aria-label, 'mensaje no leído') or contains(@aria-label, 'mensajes no leídos')]"

# ==============================
# Chat interface elements
# ==============================
# (Consolidado; antes duplicado)
CHAT_INPUT_BOX = "//div[@aria-placeholder='Type a message' or @aria-placeholder='Escribe un mensaje' or @title='Type a message']"
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

# Descarga de archivos (audio como ejemplo + fallback genérico por data-icon)
ANY_DOWNLOAD_ICON = "//span[@data-icon='audio-download' or @data-icon='download' or @data-icon='download-outline']"

# ==============================
# Composer / acciones
# ==============================
ATTACH_BUTTON = "css=span[data-icon='plus-rounded']"
SEND_BUTTON = "css=span[data-icon='wds-ic-send-filled'], css=span[data-icon='send']"
FILE_INPUT = "css=input[type='file']"

# ==============================
# Crear nuevo chat / grupo
# ==============================
NEW_CHAT_BUTTON = 'xpath=//span[@data-icon="new-chat-outline" or @data-icon="chat-new-outline"]'
NEW_GROUP_BUTTON = 'xpath=//div[@aria-label="New group" or @aria-label="Nuevo grupo" and @role="button"]'
INPUT_MEMBERS_GROUP = 'xpath=//input[@placeholder="Search name or number" or @placeholder="Buscar un nombre o número"]'
ENTER_GROUP_NAME = 'xpath=//div[@aria-label="Group subject (optional)" or @aria-label="Asunto del grupo (opcional)"]'
GROUP_INFO_BUTTON = 'xpath=//div[@title="Profile details" or @title="Detalles del perfil" and @role="button"]'
ADD_MEMBERS_BUTTON = 'xpath=//span[@data-icon="person-add-filled-refreshed" or @data-icon="person-add"]'
CONFIRM_ADD_MEMBERS_BUTTON = 'xpath=//span[(@aria-label="Confirm" or @aria-label="Confirmar") and (@data-icon="checkmark-medium" or @data-icon="checkmark")]'
REMOVE_MEMBER_BUTTON = 'xpath=//span[@data-icon="clear-refreshed" or @data-icon="x-rounded"]'
