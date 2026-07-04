"""
caption_generator.py — Strokes & Barrels Instagram caption generator.

Setup:
    pip install anthropic python-dotenv

    Create a .env file in this folder containing:
        ANTHROPIC_API_KEY=your_key_here
    Add .env to .gitignore so the key never gets committed.

Usage:
    python caption_generator.py --test    # smoke test
    python caption_generator.py           # interactive mode
    python caption_generator.py --batch   # captions for this week's 3 posts
"""

import os
import sys

import anthropic
from dotenv import load_dotenv

load_dotenv()  # loads ANTHROPIC_API_KEY from .env into the environment

STORE_URL = "https://strokesandbarrels.com"

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = (
    "You write Instagram captions for Strokes & Barrels, a modern golf "
    "brand for young diverse golfers. Voice: fun, confident, never stuffy. "
    f"Always end EVERY caption with: 'Shop the look — link in bio: {STORE_URL}'. "
    "Max 3 hashtags."
)


def generate_captions(post_description: str) -> str:
    try:
        response = client.messages.create(
            model="claude-haiku-4-5",  # fast and cheap — good for experimenting
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Write 3 different caption options for this post: {post_description}",
                }
            ],
        )
    except anthropic.AuthenticationError:
        sys.exit("Authentication failed — check ANTHROPIC_API_KEY in your .env file.")
    except anthropic.APIConnectionError:
        sys.exit("Couldn't reach the API — check your internet connection and try again.")

    return response.content[0].text


def smoke_test():
    print("Running smoke test...")
    result = generate_captions("mascot holding a golf club, green background")
    assert len(result) > 50, "Response too short — something is wrong"
    assert STORE_URL in result, f"Store URL missing from output. Got: {result[:200]}"
    print("Smoke test PASSED — API is connected and captions include the store link.")
    print()
    print(result)


def batch():
    posts = [
        "Post 1: describe what you posted",   # <- note the comma the assignment was missing!
        "Post 2: describe what you posted",
        "Post 3: describe what you posted",
    ]
    for post in posts:
        print(generate_captions(post))
        print("---")


if __name__ == "__main__":
    if "--test" in sys.argv:
        smoke_test()
    elif "--batch" in sys.argv:
        batch()
    else:
        description = input("Describe the post: ")
        print(generate_captions(description))
