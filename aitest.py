from openai import OpenAI
import base64
import requests
from dotenv import load_dotenv
import os
from PIL import Image
from io import BytesIO

# Load environment variables
load_dotenv()

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
IMGBB_API_KEY = os.getenv("IMGBB_API_KEY")
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")

# 1️⃣ Upload local image to ImgBB
def upload_to_imgbb(image_path):
    with open(image_path, "rb") as f:
        encoded_image = base64.b64encode(f.read())
    url = "https://api.imgbb.com/1/upload"
    payload = {
        "key": IMGBB_API_KEY,
        "image": encoded_image
    }
    response = requests.post(url, data=payload)
    response.raise_for_status()
    return response.json()["data"]["url"]  # Public image URL

# 2️⃣ Analyze uploaded image with GPT
def analyze_image(image_url):
    response = openai.responses.create(
        model="gpt-4.1-mini",
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": "Give me a star rating out of 10. Describe this image in detail and give me an explanation (2-3 sentences)."},
                {"type": "input_image", "image_url": image_url}
            ]
        }]
    )
    return response.output_text

# 3️⃣ Generate a recipe
def generate_recipe(dish_name):
    response = openai.responses.create(
        model="gpt-4.1-mini",
        input=f"Generate a detailed recipe for {dish_name}, including ingredients and step-by-step instructions."
    )
    return response.output_text

# 4️⃣ Generate an image of the dish using Stability API
def generate_dish_image(dish_name):
    url = "https://api.stability.ai/v2beta/stable-image/generate/core"

    headers = {
        "Authorization": f"Bearer {STABILITY_API_KEY}",
        "Accept": "application/json"
    }

    payload = {
        "prompt": f"A professional, realistic photograph of {dish_name}, plated which looks like I would make it at home, make it look realistic and less perfectionist like a human would actually make it, make it less perfect and less fancy, and make it look human like.",
        "output_format": "png",
        "aspect_ratio": "1:1"
    }

    response = requests.post(url, headers=headers, files={"none": ""}, data=payload)
    response.raise_for_status()

    data = response.json()

    if "image" in data:
        image_b64 = data["image"]
        image_bytes = base64.b64decode(image_b64)
        img = Image.open(BytesIO(image_bytes))
        img.save("dish.png")
        img.show()
        return "dish.png"
    else:
        raise ValueError(f"Unexpected response format: {data}")

# -------------------------
# Example usage
# -------------------------
if __name__ == "__main__":
    # Upload image + analyze
    image_url = upload_to_imgbb("image.png")
    print(f"Uploaded image URL: {image_url}")
    print("Analysis:", analyze_image(image_url))

    # Generate recipe
    dish = "Spaghetti Carbonara"
    recipe = generate_recipe(dish)
    print("\nRecipe:\n", recipe)

    # Generate dish image with Stability
    print("\nGenerating image of the dish with Stability...")
    generate_dish_image(dish)