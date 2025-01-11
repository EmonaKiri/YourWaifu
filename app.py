import gradio as gr
import subprocess
import os

# Global variable to keep track of the bot process
bot_process = None

# Function to start bot.py as a background process
def start_bot():
    global bot_process
    # Start bot.py in a new subprocess
    bot_process = subprocess.Popen(['python3', 'bot.py'])
    return "Bot started!", "YourWaifu is online"  # Update the message

# Function to stop bot.py
def stop_bot():
    global bot_process
    if bot_process is not None:
        # Terminate the process
        bot_process.terminate()
        bot_process.wait()  # Wait for the process to finish
        bot_process = None
        return "Bot stopped!", "YourWaifu is offline"  # Update the message
    else:
        return "Bot is not running.", "YourWaifu is offline"  # Default offline message

# Function to display interface message
def display_interface():
    return "YourWaifu is offline"  # Initial message

# Function to list files in the root directory and confirm the chatdata file is there
def list_files():
    files = os.listdir('.')
    log = f"Files in root directory: {files}"
    print(log)
    return log

# Function to find and download the chatdata file
def download_chatdata():
    chatdata_path = "chatdata.json"  # Update to point to the root directory
    if os.path.exists(chatdata_path):
        return chatdata_path
    else:
        return None  # Return None if the file doesn't exist

# Function to refresh the download file link
def refresh_download():
    return download_chatdata()  # Refresh the file path for the download link

# Create the Gradio interface
with gr.Blocks() as demo:
    with gr.Row():
        with gr.Column(scale=1):  # Left column for image
            gr.Image("waifu.png", label="YourWaifu's Here", elem_id="image-box", show_label=False)
        with gr.Column(scale=2):  # Right column for controls and logs
            status_textbox = gr.Textbox(display_interface(), label="Status", interactive=False)  # Initial status
            
            # Start and Stop buttons for bot control
            start_button = gr.Button("Start Bot")
            stop_button = gr.Button("Stop Bot")
            start_button.click(start_bot, None, [status_textbox])  # Update status on click
            stop_button.click(stop_bot, None, [status_textbox])  # Update status on click

            log_box = gr.Textbox(list_files(), label="Log", interactive=False, lines=4)  # Log display

            # Button to refresh logs and download chat data
            with gr.Row():
                refresh_log_button = gr.Button("Refresh Log")
                refresh_log_button.click(list_files, None, log_box)  # Refresh log on click
                
                download_button = gr.File(label="Download Chat Data", value=download_chatdata)  # Initial download link
                refresh_download_button = gr.Button("Refresh Download Link")
                refresh_download_button.click(refresh_download, None, download_button)  # Refresh the download link

# Launch the app
demo.launch()
