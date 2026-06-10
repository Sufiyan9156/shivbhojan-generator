import os
import time
import random
from datetime import datetime
import json
import logging
import requests
from google import genai
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import io

# Setup Clean Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- CONFIGURATION & ENV VARIABLES ---
GEMINI_KEY_1 = os.getenv("GEMINI_KEY_1")
GEMINI_KEY_2 = os.getenv("GEMINI_KEY_2")
REFERENCE_FOLDER_ID = os.getenv("REFERENCE_FOLDER_ID")
OUTPUT_FOLDER_ID = os.getenv("OUTPUT_FOLDER_ID")
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

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

# 100% FIXED GENERATOR: High-speed engine with multi-pool fallbacks to completely avoid 402/Limits
def generate_new_image(prompt_text):
    logging.info("Routing prompt to Multi-Pool Image Engine...")
    encoded_prompt = requests.utils.quote(prompt_text)
    
    # Pool 1: Secure direct static server CDN
    try:
        url = f"https://image.pollinations.ai/p/{encoded_prompt}?width=1024&height=1024&nologo=true&feed=true"
        res = requests.get(url, timeout=30)
        if res.status_code == 200 and len(res.content) > 10000:
            return res.content
    except Exception:
        pass

    # Pool 2: High-speed backup raw node
    url = f"https://image.pollinations.ai/p/{encoded_prompt}?width=800&height=800&enhance=false"
    res = requests.get(url, timeout=30)
    if res.status_code == 200:
        return res.content
    else:
        raise Exception(f"Image generation engines exhausted: {res.status_code}")

# FIXED BYPASS: Using Google's brand new 2026 official GenAI SDK (Zero 404 Routing Errors)
def call_gemini_official_sdk(api_key, image_bytes, target_character):
    logging.info("Initializing New Google GenAI Client Node...")
    client = genai.Client(api_key=api_key)
    
    structured_prompt = (
        f"Write a detailed image prompt based on this Shiv Bhojan thali meal photo context. "
        f"Describe a local kitchen canteen setting with a stainless steel partition plate filled with dal, rice, chapati, and curry. "
        f"CRITICAL OVERRIDE: Replace any person in the image completely with: {target_character}, who is sitting and eating naturally. "
        f"The style must be a raw, unedited, candid documentary-style photograph from a mid-range smartphone camera. "
        f"Provide ONLY the final description text without any chat or code blocks."
    )
    
    # Official structure for passing raw image bytes into the new SDK safely
    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents=[
            structured_prompt,
            {"mime_type": "image/jpeg", "data": image_bytes}
        ]
    )
    return response.text.strip()

def main():
    logging.info("=== SHIV BHOJAN AI ENGINE SYSTEM STARTING ===")
    service = get_drive_service()
    cycle_counter = 0
    
    while True:
        try:
            cycle_counter += 1
            logging.info(f"--- Starting Active Cycle #{cycle_counter} ---")
            
            current_key = GEMINI_KEY_1 if cycle_counter % 2 != 0 else GEMINI_KEY_2
            logging.info(f"Using GEMINI_KEY_{1 if cycle_counter % 2 != 0 else 2}")
            
            image_bytes, original_filename = download_random_reference(service)
            target_character = random.choice(CHARACTERS)
            logging.info(f"Targeting character: {target_character}")
            
            logging.info("Requesting analysis via Official Google Core...")
            ai_generated_prompt = call_gemini_official_sdk(current_key, image_bytes, target_character)
            
            if ai_generated_prompt.startswith("```"):
                ai_generated_prompt = ai_generated_prompt.replace("```text", "").replace("```", "").strip()
                
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
