import os
import time
import random
import requests
import urllib.parse
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
from PIL import Image, ImageOps
from dotenv import load_dotenv
from prompts import VISION_SYSTEM_PROMPT, STYLE_PRESETS

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure Google Gemini (Vision)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Folder to save images locally
UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def index():
    return render_template('index.html')


def get_gemini_vision_description(image_path):
    """
    Asks Gemini to describe the image. 
    We still use this to tell the Image Generator WHAT is in the picture 
    so it knows how to style it correctly.
    """
    try:
        # FIX: Switched to 'gemini-1.5-flash' for better stability and higher free limits
        model = genai.GenerativeModel('gemini-2.5-flash') 
        img = Image.open(image_path)
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass
        img = img.convert("RGB")
        
        response = model.generate_content([VISION_SYSTEM_PROMPT, img])
        return response.text
    except Exception as e:
        print(f"Gemini Vision Error: {e}")
        return None

def upload_image_to_public_host(file_path):
    """
    Uploads the local image to a temporary public host (Catbox.moe)
    so that the Pollinations AI can access it for Image-to-Image processing.
    """
    try:
        print("Uploading image to public host for AI access...")
        with open(file_path, 'rb') as f:
            # Catbox.moe is a simple free file host often used for this
            response = requests.post(
                'https://catbox.moe/user/api.php',
                data={'reqtype': 'fileupload'},
                files={'fileToUpload': f},
                timeout=30
            )
        
        if response.status_code == 200:
            public_url = response.text.strip()
            print(f"Image publicly accessible at: {public_url}")
            return public_url
        else:
            print(f"Upload failed: {response.text}")
            return None
    except Exception as e:
        print(f"Upload Error: {e}")
        return None

def download_image_with_retry(url, retries=3, timeout=120):
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                return response
        except Exception as e:
            print(f"Retry {attempt+1} failed: {e}")
            time.sleep(2)
    return None

@app.route('/generate-image', methods=['POST'])
def generate_image():
    try:
        prompt = request.form.get('prompt')
        style = request.form.get('style')
        uploaded_file = request.files.get('image')
        
        final_prompt = ""
        image_url_param = "" # This will hold the URL of the source image

        # --- CASE 1: Image Uploaded (Real Image-to-Image) ---
        if uploaded_file:
            print("Processing uploaded image...")
            filename = f"upload_{int(time.time())}.png"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            uploaded_file.save(filepath)
            
            # 1. Upload to public host so Pollinations can see it
            public_image_url = upload_image_to_public_host(filepath)
            
            if public_image_url:
                # Add the image URL to the API call
                image_url_param = f"&image={public_image_url}"
            else:
                print("Warning: Could not upload image. Falling back to Prompt-to-Image.")

            # 2. Get Description (still needed to guide the style)
            vision_description = get_gemini_vision_description(filepath)
            
            if not vision_description:
                if prompt:
                    vision_description = prompt
                else:
                    # If Gemini fails (e.g., rate limit) and no text prompt was given
                    return jsonify({'status': 'error', 'message': 'AI is busy. Please enter a text prompt describing your image and try again.'})
            
            # Use the description as the base prompt
            final_prompt = vision_description

        # --- CASE 2: Text Only ---
        elif prompt:
            final_prompt = prompt
        else:
            return jsonify({'status': 'error', 'message': 'Please upload an image or enter text!'})

        # --- APPLY STYLE ---
        if style in STYLE_PRESETS:
            final_prompt += STYLE_PRESETS[style]
        else:
            final_prompt += f", {style} style, high quality"

        # --- GENERATE WITH REAL IMG2IMG ---
        print(f"Generative Prompt: {final_prompt[:100]}...")
        
        seed = random.randint(1, 10000)
        encoded_prompt = urllib.parse.quote(final_prompt)
        
        # We append image_url_param if it exists. 
        api_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model=flux&width=1024&height=1024&seed={seed}&nologo=true{image_url_param}"
        
        print(f"Calling API: {api_url}")

        response = download_image_with_retry(api_url)

        if response:
            gen_filename = f"gen_{int(time.time())}.png"
            gen_filepath = os.path.join(UPLOAD_FOLDER, gen_filename)
            
            with open(gen_filepath, "wb") as f:
                f.write(response.content)
            
            return jsonify({
                'status': 'success',
                'image_url': "/" + gen_filepath
            })
        else:
            return jsonify({'status': 'error', 'message': 'Server Busy. Try again.'})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5000)