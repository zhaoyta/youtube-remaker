"""Gemini 网页选择器。Google 改版时只改这里，按优先级排列。"""

INPUT = [
    "div.ql-editor[contenteditable='true']",
    "[aria-label='Enter a prompt for Gemini']",
    "[aria-label='向 Gemini 提供提示']",
    "rich-textarea .ql-editor",
    "div[contenteditable='true']",
    "div[role='textbox']",
    "textarea",
]

SEND = [
    "button[aria-label='Send message']",
    "button[aria-label='发送']",
    "button[aria-label='傳送']",
    "button.send-button",
    "button[aria-label*='Send']",
    "button[aria-label*='发送']",
]

STOP = [
    "button[aria-label='Stop response']",
    "button[aria-label='停止回应']",
    "button[aria-label='停止回應']",
    "button[aria-label*='Stop']",
    "button[aria-label*='停止']",
]

NEW_CHAT = [
    "a[aria-label='New chat']",
    "button[aria-label='New chat']",
    "a[aria-label='新对话']",
    "button[aria-label='新对话']",
    "a[aria-label='新對話']",
    "[data-test-id='new-chat-button']",
    "a[href*='/app/']",
]

MIC = [
    "button[data-node-type='speech_dictation_mic_button']",
    "button[aria-label='Microphone']",
    "button[aria-label='麦克风']",
    "button[aria-label='麥克風']",
]

RESPONSE = [
    "model-response .markdown",
    "MESSAGE-CONTENT .markdown",
    ".markdown.markdown-main-panel",
    "model-response",
    "[class*='response-content']",
]
