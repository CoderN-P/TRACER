import os

from openai import AsyncOpenAI
from ..models import AICommand


client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

async def text_to_command(query: str, path="src/ai/PROMPT.txt") -> AICommand:
    with open(path, 'r') as prompt_file:
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

    response = await client.responses.parse(
        model="gpt-5-nano",
        input=messages,
        temperature=1,
        top_p=1,
        text_format=AICommand
    )
    
    
    
    return response.output_parsed





        
    
    
