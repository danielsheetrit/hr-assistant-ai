def chat_validations(question, answer_length):
    res = None

    if not question:
        res = 'No Question provided'

    if not answer_length:
        res = 'No Answer length provided'

    return res