import fitz # PyMuPDF
import os

# --- Configuration ---
INPUT_PDF_PATH = "/home/kayden/Desktop/python_projects/ExamBOT/metal-mining/Lec3-Underground Mine Development.pdf"   # <--- REPLACE with the path to your original PDF
OUTPUT_PDF_PATH = "underground_mine_development.pdf" # Name for the new PDF after trimming

# --- Main Logic ---

def trim_pdf_pages(input_pdf_path, output_pdf_path):
    """
    Creates a new PDF by removing the first page and the last two pages
    from the input PDF.
    """
    if not os.path.exists(input_pdf_path):
        print(f"Error: Input PDF file not found at '{input_pdf_path}'")
        return

    try:
        # Open the original PDF
        doc = fitz.open(input_pdf_path)
        total_pages = doc.page_count
        print(f"Original PDF '{input_pdf_path}' has {total_pages} pages.")

        # Determine the range of pages to keep (0-indexed)
        # We want to skip the first page (index 0)
        # And skip the last two pages (indices total_pages - 1 and total_pages - 2)
        # So, the pages to keep are from index 1 up to (but not including) total_pages - 2
        start_page_to_keep = 1
        end_page_to_keep_exclusive = total_pages - 2

        # Handle edge cases where the PDF is too small
        if total_pages <= 3:
            print(f"PDF has {total_pages} page(s). Skipping the first page and the last two pages leaves no pages to process.")
            print("No output PDF will be created.")
            doc.close()
            return
        
        if end_page_to_keep_exclusive <= start_page_to_keep:
            print(f"Calculated page range to keep is empty or invalid. This might happen with very short PDFs.")
            print(f"Pages to keep would be from index {start_page_to_keep} to {end_page_to_keep_exclusive-1}.")
            print("No output PDF will be created.")
            doc.close()
            return

        # Create a new, empty PDF document
        new_doc = fitz.open()

        print(f"Copying pages from index {start_page_to_keep} to {end_page_to_keep_exclusive - 1} (inclusive)...")

        # Insert selected pages into the new document
        # The insert_pdf method is convenient for copying ranges or specific pages
        new_doc.insert_pdf(doc, 
                           from_page=start_page_to_keep, 
                           to_page=end_page_to_keep_exclusive - 1)

        # Save the new PDF
        new_doc.save(output_pdf_path)
        print(f"Successfully created '{output_pdf_path}' with {new_doc.page_count} pages.")

        # Close documents
        doc.close()
        new_doc.close()

    except Exception as e:
        print(f"An error occurred during PDF trimming: {e}")

# --- Execute the script ---
if __name__ == "__main__":
    trim_pdf_pages(INPUT_PDF_PATH, OUTPUT_PDF_PATH)