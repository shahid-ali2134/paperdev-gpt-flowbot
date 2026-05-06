from __future__ import annotations


CHATGPT_MAIN_INPUT_SELECTORS = [
    'textarea[data-testid="prompt-textarea"]',
    'div[contenteditable="true"][data-testid="prompt-textarea"]',
    'textarea[placeholder*="Message"]',
    'div[contenteditable="true"]',
]

ASSISTANT_RESPONSE_SELECTORS = [
    '[data-message-author-role="assistant"]',
    'article:has-text("")',
]

STOP_BUTTON_NAMES = [
    "Stop streaming",
    "Stop generating",
    "Stop",
]

SEND_BUTTON_SELECTORS = [
    'button[data-testid="send-button"]',
    'button[aria-label*="Send"]',
]

NEW_CHAT_BUTTON_NAMES = [
    "New chat",
    "New Chat",
]

CHAT_TITLE_SELECTORS = [
    'button[aria-label*="Rename"]',
    '[data-testid="conversation-options-button"]',
]
