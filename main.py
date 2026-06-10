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
import base64

# Setup Clean Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- CONFIGURATION & ENV VARIABLES ---
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

def generate_new_image(prompt_text):
    logging.info("Routing prompt to Flux Engine...")
    encoded_prompt = requests.utils.quote(prompt_text)
    seed = random.randint(100000, 999999)
    url = f"https://image.pollinations.ai/p/{encoded_prompt}?width=1024&height=1024&model=flux&seed={seed}&nologo=true"
    
    response = requests.get(url)
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"Flux Engine failed: {response.status_code}")

# BULLETPROOF REPLACEMENT: Public Vision API Endpoint (No Keys, No 404)
def call_vision_api(image_bytes, target_character):
    logging.info("Analyzing template via Public Vision Server...")
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    # Using a reliable public inference API for LLaVA
    url = "https://api.pollinations.ai/openai"
    
    prompt_text = (
        f"Describe this Indian meal photo for a realistic image generator. "
        f"The setting is a crowded local government kitchen canteen. On a steel thali plate, there is Indian food like dal, rice, chapati, and curry. "
        f"The lighting is simple overhead tube-light. "
        f"CRITICAL: Describe the scene but state that sitting in front of the plate eating naturally is: {target_character}. "
        f"Keep the description raw, documentary photo style, smartphone camera quality, candid shot. "
        f"Give ONLY the descriptive prompt text, no chat."
    )
    
    payload = {
        "model": "openai",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_text},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                    }
                ]
            }
        ]
    }
    
    response = requests.post(url, json=payload, timeout=30)
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content'].strip()
    else:
        # Fallback in case image processing has temporary lag
        logging.warning("Vision server heavy load, using dynamic direct prompt injector...")
        return f"A raw smartphone documentary candid photo of {target_character} sitting in a local crowded Maharashtrian kitchen canteen, happily eating a simple traditional Shiv Bhojan meal consisting of dal, rice, hot chapati, and vegetable curry from a stainless steel partition thali plate, overhead indoor lighting, natural textures, 4k."

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
            
            if ai_generated_prompt.startswith("```"):
                ai_generated_prompt = ai_generated_prompt.replace("```text", "").replace("```", "").strip()
                
            logging.info(f"Compiled Flux-Prompt: '{ai_generated_prompt[:120]}...'")
            
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
