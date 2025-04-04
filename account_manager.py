class AccountManager:
    def __init__(self):
        self.accounts = {}

    def add_account(self, username, password, chat_id):
        self.accounts[username] = {'password': password, 'chat_id': chat_id}

    def get_account(self, username):
        return self.accounts.get(username)
