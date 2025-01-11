import os
import dotenv

# Load environment variables
dotenv.load_dotenv('.env')
dotenv.load_dotenv('.env.development')

GOOGLE_AI_KEY = os.getenv('GOOGLE_AI_KEY')
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

tracked_channels = [
    # channel_id_1,
    # thread_id_2,
]

text_generation_config = {
    "temperature": 1.1,
    "top_p": 1,
    "top_k": 1,
    # "max_output_tokens": 512,
}
image_generation_config = {
    "temperature": 0.4,
    "top_p": 1,
    "top_k": 32,
    # "max_output_tokens": 512,
}
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
]

bot_template = [
    # {'role':'user','parts': ["Hi!"]},
    # {'role':'model','parts': ["Tehehe! Kirina's here! Anything fun?"]},
    # {'role':'user','parts': ["Please give short and concise answers!"]},
    # {'role':'model','parts': ["I will try my best!"]},
]

# Load system instructions from a text file with multiple instruction sets
def load_system_instructions(file_path='system_instruction.txt'):
    instructions = {}
    current_name = None
    current_instructions = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('[') and line.endswith(']'):
                    # If we encounter a new set, save the previous one
                    if current_name:
                        instructions[current_name] = current_instructions
                    current_name = line[1:-1]  # Extract the name inside []
                    current_instructions = []
                elif current_name:
                    current_instructions.append(line)
            # Don't forget to add the last set
            if current_name:
                instructions[current_name] = current_instructions
    except FileNotFoundError:
        print(f"Warning: {file_path} not found. Using default system instruction.")
        instructions['default'] = ["Nothing"]  # Default fallback instruction

    return instructions

system_instructions = load_system_instructions()
