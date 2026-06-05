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

FALLBACK_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-flash-latest",
    "gemini-1.5-flash"
]

def analyze_image_for_sorting(
    image_url: str, 
    available_categories: list[str], 
    custom_rules: str = "", 
    model_name: str = "gemini-2.5-flash"
) -> str:
    """
    Downloads an image (thumbnail) and uses Gemini API to classify it or suggest deletion.
    Returns the exact category name, or "delete".
    Raises Exception if all models fail.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise Exception("GEMINI_API_KEY variable is missing in environment.")
    
    genai.configure(api_key=api_key)

    try:
        response = requests.get(image_url, timeout=15)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
    except Exception as img_err:
        raise Exception(f"Failed to download image from worker proxy: {img_err}")

    # Prioritize models
    models_to_try = [model_name]
    if "1.5" in model_name:
        mapped = model_name.replace("1.5", "2.5")
        if mapped not in models_to_try:
            models_to_try.append(mapped)
            
    for fb in FALLBACK_MODELS:
        if fb not in models_to_try:
            models_to_try.append(fb)

    last_error = None
    for m_name in models_to_try:
        try:
            cats_list = [f"- {name}: {desc}" if desc else f"- {name}" for name, desc in available_categories.items()]
            cats_str = "\n".join(cats_list)
            system_instruction = (
                "You are an expert photo sorter assistant. Your task is to analyze the provided image and decide which category it belongs to, or if it should be deleted. "
                f"Available categories:\n{cats_str}\n\n"
                "If the photo is very blurry, completely dark, an accidental pocket shot, or generally bad, reply ONLY with 'delete'. "
                "Otherwise, reply ONLY with the EXACT name of the best matching category from the list above. "
                "If it does not fit any category clearly, but is a good photo, reply with 'uncategorized'. "
                "DO NOT output any other text or explanation."
            )
            
            if custom_rules:
                system_instruction += f"\n\nCRITICAL USER'S CUSTOM RULES:\n{custom_rules}"
                
            model = genai.GenerativeModel(model_name=m_name, system_instruction=system_instruction)
            result = model.generate_content([img, "Please classify this image."])
            text = result.text.strip().lower()
            
            # Validate output
            valid_outputs = [c.lower() for c in available_categories.keys()] + ["delete", "uncategorized"]
            text = text.replace('.', '').replace('\'', '').replace('"', '')
            
            if text not in valid_outputs:
                logger.warning(f"AI model {m_name} returned unexpected category: '{text}'. Falling back to uncategorized.")
                return "uncategorized"
                
            return text
        except Exception as e:
            logger.warning(f"AI model '{m_name}' failed: {e}. Trying next fallback...")
            last_error = e
            
    raise Exception(f"All models failed. Last error: {last_error}")
