# -*- coding: utf-8 -*-

"""
RAG V5.1
Ollama Client
"""

import requests

from .config import (
    OLLAMA_URL,
    OLLAMA_MODEL,
)


def chat(
    messages,
    temperature: float = 0.1,
):

    url = (
        f"{OLLAMA_URL}/api/chat"
    )

    payload = {

        "model":
            OLLAMA_MODEL,

        "messages":
            messages,

        "stream":
            False,

        "options": {

            "temperature":
                temperature,
        },
    }

    response = requests.post(

        url,

        json=payload,

        timeout=300,

    )

    response.raise_for_status()

    data = response.json()

    return data["message"]["content"]


def generate_answer(
    system_prompt: str,
    user_prompt: str,
):

    messages = [

        {
            "role":
                "system",

            "content":
                system_prompt,
        },

        {
            "role":
                "user",

            "content":
                user_prompt,
        },

    ]

    return chat(
        messages
    )