from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
from ..models.CommandResponse import AICommand


client = OpenAI()

def text_to_command(query: str, path="src/ai/PROMPT.txt") -> AICommand:
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

    response = client.responses.parse(
        model="gpt-4.1-nano",
        input=messages,
        temperature=1,
        top_p=1,
        max_output_tokens=500,
        text_format=AICommand
    )
    
    return response.output_parsed




        
    
    
