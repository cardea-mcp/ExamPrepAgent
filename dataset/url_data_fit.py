import csv
import re

def parse_kubernetes_qa_to_csv(input_file, output_file):
    """
    Parse Kubernetes Q&A text file and convert to CSV format
    """
    questions = []
    
    with open(input_file, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Split by the separator line
    sections = content.split('--------------------------------------------------')
    
    for section in sections:
        section = section.strip()
        if not section:
            continue
            
        # Extract question
        question_match = re.search(r'Q\d+:\s*(.*?)(?=\nA\d+:)', section, re.DOTALL)
        if not question_match:
            continue
        question = question_match.group(1).strip()
        
        # Extract answer
        answer_match = re.search(r'A\d+:\s*(.*?)(?=\nDifficulty:|$)', section, re.DOTALL)
        if not answer_match:
            continue
        answer = answer_match.group(1).strip()
        
        # Extract difficulty
        difficulty_match = re.search(r'Difficulty:\s*(\w+)', section)
        difficulty = difficulty_match.group(1) if difficulty_match else ''
        
        # Extract topic
        topic_match = re.search(r'Topic:\s*([^\n]+)', section)
        topic = topic_match.group(1).strip() if topic_match else ''
        
        # Extract type
        type_match = re.search(r'Type:\s*(\w+)', section)
        question_type = type_match.group(1) if type_match else ''
        
        # Add to questions list
        questions.append({
            'question': question,
            'answer': answer,
            'topic': topic,
            'type': question_type,
            'difficulty': difficulty
        })
    
    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['question', 'answer', 'topic', 'type', 'difficulty']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for question in questions:
            writer.writerow(question)
    
    print(f"Successfully converted {len(questions)} questions to {output_file}")

# Usage
if __name__ == "__main__":
    input_filename = "/home/kayden/Desktop/python_projects/ExamBOT/dataset/kubernetes_basic.txt"  # Replace with your input file name
    output_filename = "kubernetes_qa.csv"
    
    try:
        parse_kubernetes_qa_to_csv(input_filename, output_filename)
    except FileNotFoundError:
        print(f"Error: File '{input_filename}' not found. Please check the file path.")
    except Exception as e:
        print(f"Error: {str(e)}")