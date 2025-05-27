import csv
import re
import os

def convert_qa_to_csv(input_file, output_file):
    """
    Convert Q&A text file to CSV format with Question and Answer columns.
    
    Args:
        input_file (str): Path to the input text file
        output_file (str): Path to the output CSV file
    """
    
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        return
    
    try:
        # Read the input file
        with open(input_file, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Regular expression to match Q: and A: pairs
        # This pattern captures everything after Q: until it finds A:, then captures everything after A: until next Q: or end
        qa_pattern = re.compile(r'Q:\s*(.*?)\s*A:\s*(.*?)(?=Q:|$)', re.DOTALL)
        
        # Find all Q&A pairs
        matches = qa_pattern.findall(content)
        
        if not matches:
            print("No Q&A pairs found in the file.")
            return
        
        # Clean up the extracted text (remove extra whitespace and newlines)
        qa_pairs = []
        for question, answer in matches:
            # Clean question and answer text
            clean_question = ' '.join(question.strip().split())
            clean_answer = ' '.join(answer.strip().split())
            qa_pairs.append([clean_question, clean_answer])
        
        # Write to CSV file
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            writer.writerow(['Question', 'Answer'])
            
            # Write Q&A pairs
            writer.writerows(qa_pairs)
        
        print(f"Successfully converted {len(qa_pairs)} Q&A pairs to '{output_file}'")
        
    except Exception as e:
        print(f"Error processing file: {e}")

def main():
    # Configure input and output file paths
    input_file = "/home/kayden/Desktop/python_projects/ExamBOT/metal-mining/all_qa_pairs.txt"  # Change this to your input file name
    output_file = "mining_qa_pairs.csv"  # Change this to your desired output file name
    
    convert_qa_to_csv(input_file, output_file)

if __name__ == "__main__":
    main()