import discord
import google.generativeai as genai
from discord.ext import commands
import aiohttp 
import asyncio
import traceback
from config import *
from discord import app_commands
from typing import Optional, Dict
import json  # For saving chat data in JSON format
import os
import sys
import io

# Force UTF-8 encoding for standard output and standard error
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
#---------------------------------------------AI Configuration-------------------------------------------------
genai.configure(api_key=GOOGLE_AI_KEY)
current_instruction = system_instructions.get("misonomika", "Default system instruction.")
model = genai.GenerativeModel(model_name="gemini-1.5-flash-002", generation_config=text_generation_config, safety_settings=safety_settings, system_instruction=current_instruction)


message_history: Dict[int, genai.ChatSession] = {}
tracked_threads = []

# Check current working directory
print(f"Current working directory: {os.getcwd()}")

# Load existing chat data
def load_chat_data():
    chatdata_path = 'chatdata.json'
    if not os.path.exists(chatdata_path):
        # Create an empty file if it doesn't exist
        with open(chatdata_path, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=4)
        print(f"{chatdata_path} created.")
        return {}

    try:
        with open(chatdata_path, 'r', encoding='utf-8') as f:
            # Check if the file is empty
            if os.stat(chatdata_path).st_size == 0:
                print(f"{chatdata_path} is empty. Returning an empty history.")
                return {}
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Error reading {chatdata_path}: invalid JSON format.")
        return {}
message_history = load_chat_data()

#---------------------------------------------Discord Code-------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents, help_command=None, activity=discord.Game('with your heart'))

# Dictionary to track auto-reply and vowel replacement status
auto_reply_status = {}
vowel_replace_status = {}
# Dictionary to store instruction settings by channel
channel_instructions = {}

# Function to replace the first vowel in each word
def replace_vowels(text):
    vowels = 'aeiouAEIOU'
    def replace_first_vowel(word):
        if len(word) == 1 or word.startswith('@'):  # Leave single-character words and mentions alone
            return word
        for i, char in enumerate(word):
            if char in vowels:
                return word[:i] + "'" + word[i+1:]
        return word  # Return the word unchanged if no vowels are found
    return ' '.join([replace_first_vowel(word) for word in text.split()])
    
#------------------- AUTOCOMPLETE AND /set_instruction ADDITION START -------------------
# Autocomplete function to provide a list of instruction names
async def instruction_autocomplete(interaction: discord.Interaction, current: str):
    # Return matching instruction names based on user input
    return [
        app_commands.Choice(name=name, value=name)
        for name in system_instructions.keys()
        if current.lower() in name.lower()
    ]

@bot.tree.command(name='set_instruction', description='Switch between different system instructions for this channel.')
@app_commands.autocomplete(instruction_name=instruction_autocomplete)
async def set_instruction(interaction: discord.Interaction, instruction_name: str):
    global model  # Ensure model is accessible

    channel_id = interaction.channel.id  # Identify the specific channel

    if instruction_name in system_instructions:
        # Update the current instruction for the specific channel
        current_instruction = system_instructions[instruction_name]

        # Re-initialize the model with the updated instruction
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash-002",
            generation_config=text_generation_config,
            safety_settings=safety_settings,
            system_instruction=current_instruction
        )

        # Reset the message history for this channel with the new instruction
        message_history[channel_id] = model.start_chat(history=bot_template)

        await interaction.response.send_message(f"System instruction set to '{instruction_name}' in this channel!")
        print(f"System instruction switched to '{instruction_name}' in channel {channel_id}: {current_instruction}")
    else:
        await interaction.response.send_message(f"Instruction set '{instruction_name}' not found.")
        print(f"Attempted to switch to non-existent instruction set '{instruction_name}'")

#------------------- AUTOCOMPLETE AND /set_instruction ADDITION END -------------------


# Slash Command to toggle auto-reply
@bot.tree.command(name='toggle_reply', description='Toggle auto-reply on/off in this channel.')
async def toggle_reply(interaction: discord.Interaction):
    channel_id = interaction.channel.id
    global auto_reply_status
    auto_reply_status[channel_id] = not auto_reply_status.get(channel_id, False)
    status = "enabled" if auto_reply_status[channel_id] else "disabled"
    await interaction.response.send_message(f"Auto-reply has been {status} in this channel!")

# Slash Command to toggle vowel replacement
@bot.tree.command(name='toggle_vowel_replace', description='Toggle vowel replacement on/off in this channel.')
async def toggle_vowel_replace(interaction: discord.Interaction):
    global vowel_replace_status  # Declare as global to ensure modifications
    channel_id = interaction.channel.id
    
    # Toggle the current state of vowel replacement in the dictionary
    vowel_replace_status[channel_id] = not vowel_replace_status.get(channel_id, False)
    
    # Send a response message showing the current status
    status = "enabled" if vowel_replace_status[channel_id] else "disabled"
    await interaction.response.send_message(f"Vowel replacement has been {status} in this channel!")
    
    # Debugging log
    print(f"Vowel replacement for channel {channel_id} is now {status}.")
            
# On Message Function
@bot.event
async def on_message(message: discord.Message):
    # Debugging the toggle status
    channel_id = message.channel.id
    #print(f"Auto-reply is {'enabled' if auto_reply_status.get(channel_id, False) else 'disabled'} in channel {channel_id}.")
    #print(f"Vowel replacement is {'enabled' if vowel_replace_status.get(channel_id, False) else 'disabled'} in channel {channel_id}.")
    
    # Ignore messages sent by the bot
    if message.author == bot.user:
        return

    # Ignore messages sent to everyone
    if message.mention_everyone:
        return

    # Get the auto-reply status for the channel
    is_auto_reply_enabled = auto_reply_status.get(channel_id, False)  # Default to False if not set
    is_vowel_replace_enabled = vowel_replace_status.get(channel_id, False)

    # Set conditions for whether the bot should reply
    should_reply = False

    # Auto-reply is enabled, so we need to check conditions
    if is_auto_reply_enabled:
        # 1. Reply to messages from all other bots
        if message.author.bot:
            should_reply = True
        
        # 2. Reply to messages from users that mention the bot or are direct replies to the bot
        elif bot.user.mentioned_in(message) or (message.reference and message.reference.resolved and message.reference.resolved.author == bot.user):
            should_reply = True

        # 3. Reply to plain messages from users (not mentioning anyone or replying)
        elif not message.reference and not message.mentions:  # No reference and no mentions
            should_reply = True

    else:
        # Auto-reply is disabled, so only reply when directly mentioned or the message replies to the bot
        if bot.user.mentioned_in(message) or (message.reference and message.reference.resolved and message.reference.resolved.author == bot.user):
            should_reply = True

    # If the bot should not reply, return without doing anything
    if not should_reply:
        return

    # Start typing to seem like something is happening
    try:
        async with message.channel.typing():
            print("FROM:" + str(message.author.name) + ": " + message.content)

            # Prepare the user's prompt
            user_prompt = message.clean_content
            
            # If vowel replacement is enabled, apply it to the user's prompt
            if is_vowel_replace_enabled:
                user_prompt = replace_vowels(user_prompt)
                # Debug modified user prompt after vowel replacement
                print(f"Modified user prompt after vowel replacement: '{user_prompt}'")

            # Prepare the base query for the AI model
            query = f"@{message.author.name} said \"{user_prompt}\""

            # Check if the message has attachments
            images = []
            if message.attachments:
                if not message.content:
                    query = f"@{message.author.name} sent an image"
                else:
                    query = f"@{message.author.name} said \"{user_prompt}\" while sending an image"  # Use user_prompt here

                for attachment in message.attachments:
                    print("Attachment")
                    if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                        async with aiohttp.ClientSession() as session:
                            async with session.get(attachment.url) as resp:
                                if resp.status != 200:
                                    await message.channel.send('Sorry I could not download that picture >_<')
                                    return
                                image_data = await resp.read()
                                images.append({"mime_type": "image/jpeg", "data": image_data})

            # Check if message is quoting someone
            if message.reference is not None:
                reply_message = await message.channel.fetch_message(message.reference.message_id)
                if reply_message.author.id != bot.user.id:
                    query = f"{query} while quoting @{reply_message.author.name} \"{reply_message.clean_content}\""

            # Log the final query that will be sent to the AI model
            print(f"Final query to AI model: '{query}'")

            response_text = await generate_response(message.channel.id, images, query)

        # Wait for 30 seconds before sending the reply
        if is_auto_reply_enabled:
            print("Waiting for 30 seconds before replying...")
            await asyncio.sleep(30)  # This makes the bot pause for 30 seconds before replying

        # Split the Message so discord does not get upset
        await split_and_send_messages(message, response_text, 1700)

        # Save chat history to a JSON file
        save_chat_data(message.channel.id, message_history[message.channel.id].history)
        
    except Exception as e:
        traceback.print_exc()
        await message.reply('There is something wrong with me! Please check my logs >_<')


# Function to save chat data to a JSON file
def save_chat_data(channel_id, history):
    chatdata_path = 'chatdata.json'  # Save in the main directory as JSON
    try:
        print(f"Saving history for channel {channel_id}: {history}, type: {type(history)}")

        # Load existing data
        if os.path.exists(chatdata_path):
            with open(chatdata_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        else:
            existing_data = {}

        # Prepare the new history entry
        if channel_id not in existing_data:
            existing_data[channel_id] = []

        # Convert history to a serializable format
        serializable_history = []
        for part in history:
            print(f"Part: {part}, Type: {type(part)}")  # Debugging line to inspect each part
            if isinstance(part, dict):
                serializable_history.append({
                    'text': part.get('text', str(part)),  # Safely access text
                    'role': part.get('role', 'unknown')  # Default to 'unknown' if role is not available
                })
            elif hasattr(part, 'text') and hasattr(part, 'role'):
                serializable_history.append({
                    'text': part.text,  # Directly use the text
                    'role': part.role  # Directly use the role
                })
            else:
                serializable_history.append(str(part))  # If part is not a dict, just convert to string

        # Append the new history to the existing data
        existing_data[channel_id].extend(serializable_history)

        # Save the updated history to the JSON file
        with open(chatdata_path, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=4)  # Ensure special characters are preserved
        print(f"Chat data successfully saved in {chatdata_path}.")
    except Exception as e:
        print(f"Error saving chat data: {e}")
#---------------------------------------------AI Generation History-------------------------------------------------		   

# Modified generate_response function to use channel-specific instructions
async def generate_response(channel_id, images, text):
    try:
        prompt_parts = images
        prompt_parts.append(text)

        # Start a new chat session if none exists for this channel, using the specified instruction
        if channel_id not in message_history:
            instruction = channel_instructions.get(channel_id, current_instruction)
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash-002", 
                generation_config=text_generation_config, 
                safety_settings=safety_settings, 
                system_instruction=instruction
            )
            message_history[channel_id] = model.start_chat(history=bot_template)
        
        response = message_history[channel_id].send_message(prompt_parts)
        return response.text
    except Exception as e:
        with open('errors.log', 'a+', encoding='utf-8') as errorlog:
            errorlog.write('\n##########################\n')
            errorlog.write('Message: ' + text)
            errorlog.write('\n-------------------\n')
            errorlog.write('Traceback:\n' + traceback.format_exc())


#---------------------------------------------Sending Messages-------------------------------------------------
async def split_and_send_messages(message_system: discord.Message, text, max_length):
    # Split the string into parts
    messages = []
    for i in range(0, len(text), max_length):
        sub_message = text[i:i + max_length]
        messages.append(sub_message)

    # Send each part as a separate message
    for string in messages:
        message_system = await message_system.reply(string)	

#---------------------------------------------Run Bot-------------------------------------------------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print("----------------------------------------")
    print(f'Gemini Bot Logged in as {bot.user}')
    print("----------------------------------------")

bot.run(DISCORD_BOT_TOKEN)
