verification_data = {}

def save_verification_code(code):
    verification_data['code'] = code

def is_verification_pending():
    return 'code' in verification_data

# ... (include your other verification functions)
