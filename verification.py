from threading import Lock

class VerificationHandler:
    def __init__(self):
        self.pending_verifications = {}
        self.lock = Lock()
        self.telegram_bot = None

    def set_telegram_bot(self, bot):
        self.telegram_bot = bot

    def start_verification(self, username, chat_id):
        with self.lock:
            self.pending_verifications[chat_id] = {
                'username': username,
                'code': None
            }
        if self.telegram_bot:
            self.telegram_bot.send_message(
                chat_id,
                "🔐 Instagram requires verification!\n"
                "Please check your email/SMS and send the 6-digit code:"
            )

    def is_verification_pending(self, chat_id):
        with self.lock:
            return chat_id in self.pending_verifications

    def submit_code(self, chat_id, code):
        with self.lock:
            if chat_id in self.pending_verifications:
                self.pending_verifications[chat_id]['code'] = code
                return True
        return False
