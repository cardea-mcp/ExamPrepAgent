import fitz  # PyMuPDF
import google.generativeai as genai
import os
from dotenv import load_dotenv
import io
from PIL import Image

# Load environment variables
load_dotenv()

# Configure Google Generative AI with your API key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in .env file. Please create one.")
genai.configure(api_key=GOOGLE_API_KEY)

# --- Configuration ---
PDF_PATH = "/home/kayden/Desktop/python_projects/ExamBOT/metal-mining/lec4_underground_mine_development.pdf"  # <--- REPLACE WITH YOUR PDF FILE PATH
OUTPUT_DIR = "qna_output"     # Directory to save Q&A if needed
MODEL_NAME = "gemini-1.5-flash"
PROMPT = """Generate 5 distinct and informative question and answer pairs from the content of this page. 
Focus on key facts, concepts, and relationships.
Format each pair clearly as:
Q: <question text>
A: <answer text>

If there is only image in the page, you don't have to generate 5 question and answer pairs. You can generate fewer question and answer pairs which are most relevant to the image.
"""

# --- Helper Functions (same as before) ---

def pdf_page_to_image(pdf_path, page_num, dpi=300):
    """
    Converts a specific page of a PDF into a PIL Image object.
    Args:
        pdf_path (str): Path to the PDF file.
        page_num (int): The 0-indexed page number to convert.
        dpi (int): Dots per inch for rendering (higher = better quality, larger image).
    Returns:
        PIL.Image.Image: The rendered page as a PIL Image.
    """
    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(page_num)

        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)

        img = Image.open(io.BytesIO(pix.tobytes("png")))
        doc.close()
        return img
    except Exception as e:
        print(f"Error converting PDF page {page_num} to image: {e}")
        return None

def send_image_to_gemini(image_data, prompt, model_name=MODEL_NAME):
    """
    Sends an image and a prompt to the Gemini Vision model and returns its response.
    Args:
        image_data (bytes or PIL.Image.Image): The image data (PNG bytes or PIL Image object).
        prompt (str): The prompt to send to the model.
        model_name (str): The name of the Gemini model to use.
    Returns:
        str: The generated text response from the model, or None if an error occurs.
    """
    try:
        model = genai.GenerativeModel(model_name)

        if isinstance(image_data, Image.Image):
            byte_arr = io.BytesIO()
            image_data.save(byte_arr, format='PNG')
            image_data = byte_arr.getvalue()

        content = [
            prompt,
            {
                'mime_type': 'image/png',
                'data': image_data
            }
        ]

        print(f"Sending request to Gemini model {model_name}...")
        response = model.generate_content(content)

        if response.prompt_feedback and response.prompt_feedback.block_reason:
            print(f"Gemini blocked content due to: {response.prompt_feedback.block_reason}")
            return None

        return response.text
    except Exception as e:
        print(f"Error sending to Gemini: {e}")
        return None

# --- Main Logic ---

def process_pdf_for_qna(pdf_path, output_dir=OUTPUT_DIR, prompt=PROMPT):
    """
    Processes specific pages of a PDF, converts them to images, sends to Gemini Vision,
    and collects Q&A pairs. Skips the first page and the last two pages.
    Args:
        pdf_path (str): Path to the input PDF file.
        output_dir (str): Directory to save output files (optional).
        prompt (str): The prompt for Gemini Vision.
    Returns:
        list: A list of dictionaries, where each dictionary contains
              'page_num' and 'qna_text' for that page.
    """
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found at '{pdf_path}'")
        return []

    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    all_qna_results = []
    
    try:
        doc = fitz.open(pdf_path)
        total_pages = doc.page_count
        print(f"Processing PDF: '{pdf_path}' with {total_pages} pages...")

        # Determine the range of pages to process
        # We skip the first page (index 0)
        # And skip the last two pages (indices total_pages-1 and total_pages-2)
        start_page_index = 1
        end_page_index = total_pages - 2 # range's end is exclusive, so this means pages up to total_pages-3

        # Check if there are enough pages to process after skipping
        if end_page_index <= start_page_index: # means total_pages <= 3
            print(f"PDF has {total_pages} page(s). Skipping the first page and the last two pages leaves no pages to process.")
            print("No pages will be processed based on the skip criteria.")
            doc.close()
            return []

        # Modified loop range
        for page_num in range(start_page_index, end_page_index):
            print(f"\n--- Processing Page {page_num + 1}/{total_pages} (Actual PDF Page) ---")
            
            # 1. Convert PDF page to image
            pil_image = pdf_page_to_image(pdf_path, page_num)
            if pil_image is None:
                print(f"Skipping page {page_num + 1} due to image conversion error.")
                continue

            # 2. Send image to Gemini Vision
            qna_text_from_gemini = send_image_to_gemini(pil_image, prompt)

            if qna_text_from_gemini:
                print(f"Generated Q&A for Page {page_num + 1}:\n{qna_text_from_gemini}")
                all_qna_results.append({
                    'page_num': page_num + 1,
                    'qna_text': qna_text_from_gemini
                })
                
                # Optional: Save Q&A to a file per page
                if output_dir:
                    output_file_path = os.path.join(output_dir, f"page_{page_num + 1}_qna.txt")
                    with open(output_file_path, "w", encoding="utf-8") as f:
                        f.write(f"--- Q&A for Page {page_num + 1} ---\n\n")
                        f.write(qna_text_from_gemini)
                    print(f"Saved Q&A for page {page_num + 1} to {output_file_path}")
            else:
                print(f"No Q&A generated for Page {page_num + 1}.")
                all_qna_results.append({
                    'page_num': page_num + 1,
                    'qna_text': "N/A - No response or error from Gemini."
                })

        doc.close()
        print("\n--- PDF Processing Complete ---")
        return all_qna_results

    except Exception as e:
        print(f"An unexpected error occurred during PDF processing: {e}")
        return []

if __name__ == "__main__":
    results = process_pdf_for_qna(PDF_PATH)

    print("\n\n--- Summary of All Generated Q&A ---")
    if results:
        for res in results:
            print(f"\n===== Page {res['page_num']} =====")
            print(res['qna_text'])
    else:
        print("No Q&A pairs were generated. Check for errors or if all pages were skipped.")