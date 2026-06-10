import os
import time
import random
from datetime import datetime
import json
import logging
import requests
import google.generativeai as genai
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import io

# Setup Clean Logging for Railway Console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- CONFIGURATION & ENV VARIABLES ---
GEMINI_KEY_1 = os.getenv("GEMINI_KEY_1")
GEMINI_KEY_2 = os.getenv("GEMINI_KEY_2")
REFERENCE_FOLDER_ID = os.getenv("REFERENCE_FOLDER_ID")
OUTPUT_FOLDER_ID = os.getenv("OUTPUT_FOLDER_ID")
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

# 24/7 Diversified Maharashtrian Characters List
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

# --- GOOGLE DRIVE AUTHENTICATION ---
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

# --- DYNAMIC DATE FOLDER GENERATOR ---
def get_or_create_today_folder(service):
    today_str = datetime.now().strftime("%d %B %Y")
    
    query = f"name = '{today_str}' and '{OUTPUT_FOLDER_ID}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = service.files().list(q=query, fields="files(id)").execute()
    items = results.get('files', [])
    
    if items:
        return items[0]['id']
    else:
        logging.info(f"Dynamic Folder missing. Creating folder: {today_str}")
        file_metadata = {
            'name': today_str,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [OUTPUT_FOLDER_ID]
        }
        folder = service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')

# --- DOWNLOAD RANDOM REFERENCE IMAGE FROM DRIVE ---
def download_random_reference(service):
    query = f"'{REFERENCE_FOLDER_ID}' in parents and (mimeType = 'image/jpeg' or mimeType = 'image/png') and trashed = false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])
    
    if not items:
        raise Exception("Drive Error: REFERENCES folder is empty or not accessible!")
        
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

# --- ULTRAL-REALISTIC IMAGE GENERATION ENGINE (FLUX FLAVOR) ---
def generate_new_image(prompt_text):
    logging.info("Routing prompt to high-fidelity photo engine...")
    encoded_prompt = requests.utils.quote(prompt_text)
    
    seed = random.randint(100000, 999999)
    url = f"https://image.pollinations.ai/p/{encoded_prompt}?width=1024&height=1024&model=flux&seed={seed}&nologo=true"
    
    response = requests.get(url)
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"Flux Engine failed. Http status code: {response.status_code}")

# --- SYSTEM CORE EXECUTION ---
def main():
    logging.info("=== SHIV BHOJAN AI ENGINE SYSTEM STARTING ===")
    service = get_drive_service()
    
    cycle_counter = 0
    
    while True:
        try:
            cycle_counter += 1
            logging.info(f"--- Starting Active Cycle #{cycle_counter} ---")
            
            if cycle_counter % 2 != 0:
                current_key = GEMINI_KEY_1
                key_label = "GEMINI_KEY_1"
            else:
                current_key = GEMINI_KEY_2
                key_label = "GEMINI_KEY_2"
                
            genai.configure(api_key=current_key)
            logging.info(f"Rotated key configuration context to: {key_label}")
            
            image_bytes, original_filename = download_random_reference(service)
            
            target_character = random.choice(CHARACTERS)
            logging.info(f"Targeting new subject character inject: {target_character}")
            
            structured_prompt = (
                f"Analyze this Shiv Bhojan meal photograph thoroughly. Write a highly detailed, comprehensive image generation prompt. "
                f"Your prompt must keep the exact same context: the indoor setting of a crowded local government-subsidized kitchen canteen, "
                f"the layout of the table, the specific steel partition thali plate, the local Indian food (dal, yellowish rice, flat chapati, vegetable curry). "
                f"The lighting must stay as a realistic, overhead white tube-light or afternoon natural light coming from an open door. "
                f"CRITICAL REPLACEMENT: Completely remove the person sitting in front of the thali in this photo, and replace them with: {target_character}. "
                f"The person should look like they are in the middle of eating their food naturally. "
                f"STYLE RULES: The overall final generated image must look like a realistic documentary-style raw photograph taken from a mid-range Android smartphone camera "
                f"by an ordinary person. Natural skin textures, no artificial enhancements, 4k resolution, hyper-realistic, candid shot. "
                f"OUTPUT INSTRUCTION: Reply ONLY with the final descriptive image prompt text. Do not add any conversational chat, explanations, introductory remarks, or markdown code blocks."
            )
            
            image_payload = {
                'mime_type': 'image/jpeg',
                'data': image_bytes
            }
            
            logging.info("Querying Gemini vision model for background preservation map...")
            
            # Smart Fallback System to tackle Google's 404 Endpoint issues
            ai_generated_prompt = ""
            model_names_to_try = ['models/gemini-1.5-flash', 'gemini-1.5-flash', 'models/gemini-pro-vision']
            
            for model_name in model_names_to_try:
                try:
                    logging.info(f"Attempting API call with endpoint: {model_name}")
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content([structured_prompt, image_payload])
                    ai_generated_prompt = response.text.strip()
                    if ai_generated_prompt:
                        logging.info(f"Success with model: {model_name}")
                        break
                except Exception as model_err:
                    logging.warning(f"Model {model_name} failed or gave 404. Trying next...")
                    continue
            
            if not ai_generated_prompt:
                raise Exception("All available Gemini Vision models failed to respond (404/Routing issues).")
            
            if ai_generated_prompt.startswith("```"):
                ai_generated_prompt = ai_generated_prompt.replace("```text", "").replace("```", "").strip()
                
            logging.info(f"Successfully compiled Flux-Prompt: '{ai_generated_prompt[:120]}...'")
            
            new_image_data = generate_new_image(ai_generated_prompt)
            
            active_folder_id = get_or_create_today_folder(service)
            
            current_timestamp = datetime.now().strftime("%H-%M-%S")
            final_filename = f"photo_{current_timestamp}.jpg"
            
            meta_data = {
                'name': final_filename,
                'parents': [active_folder_id]
            }
            
            media_content = MediaFileUpload(
                io.BytesIO(new_image_data),
                mimetype='image/jpeg',
                resumable=True
            )
            
            uploaded_node = service.files().create(
                body=meta_data,
                media_body=media_content,
                fields='id'
            ).execute()
            
            logging.info(f"SUCCESS: Generated asset '{final_filename}' synced to Drive. ID: {uploaded_node.get('id')}")
            
        except Exception as error:
            logging.error(f"FAIL: Error caught in active loop: {str(error)}")
            logging.info("Preserving process uptime. Safe-skipping directly to next cycle countdown.")
            
        logging.info("Cycle complete. System cooling down for 150 seconds...")
        time.sleep(150)

if __name__ == "__main__":
    main()
