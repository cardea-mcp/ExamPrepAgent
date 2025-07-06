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
    
    def create_kubernetes_qa_pairs_table(self):
        """Create kubernetes_qa_pairs table with larger text fields"""
        with self.engine.connect() as conn:
            # Drop table if exists
            conn.execute(text("DROP TABLE IF EXISTS kubernetes_qa_pairs"))
            
            # Create table with larger text fields
            create_table_sql = """
            CREATE TABLE kubernetes_qa_pairs (
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                title TEXT NOT NULL,
                content LONGTEXT NOT NULL,
                question TEXT NOT NULL,
                answer LONGTEXT NOT NULL,
                topic VARCHAR(500),
                type VARCHAR(100),
                difficulty VARCHAR(50),
                FULLTEXT INDEX (content) WITH PARSER MULTILINGUAL,
                INDEX idx_difficulty (difficulty),
                INDEX idx_type (type),
                INDEX idx_topic (topic)
            )
            """
            conn.execute(text(create_table_sql))
            conn.commit()
            print("✅ Created kubernetes_qa_pairs table with large text fields")
    
    def load_csv_data(self, csv_file_path: str):
        """Load CSV data directly into kubernetes_qa_pairs table"""
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
                            'title': row['topic'] or 'General',  # Use topic as title metadata
                            'content': content,  # Combined for full-text search
                            'question': row['question'],  # Original question
                            'answer': row['answer'],  # Original answer
                            'topic': row['topic'],
                            'type': row['type'],
                            'difficulty': row['difficulty'].lower()  # Normalize difficulty
                        }
                        
                        # Insert record
                        insert_sql = text("""
                            INSERT INTO kubernetes_qa_pairs 
                            (title, content, question, answer, topic, type, difficulty)
                            VALUES (:title, :content, :question, :answer, :topic, :type, :difficulty)
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
            result = conn.execute(text("SELECT COUNT(*) FROM kubernetes_qa_pairs"))
            total_count = result.scalar()
            
            # Check difficulty distribution
            difficulty_result = conn.execute(text("""
                SELECT difficulty, COUNT(*) as count 
                FROM kubernetes_qa_pairs 
                GROUP BY difficulty
            """))
            
            # Show sample records
            sample_result = conn.execute(text("""
                SELECT id, title, topic, difficulty
                FROM kubernetes_qa_pairs 
                LIMIT 5
            """))
            
            print(f"📊 Total records loaded: {total_count}")
            print("📊 Difficulty distribution:")
            for row in difficulty_result:
                print(f"  - {row[0]}: {row[1]} questions")
            
            print("📋 Sample records:")
            for row in sample_result:
                print(f"  ID: {row[0]}, Title: {row[1]}, Topic: {row[2]}, Difficulty: {row[3]}")
    def run_complete_setup(self, csv_file_path: str):
        """Run complete setup: create table and load data"""
        print("🚀 Setting up kubernetes_qa_pairs from CSV...")
        
        # Step 1: Create table
        self.create_kubernetes_qa_pairs_table()
        
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
    csv_path = "/home/kayden/Desktop/python_projects/ExamPrepAgent/dataset/kubernetes_qa.csv"  # Update this path as needed
    
    loader = KnowledgeBaseLoader()
    loader.run_complete_setup(csv_path)