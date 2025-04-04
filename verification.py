class VerificationHandler:
    def __init__(self):
        self.pending_verifications = {}

    def start_verification(self, username, chat_id):
        self.pending_verifications[chat_id] = username

    def is_verification_pending(self, chat_id):
        return chat_id in self.pending_verifications

    def submit_code(self, chat_id, code):
        username = self.pending_verifications.pop(chat_id, None)
        if username:
            # Handle the verification code submission
            pass
