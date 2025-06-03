from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
from ..models import CommandResponse


client = OpenAI()

def text_to_command(query: str) -> CommandResponse:
    with open('PROMPT.txt', 'r') as prompt_file:
        system_prompt = prompt_file.read()
        
    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": query
        }
    ]
    
    response = client.beta.chat.completions.parse(
        model="gpt-4.1-nano",
        messages=messages,
        temperature=1,
        top_p=1,
        max_tokens=500,
        response_format=CommandResponse
    )
    
    return response.choices[0].message.parsed
        
    
    
