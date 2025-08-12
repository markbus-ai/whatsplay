# State locators
AUTH = "//div[contains(text(), 'Steps to log in') or contains(text(), 'Pasos para iniciar sesión')]"
QR_CODE = "//canvas[@aria-label='Scan this QR code to link a device!']"
LOADING = "//div[//span[@data-icon='lock-refreshed'] and contains(text(), 'End-to-end encrypted') or contains(text(), 'Cifrado de extremo a extremo')]"
LOADING_CHATS = "//div[text()='Loading your chats' or text()='Cargando tus chats']"
LOGGED_IN = "//span[@data-icon='wa-wordmark-refreshed']"

# Navigation buttons
CHATS_BUTTON = "//div[@aria-label='Chats']"
STATUS_BUTTON = "//div[@aria-label='Status']"
CHANNELS_BUTTON = "//div[@aria-label='Channels']"
COMMUNITIES_BUTTON = "//div[@aria-label='Communities']"

# Chat filter buttons
ALL_CHATS_BUTTON = "//div[text()='All' or text()='Todos']"
UNREAD_CHATS_BUTTON = "//div[text()='Unread' or text()='No leídos']"
FAVOURITES_CHATS_BUTTON = "//div[text()='Favourites' or text()='Favoritos']"
GROUPS_CHATS_BUTTON = "//div[text()='Groups' or text()='Grupos']"

# Search related locators
SEARCH_BUTTON = [
    "//div[@aria-label='Search input textbox']",
    "//button[@aria-label='Search']",
    "//button[@title='Search']",
    "//button[@aria-label='Search or start new chat']",
    "//div[@role='button' and @title='Search input textbox']",
    "//span[@data-icon='search']/parent::button",
    "//span[@data-testid='search']/parent::button",
]

SEARCH_TEXT_BOX = [
    "//div[@contenteditable='true']",
    "//div[contains(@class, 'lexical-rich-text-input')]//div[@contenteditable='true']",
    "//div[@role='textbox'][@contenteditable='true']",
    "//div[contains(@class, '_13NKt')]",
]

SEARCH_RESULT = "//div[@aria-label='Search results.']"
SEARCH_ITEM = "//div[@role='listitem']"
CHAT_INPUT_BOX = "//div[@title='Type a message'][@role='textbox']"
CANCEL_SEARCH = "//button[@aria-label='Cancel search']"

# Chat interface elements
CHAT_INPUT_BOX = "//div[@aria-placeholder='Type a message' or @aria-placeholder='Escribe un mensaje']"
CHAT_DIV = "//div[@role='application']"
UNREAD_CHAT_DIV = "//div[@aria-label='Chat list' or @aria-label='Lista de chats']"

# Search results
SEARCH_ITEM = "//div[@role='listitem']"
SEARCH_ITEM_COMPONENTS = (
    ".//div[@role='gridcell' and @aria-colindex='2']/parent::div/div"
)
SEARCH_ITEM_UNREAD_MESSAGES = ".//span[contains(@aria-label, 'unread message') or contains(@aria-label, 'mensaje no leído')]"
SPAN_TITLE = ".//span[@title]"

# Message elements
CHAT_COMPONENT = ".//div[@role='row']"
CHAT_MESSAGE = ".//div[@data-pre-plain-text]"
CHAT_MESSAGE_QUOTE = ".//div[@aria-label='Quoted message' or @aria-label='Mensaje citado']"
CHAT_MESSAGE_IMAGE = ".//div[@aria-label='Open picture' or @aria-label='Abrir imagen']"
CHAT_MESSAGE_IMAGE_ELEMENT = (
    ".//img[starts-with(@src, 'blob:https://web.whatsapp.com')]"
)
# Locator para identificar cualquier botón de descarga de archivos
ANY_DOWNLOAD_ICON = "//span[@data-icon='audio-download']"
ATTACH_BUTTON = "span[data-icon='plus-rounded']"
SEND_BUTTON = "span[data-icon='wds-ic-send-filled']"
FILE_INPUT = "input[type='file']"
NEW_CHAT_BUTTON = 'xpath=//span[@data-icon="new-chat-outline"]'
NEW_GROUP_BUTTON = 'xpath=//div[@aria-label="New group" or @aria-label="Nuevo grupo" and @role="button"]'
INPUT_MEMBERS_GROUP = 'xpath=//input[@placeholder="Search name or number" or @placeholder="Buscar un nombre o número"]'
ENTER_GROUP_NAME = 'xpath=//div[@aria-label="Group subject (optional)" or @aria-label="Asunto del grupo (opcional)"]'
GROUP_INFO_BUTTON = 'xpath=//div[@title="Profile details" or @title="Detalles del perfil" and @role="button"]'
ADD_MEMBERS_BUTTON = 'xpath=//span[@data-icon="person-add-filled-refreshed"]'
CONFIRM_ADD_MEMBERS_BUTTON = 'xpath=//span[@aria-label="Confirm" or @aria-label="Confirmar" and @data-icon="checkmark-medium"]'
REMOVE_MEMBER_BUTTON = 'xpath=//span[@data-icon="clear-refreshed"]'