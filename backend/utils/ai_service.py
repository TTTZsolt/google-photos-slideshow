import google.generativeai as genai
import os
import requests
from io import BytesIO
import logging

try:
    from PIL import Image
except ImportError:
    pass # Might need pillow

logger = logging.getLogger(__name__)

def analyze_image_for_sorting(
    image_url: str, 
    available_categories: list[str], 
    custom_rules: str = "", 
    model_name: str = "gemini-2.5-flash"
) -> str:
    """
    Downloads an image (thumbnail) and uses Gemini API to classify it or suggest deletion.
    Returns the exact category name, or "delete".
    """
    if "1.5" in model_name:
        model_name = model_name.replace("1.5", "2.5")
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY is not set in environment.")
        return "delete" # Safe fallback or maybe return None? Let's return None on error
    
    genai.configure(api_key=api_key)

    try:
        # 1. Download image
        response = requests.get(image_url, timeout=15)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
        
        # 2. Prepare Prompt
        cats_str = ", ".join(available_categories)
        system_instruction = (
            "You are an expert photo sorter assistant. Your task is to analyze the provided image and decide which category it belongs to, or if it should be deleted. "
            f"Available categories: {cats_str}.\n"
            "If the photo is very blurry, completely dark, an accidental pocket shot, or generally bad, reply ONLY with 'delete'. "
            "Otherwise, reply ONLY with the EXACT name of the best matching category from the list above. "
            "If it does not fit any category clearly, but is a good photo, reply with 'uncategorized'. "
            "DO NOT output any other text or explanation."
        )
        
        if custom_rules:
            system_instruction += f"\n\nCRITICAL USER'S CUSTOM RULES:\n{custom_rules}"
            
        model = genai.GenerativeModel(model_name=model_name, system_instruction=system_instruction)
        
        # 3. Generate
        result = model.generate_content([img, "Please classify this image."])
        
        text = result.text.strip().lower()
        
        # Validate output
        valid_outputs = [c.lower() for c in available_categories] + ["delete", "uncategorized"]
        
        # Clean up punctuation just in case
        text = text.replace('.', '').replace('\'', '').replace('"', '')
        
        if text not in valid_outputs:
            logger.warning(f"AI returned unexpected category: '{text}'. Falling back to uncategorized.")
            return "uncategorized"
            
        return text
        
    except Exception as e:
        logger.error(f"AI classification failed for {image_url}: {e}")
        return "uncategorized" # Fallback so we don't break the flow
