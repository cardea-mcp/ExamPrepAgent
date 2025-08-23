import csv
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv()

class KnowledgeBaseLoader:
    def __init__(self):
        # Create connection with SSL for TiDB Cloud
        connection_string = (
            f"mysql+pymysql://{os.getenv('TIDB_USERNAME')}:{os.getenv('TIDB_PASSWORD')}@"
            f"{os.getenv('TIDB_HOST')}:{os.getenv('TIDB_PORT', 4000)}/{os.getenv('TIDB_DATABASE')}"
            f"?ssl_verify_cert=true&ssl_verify_identity=true"
        )
        
        self.engine = create_engine(
            connection_string,
            echo=True,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        self.Session = sessionmaker(bind=self.engine)
    
    def create_k8_qa_pairs_table(self):
        """Create k8_qa_pairs_llm table with larger text fields"""
        with self.engine.connect() as conn:
            # Drop table if exists
            conn.execute(text("DROP TABLE IF EXISTS k8_qa_pairs_llm"))
            
            # Create table with larger text fields
            create_table_sql = """
            CREATE TABLE k8_qa_pairs_llm (
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                content LONGTEXT NOT NULL,
                question TEXT NOT NULL,
                answer LONGTEXT NOT NULL,
                explanation LONGTEXT NOT NULL,
                FULLTEXT INDEX (content) WITH PARSER MULTILINGUAL
            )
            """
            conn.execute(text(create_table_sql))
            conn.commit()
            print("✅ Created k8_qa_pairs table with large text fields")
    
    def load_csv_data(self, csv_file_path: str):
        """Load CSV data directly into k8_qa_pairs table"""
        try:
            if not os.path.exists(csv_file_path):
                print(f"❌ CSV file not found: {csv_file_path}")
                return False
            
            records_loaded = 0
            
            with open(csv_file_path, "r", encoding="utf-8") as f:
                csv_reader = csv.DictReader(f)
                
                with self.engine.connect() as conn:
                    for row in csv_reader:
                        # Create content by combining question and answer
                        content = f"{row['question']} {row['answer']}"
                        
                        # Prepare record for insertion
                        record = {
                            'content': content,  # Combined for full-text search
                            'question': row['question'],  # Original question
                            'answer': row['answer'],
                            'explanation': row['explanation'],  
                        }
                        
                        # Insert record
                        insert_sql = text("""
                            INSERT INTO k8_qa_pairs_llm 
                            (content, question, answer, explanation)
                            VALUES (:content, :question, :answer, :explanation)
                        """)
                        conn.execute(insert_sql, record)
                        records_loaded += 1
                    
                    conn.commit()
            
            print(f"✅ Successfully loaded {records_loaded} Q&A pairs from CSV")
            return True
            
        except Exception as e:
            print(f"❌ Error loading CSV data: {str(e)}")
            return False
    
    def verify_data(self):
        """Verify the data was loaded correctly"""
        with self.engine.connect() as conn:
            # Check total count
            result = conn.execute(text("SELECT COUNT(*) FROM k8_qa_pairs_llm"))
            total_count = result.scalar()
            
            
            # Show sample records
            
            print(f"📊 Total records loaded: {total_count}")
    def run_complete_setup(self, csv_file_path: str):
        """Run complete setup: create table and load data"""
        print("🚀 Setting up kubernetes_qa_pairs from CSV...")
        
        # Step 1: Create table
        self.create_k8_qa_pairs_table()
        
        # Step 2: Load CSV data
        if self.load_csv_data(csv_file_path):
            # Step 3: Verify data
            self.verify_data()
            print("✅ Knowledge base setup completed successfully!")
            return True
        else:
            print("❌ Knowledge base setup failed!")
            return False

if __name__ == "__main__":
    # Specify your CSV file path
    csv_path = "./kubernetes_qa_pairs.csv"  # Update this path as needed
    
    loader = KnowledgeBaseLoader()
    loader.run_complete_setup(csv_path)