from datetime import datetime
from system_prompt import s_prompt


class Dialog:

    def __init__(self, subject, chat):
        self.subject = subject
        self.chat = chat
        self.last_msg = datetime.now()
        self.created_at = datetime.now()
        self.chat_color = '#333'

    def add_message(self, role, content):
        self.chat.append({"role": role, "content": content,
                         "created_at": datetime.now()})
        self.last_msg = datetime.now()

    def get_chat(self):
        return self.chat

    def to_dict(self):
        return {
            "subject": self.subject,
            "chat": self.chat,
            "last_msg": self.last_msg,
            "created_at": self.created_at,
            "chat_color": self.chat_color,
        }


def get_initialized_dialog(question):
    messages = [
        {"role": "system", "content": f"{s_prompt}", "created_at": datetime.now()},
        {"role": "assistant", "content": "How can I help you today?",
            "created_at": datetime.now()},
        {"role": "user", "content": f"{question}", "created_at": datetime.now()}
    ]
    dialog = Dialog(subject="Test dialog", chat=messages)
    return dialog
