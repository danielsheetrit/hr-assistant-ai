from datetime import datetime


class Dialog:

    def __init__(self, title, chat, user_id):
        self.title = title
        self.chat = chat
        self.user_id = user_id
        self.last_msg = datetime.now()
        self.created_at = datetime.now()
        self.chat_color = '#333'

    def add_message(self, role, content):
        self.chat.append({"role": role, "content": content,
                         "created_at": datetime.now()})
        self.last_msg = datetime.now()

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "title": self.title,
            "chat": self.chat,
            "last_msg": self.last_msg,
            "created_at": self.created_at,
            "chat_color": self.chat_color,
        }
