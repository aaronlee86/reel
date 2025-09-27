import os

# Initialize the OpenAI client with API key from environment variable
print("loading OpenAI module...")
from openai import OpenAI
from pydantic import BaseModel
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY")
)
print("done")

def get_sentences_short(english_text, chinese_text):
    """Translate Chinese to colloquial American English"""
    class SentenceResult(BaseModel):
        english: list[str]
        chinese: list[str]

    try:
        response = client.responses.parse(
            model="gpt-5-mini-2025-08-07",
            input=[
                {"role": "system", "content": f"""User will give a English word and its Chinese translation
                                                Use the English word in given Chinese meaning to make 3 colloquial, and natural sentences which are no more than 8 words
                                                Also give me Traditional Chinese translation for each sentence, better use {chinese_text} in translation.
                                                return two arrays."""},
                {"role": "user", "content": f"english:{english_text}; chinese:{chinese_text}"}
            ],
            text_format=SentenceResult
        )

        print(f"total tokens {response.usage.total_tokens}")
        result = response.output_parsed
        return [[a, b] for a, b in zip(result.english, result.chinese)]

    except Exception as e:
        print(f"Error: {e}")
        return []

def get_sentences_medium(english_text, chinese_text):
    """Translate Chinese to colloquial American English"""
    class SentenceResult(BaseModel):
        english: list[str]
        chinese: list[str]

    try:
        response = client.responses.parse(
            model="gpt-5-mini-2025-08-07",
            input=[
                {"role": "system", "content": f"""User will give a English word and its Chinese translation
                                                Use the English word in given Chinese meaning to make 3 colloquial, and natural sentences which are between 6 to 12 words
                                                Also give me Traditional Chinese translation for each sentence, better use {chinese_text} in translation.
                                                return two arrays."""},
                {"role": "user", "content": f"english:{english_text}; chinese:{chinese_text}"}
            ],
            text_format=SentenceResult
        )

        print(f"total tokens {response.usage.total_tokens}")
        result = response.output_parsed
        return [[a, b] for a, b in zip(result.english, result.chinese)]

    except Exception as e:
        print(f"Error: {e}")
        return []

def get_sentences_long(english_text, chinese_text):
    """Translate Chinese to colloquial American English"""
    class SentenceResult(BaseModel):
        english: list[str]
        chinese: list[str]

    try:
        response = client.responses.parse(
            model="gpt-5-mini-2025-08-07",
            input=[
                {"role": "system", "content": f"""User will give a English word and its Chinese translation
                                                Use the English word in given Chinese meaning to make 3 colloquial, and natural sentences which are between 11 and 16 words
                                                Also give me Traditional Chinese translation for each sentence, better use {chinese_text} in translation.
                                                return two arrays."""},
                {"role": "user", "content": f"english:{english_text}; chinese:{chinese_text}"}
            ],
            text_format=SentenceResult
        )

        print(f"total tokens {response.usage.total_tokens}")
        result = response.output_parsed
        return [[a, b] for a, b in zip(result.english, result.chinese)]

    except Exception as e:
        print(f"Error: {e}")
        return []

def get_explain(english_text, chinese_text):
    """Translate Chinese to colloquial American English"""
    class Result(BaseModel):
        explain: list[str]

    try:
        response = client.responses.parse(
            model="gpt-5-mini-2025-08-07",
            input=[
                {"role": "system", "content": f"""given a English word and its Chinese translation
                                                explain the English word in Taiwanese traditional chinese in a colloquial, and natural way.
                                                Give me 2 explainations. Don't give me example sentence. just explain in 10 to 30 words.
                                                better include {chinese_text} in the answer.
                                                return a array"""},
                {"role": "user", "content": f"English:{english_text}; Chinese:{chinese_text}"}
            ],
            text_format=Result
        )

        print(f"total tokens {response.usage.total_tokens}")
        result = response.output_parsed
        return result.explain

    except Exception as e:
        print(f"Error: {e}")
        return []


def main():
    print("\n=== Translation Example ===")
    # Example Chinese text - replace with your text
    chinese_text = "佔位子"
    english_text = "hold seat"
    translation = get_explain(english_text, chinese_text)
    if translation:
        print(translation)

if __name__ == "__main__":
    main()

