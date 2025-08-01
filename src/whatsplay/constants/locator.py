# State locators
AUTH = "//div[contains(text(), 'Steps to log in')]"
QR_CODE = "//canvas[@aria-label='Scan this QR code to link a device!']"
LOADING = "//div[//span[@data-icon='lock-refreshed'] and contains(text(), 'End-to-end encrypted')]"
LOADING_CHATS = "//div[text()='Loading your chats']"
LOGGED_IN = "//span[@data-icon='wa-wordmark-refreshed']"

# Navigation buttons
CHATS_BUTTON = "//div[@aria-label='Chats']"
STATUS_BUTTON = "//div[@aria-label='Status']"
CHANNELS_BUTTON = "//div[@aria-label='Channels']"
COMMUNITIES_BUTTON = "//div[@aria-label='Communities']"

# Chat filter buttons
ALL_CHATS_BUTTON = "//div[text()='All']"
UNREAD_CHATS_BUTTON = "//div[text()='Unread']"
FAVOURITES_CHATS_BUTTON = "//div[text()='Favourites']"
GROUPS_CHATS_BUTTON = "//div[text()='Groups']"

# Search related locators
SEARCH_BUTTON = [
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
CHAT_INPUT_BOX = "//div[@aria-placeholder='Type a message']"
CHAT_DIV = "//div[@role='application']"
UNREAD_CHAT_DIV = "//div[@aria-label='Chat list']"

# Search results
SEARCH_RESULT = "//div[@aria-label='Search results.']"
SEARCH_ITEM = "//div[@role='listitem']"
SEARCH_ITEM_COMPONENTS = (
    ".//div[@role='gridcell' and @aria-colindex='2']/parent::div/div"
)
SEARCH_ITEM_UNREAD_MESSAGES = ".//span[contains(@aria-label, 'unread message')]"
SPAN_TITLE = ".//span[@title]"

# Message elements
CHAT_COMPONENT = ".//div[@role='row']"
CHAT_MESSAGE = ".//div[@data-pre-plain-text"
CHAT_MESSAGE_QUOTE = ".//div[@aria-label='Quoted message']"
CHAT_MESSAGE_IMAGE = ".//div[@aria-label='Open picture']"
CHAT_MESSAGE_IMAGE_ELEMENT = (
    ".//img[starts-with(@src, 'blob:https://web.whatsapp.com')]"
)
# Locator para identificar cualquier botón de descarga de archivos
ANY_DOWNLOAD_ICON = "//span[@data-icon='audio-download']"
ATTACH_BUTTON = "span[data-icon='plus-rounded']"
SEND_BUTTON = "span[data-icon='wds-ic-send-filled']"
FILE_INPUT = "input[type='file']"
