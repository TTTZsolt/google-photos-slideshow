from google import genai
from google.genai import types
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
) -> tuple[str, str]:
    """
    Downloads an image (thumbnail) and uses Gemini API to classify it or suggest deletion.
    Returns a tuple: (exact_category_name_or_delete, model_name_that_succeeded).
    Raises Exception if all models fail.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise Exception("GEMINI_API_KEY variable is missing in environment.")
    
    client = genai.Client(api_key=api_key)

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
                
            result = client.models.generate_content(
                model=m_name,
                contents=[img, "Please classify this image."],
                config=types.GenerateContentConfig(system_instruction=system_instruction),
            )
            text = result.text.strip().lower()
            
            # Validate output
            valid_outputs = [c.lower() for c in available_categories.keys()] + ["delete", "uncategorized"]
            text = text.replace('.', '').replace('\'', '').replace('"', '')
            
            if text not in valid_outputs:
                logger.warning(f"AI model {m_name} returned unexpected category: '{text}'. Falling back to uncategorized.")
                return "uncategorized", m_name
                
            return text, m_name
        except Exception as e:
            logger.warning(f"AI model '{m_name}' failed: {e}. Trying next fallback...")
            last_error = e

    raise Exception(f"All models failed. Last error: {last_error}")


def pick_best_from_duplicate_group(
    image_urls: list[str],
    custom_rules: str = "",
    model_name: str = "gemini-2.5-flash"
) -> tuple[int, str]:
    """
    Downloads a small group of near-duplicate/burst images (already identified as
    visually near-identical by perceptual hashing) and asks Gemini to pick the ONE
    to keep - the only way to apply a "keep just the best of these similar shots"
    rule, since a single-image classification call never sees its siblings.

    Returns (index_to_keep, model_name_that_succeeded), index is 0-based into
    image_urls. Raises Exception if all models fail.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise Exception("GEMINI_API_KEY variable is missing in environment.")

    client = genai.Client(api_key=api_key)

    imgs = []
    for url in image_urls:
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            imgs.append(Image.open(BytesIO(resp.content)))
        except Exception as img_err:
            raise Exception(f"Failed to download duplicate-group image: {img_err}")

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
            system_instruction = (
                "You will be shown a sequence of very similar photos - likely a burst "
                "or near-duplicate shots of the same moment - labeled Image 1, Image 2, "
                "etc. in the order given. Pick exactly ONE to keep: the best one overall "
                "(sharpest, best composition, eyes open, faces visible and not obscured). "
                "Reply ONLY with the number of the image to keep (e.g. '2'). "
                "DO NOT output any other text or explanation."
            )
            if custom_rules:
                system_instruction += f"\n\nCRITICAL USER'S CUSTOM RULES:\n{custom_rules}"

            contents = []
            for i, img in enumerate(imgs):
                contents.append(f"Image {i + 1}:")
                contents.append(img)
            contents.append("Which image should be kept? Reply with only its number.")

            result = client.models.generate_content(
                model=m_name,
                contents=contents,
                config=types.GenerateContentConfig(system_instruction=system_instruction),
            )
            text = result.text.strip()
            digits = "".join(ch for ch in text if ch.isdigit())
            if not digits:
                logger.warning(f"AI model {m_name} returned no parseable index: '{text}'. Defaulting to first image.")
                return 0, m_name
            idx = int(digits) - 1
            if not (0 <= idx < len(imgs)):
                logger.warning(f"AI model {m_name} returned out-of-range index: '{text}'. Defaulting to first image.")
                return 0, m_name
            return idx, m_name
        except Exception as e:
            logger.warning(f"AI model '{m_name}' failed (duplicate group): {e}. Trying next fallback...")
            last_error = e

    raise Exception(f"All models failed (duplicate group). Last error: {last_error}")
