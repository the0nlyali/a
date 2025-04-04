class VerificationHandler:
    def __init__(self):
        self.pending_verifications = {}
        self.telegram_bot = None

    def set_telegram_bot(self, bot):
        self.telegram_bot = bot

    def start_verification(self, username, chat_id):
        self.pending_verifications[chat_id] = username

    def is_verification_pending(self, chat_id):
        return chat_id in self.pending_verifications

    def submit_code(self, chat_id, code):
        username = self.pending_verifications.pop(chat_id, None)
        if username:
            # Handle the verification code submission
            self.telegram_bot.reply_to(chat_id, f"Verification code {code} submitted for {username}.")
