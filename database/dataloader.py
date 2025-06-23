import csv
import os
from tidb import tidb_client, QAPair

def load_csv_to_tidb(csv_file_path: str):
    """
    Load CSV data into TiDB
    
    Parameters:
    csv_file_path (str): Path to the CSV file
    """
    try:
        if not os.path.exists(csv_file_path):
            print(f"❌ CSV file not found: {csv_file_path}")
            return False
        
        qa_pairs = []
        
        with open(csv_file_path, "r", encoding="utf-8") as f:
            csv_reader = csv.DictReader(f)
            
            for i, row in enumerate(csv_reader, start=1):
                qa_pair = QAPair(
                    id=i,
                    question=row["question"],
                    answer=row["answer"],
                    topic=row["topic"],
                    type=row["type"],
                    difficulty=row["difficulty"].lower() 
                )
                qa_pairs.append(qa_pair)
        
        tidb_client.table.bulk_insert(qa_pairs)
        
        print(f"✅ Successfully loaded {len(qa_pairs)} Q&A pairs into TiDB!")
        return True
        
    except Exception as e:
        print(f"❌ Error loading CSV to TiDB: {str(e)}")
        return False

def check_data_exists() -> bool:
    """Check if data already exists in the table"""
    try:
        count = len(tidb_client.table.to_list())
        return count > 0
    except:
        return False

if __name__ == "__main__":
    csv_path = "/home/kayden/Desktop/python_projects/ExamPrepAgent/dataset/kubernetes_qa.csv" 
    
    if not check_data_exists():
        print("📊 Loading CSV data to TiDB...")
        load_csv_to_tidb(csv_path)
    else:
        print("✅ Data already exists in TiDB!")

