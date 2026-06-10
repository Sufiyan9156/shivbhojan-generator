import os

print("Railway Started")

print("GEMINI_KEY_1:", "OK" if os.getenv("GEMINI_KEY_1") else "MISSING")
print("GEMINI_KEY_2:", "OK" if os.getenv("GEMINI_KEY_2") else "MISSING")
print("REFERENCE_FOLDER_ID:", os.getenv("REFERENCE_FOLDER_ID"))
print("OUTPUT_FOLDER_ID:", os.getenv("OUTPUT_FOLDER_ID"))

if os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"):
    print("GOOGLE_SERVICE_ACCOUNT_JSON: OK")
else:
    print("GOOGLE_SERVICE_ACCOUNT_JSON: MISSING")
