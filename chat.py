import openai
from system_prompt import subject_prompt


def get_chat(messages: list, answer_length: int):
    response: dict = openai.ChatCompletion.create(
        messages=messages,
        model="gpt-3.5-turbo",
        max_tokens=answer_length,
        n=1,
        stop=None,
        temperature=1,
    )
    return response.choices[0].message.content.strip()


def get_dialog_subject(question):
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=f"{subject_prompt} {question}",
        temperature=0.6,
        max_tokens=20
    )
    return response.choices[0].text.strip(' "').strip()
