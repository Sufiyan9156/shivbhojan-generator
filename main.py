import os
import time
import random
from datetime import datetime
import json
import logging
import requests
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import io

# Setup Clean Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- CONFIGURATION & ENV VARIABLES ---
REFERENCE_FOLDER_ID = os.getenv("REFERENCE_FOLDER_ID")
OUTPUT_FOLDER_ID = os.getenv("OUTPUT_FOLDER_ID")
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
HF_TOKEN = os.getenv("HF_TOKEN")

CHARACTERS = [
    "an elderly Maharashtrian farmer with a deeply wrinkled weathered face, silver hair, and a white traditional Gandhi topi",
    "a young Maharashtrian college student in a simple checked shirt, looking cheerful",
    "a female local construction worker with a traditional Maharashtrian nose ring (nath) and a simple colorful saree",
    "a middle-aged daily wage laborer in a faded, dusty t-shirt, looking tired but content",
    "a young Maharashtrian teenager smiling and looking down at the food plate",
    "an old Maharashtrian grandmother (Aaji) with gray hair tied in a bun, wearing a traditional Navari saree",
    "a local auto-rickshaw driver in his official faded khaki uniform shirt",
    "a young female garment factory worker with a bindi on her forehead and a simple salwar suit",
    "a middle-aged local street vendor or small shopkeeper in a plain white kurta"
]

def get_drive_service():
    try:
        creds_dict = json.loads(SERVICE_ACCOUNT_JSON)
        creds = Credentials.from_service_account_info(
            creds_dict, scopes=["https://www.googleapis.com/auth/drive"]
        )
        return build("drive", "v3", credentials=creds, cache_discovery=False)
    except Exception as e:
        logging.error(f"CRITICAL: Google Drive Auth Failed: {str(e)}")
        raise e

def get_or_create_today_folder(service):
    today_str = datetime.now().strftime("%d %B %Y")
    query = f"name = '{today_str}' and '{OUTPUT_FOLDER_ID}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = service.files().list(q=query, fields="files(id)").execute()
    items = results.get('files', [])
    
    if items:
        return items[0]['id']
    else:
        logging.info(f"Creating folder: {today_str}")
        file_metadata = {
            'name': today_str,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [OUTPUT_FOLDER_ID]
        }
        folder = service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')

def download_random_reference(service):
    query = f"'{REFERENCE_FOLDER_ID}' in parents and (mimeType = 'image/jpeg' or mimeType = 'image/png') and trashed = false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])
    
    if not items:
        raise Exception("REFERENCES folder is empty!")
        
    random_file = random.choice(items)
    logging.info(f"Picked reference template file: {random_file['name']}")
    
    request = service.files().get_media(fileId=random_file['id'])
    file_stream = io.BytesIO()
    downloader = MediaIoBaseDownload(file_stream, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    
    file_stream.seek(0)
    return file_stream.read(), random_file['name']

# BULLETPROOF REPLACEMENT: Direct Hugging Face Professional Inference API 
def generate_new_image(prompt_text):
    logging.info("Routing prompt to Professional Hugging Face Stable Diffusion Engine...")
    
    # Using high-speed stable diffusion pipeline via Hugging Face Infrastructure
    url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2-1"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {"inputs": prompt_text, "options": {"wait_for_model": True}}
    
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"HuggingFace API Failed with status code {response.status_code}: {response.text}")

def call_vision_api(image_bytes, target_character):
    # Context prompt builder
    return f"A raw smartphone documentary candid photo of {target_character} sitting in a local crowded Maharashtrian kitchen canteen, happily eating a simple traditional Shiv Bhojan meal consisting of dal, rice, hot chapati, and vegetable curry from a stainless steel partition thali plate, overhead indoor lighting, natural textures, 4k resolution."

def main():
    logging.info("=== SHIV BHOJAN AI ENGINE SYSTEM STARTING ===")
    service = get_drive_service()
    cycle_counter = 0
    
    while True:
        try:
            cycle_counter += 1
            logging.info(f"--- Starting Active Cycle #{cycle_counter} ---")
            
            image_bytes, original_filename = download_random_reference(service)
            target_character = random.choice(CHARACTERS)
            logging.info(f"Targeting character: {target_character}")
            
            ai_generated_prompt = call_vision_api(image_bytes, target_character)
            logging.info(f"Compiled Prompt: '{ai_generated_prompt[:120]}...'")
            
            new_image_data = generate_new_image(ai_generated_prompt)
            active_folder_id = get_or_create_today_folder(service)
            
            current_timestamp = datetime.now().strftime("%H-%M-%S")
            final_filename = f"photo_{current_timestamp}.jpg"
            
            meta_data = {'name': final_filename, 'parents': [active_folder_id]}
            media_content = MediaFileUpload(io.BytesIO(new_image_data), mimetype='image/jpeg', resumable=True)
            
            uploaded_node = service.files().create(body=meta_data, media_body=media_content, fields='id').execute()
            logging.info(f"SUCCESS: '{final_filename}' uploaded to Drive! ID: {uploaded_node.get('id')}")
            
        except Exception as error:
            logging.error(f"FAIL: Error caught in loop: {str(error)}")
            
        logging.info("Waiting for 150 seconds...")
        time.sleep(150)

if __name__ == "__main__":
    main()
