import os
import re

# --- Configuration ---
INPUT_DIR = "qna_output"  # Directory where your Q&A text files are located
OUTPUT_FILE = "all_qa_pairs.txt" # Name of the file to store all collected Q&A

# Regular expression to capture a Q: and A: pair
# (Q:.*?) captures "Q: " followed by anything non-greedily until a newline
# \n matches the newline after the question
# (A:.*) captures "A: " followed by anything until the end of the line (or next line if it spans)
# re.DOTALL ensures that '.' can match newlines, though for this specific format it might not be strictly necessary
# but it's good practice for potentially multi-line answers.
QA_PATTERN = re.compile(r"(Q:.*?)\n(A:.*)", re.DOTALL)

# --- Main Logic ---

def collect_qna_from_directory(input_directory, output_filepath):
    """
    Collects all Q&A pairs from text files in a given directory
    and writes them to a single output file.
    """
    if not os.path.isdir(input_directory):
        print(f"Error: Input directory '{input_directory}' not found.")
        return

    all_collected_qa = []

    print(f"Scanning directory: '{input_directory}' for Q&A files...")
    # List all files in the directory
    for filename in os.listdir(input_directory):
        if filename.endswith(".txt"): # Process only text files
            filepath = os.path.join(input_directory, filename)
            print(f"Processing file: '{filename}'")

            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()

                # Find all Q&A pairs using the regex pattern
                # matches will be a list of tuples, where each tuple is (question_line, answer_line)
                matches = QA_PATTERN.findall(content)

                if matches:
                    print(f"  Found {len(matches)} Q&A pairs.")
                    all_collected_qa.extend(matches)
                else:
                    print("  No Q&A pairs found in this file (or format mismatch).")

            except Exception as e:
                print(f"Error reading or parsing file '{filename}': {e}")
    
    print(f"\nCollected a total of {len(all_collected_qa)} Q&A pairs from all files.")

    # Write all collected Q&A to a single output file
    try:
        with open(output_filepath, "w", encoding="utf-8") as outfile:
            for q_line, a_line in all_collected_qa:
                outfile.write(f"{q_line}\n{a_line}\n\n") # Q, then A, then two newlines for separation
        print(f"Successfully wrote all Q&A pairs to '{output_filepath}'")
    except Exception as e:
        print(f"Error writing to output file '{output_filepath}': {e}")

# --- Execute the script ---
if __name__ == "__main__":
    collect_qna_from_directory(INPUT_DIR, OUTPUT_FILE)