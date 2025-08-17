import pandas as pd
import re

def extract_question_answer_from_csv(input_file, output_file):
    """
    Extract questions and answers from CSV text field.
    
    Args:
        input_file (str): Path to input CSV file
        output_file (str): Path to output CSV file
    
    Returns:
        pandas.DataFrame: DataFrame with question and answer columns
    """
    # Read the CSV file
    df = pd.read_csv(input_file)
    
    # Initialize lists to store questions and answers
    questions = []
    answers = []
    
    # Process each text entry
    for text in df['text']:
        # Split on "**Correct Answer:" using regex
        parts = re.split(r'\*\*Correct Answer:\s*', text, maxsplit=1)
        
        if len(parts) == 2:
            # Extract question (everything before "**Correct Answer:")
            question = parts[0].strip()
            # Remove trailing " — " if present
            question = re.sub(r'\s*—\s*$', '', question)
            
            # Extract answer (everything after "**Correct Answer:")
            answer = parts[1].strip()
            # Remove trailing "**" if present
            answer = re.sub(r'\*\*$', '', answer)
            
            questions.append(question)
            answers.append(answer)
        else:
            # If no correct answer found, treat entire text as question with empty answer
            print(f"Warning: No correct answer found in: {text[:50]}...")
            questions.append(text.strip())
            answers.append("")
    
    # Create new dataframe
    new_df = pd.DataFrame({
        'question': questions,
        'answer': answers
    })
    
    # Save to CSV
    new_df.to_csv(output_file, index=False)
    print(f"✅ Extracted {len(new_df)} question-answer pairs to {output_file}")
    
    return new_df

def preview_extraction(input_file, num_rows=3):
    """
    Preview the extraction without saving to file.
    """
    df = pd.read_csv(input_file)
    
    print("Preview of extraction:")
    print("=" * 80)
    
    for i, text in enumerate(df['text'].head(num_rows)):
        parts = re.split(r'\*\*Correct Answer:\s*', text, maxsplit=1)
        
        if len(parts) == 2:
            question = re.sub(r'\s*—\s*$', '', parts[0].strip())
            answer = re.sub(r'\*\*$', '', parts[1].strip())
            
            print(f"Row {i+1}:")
            print(f"Question: {question}")
            print(f"Answer: {answer}")
            print("-" * 40)

if __name__ == "__main__":
    # Configuration
    input_file = "/home/kayden/Desktop/python_projects/ExamPrepAgent/medium_paragraphs.csv"  # Replace with your CSV file path
    output_file = "k8s_qa.csv"
    
    # Preview first few extractions
    print("Previewing extraction...")
    preview_extraction(input_file)
    
    # Extract all questions and answers
    print("\nExtracting all data...")
    df = extract_question_answer_from_csv(input_file, output_file)
    
    # Display statistics
    print(f"\nExtraction Statistics:")
    print(f"Total rows processed: {len(df)}")
    print(f"Average question length: {df['question'].str.len().mean():.1f} characters")
    print(f"Average answer length: {df['answer'].str.len().mean():.1f} characters")
    
    # Display first few rows
    print(f"\nFirst 3 rows of extracted data:")
    print(df.head(3).to_string(index=False))