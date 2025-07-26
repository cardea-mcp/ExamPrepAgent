import csv
import os
from dotenv import load_dotenv
import mysql.connector
from urllib.parse import urlparse

load_dotenv()

class KnowledgeBaseLoader:
    def __init__(self):

        connection_url = os.getenv("TIDB_CONNECTION")
        
        if not connection_url:
            raise ValueError("TIDB_CONNECTION environment variable not found")
        
        parsed = urlparse(connection_url)
        
        try:
            self.conn = mysql.connector.connect(
                host=parsed.hostname,
                port=parsed.port or 4000,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path.lstrip('/'),
            )
            self.cursor = self.conn.cursor(dictionary=True)
            print("✅ Connected to TiDB successfully!")
        except mysql.connector.Error as e:
            print(f"❌ Failed to connect to TiDB: {str(e)}")
            raise e
    
    def create_kubernetes_qa_pairs_table(self):
        """Create kubernetes_qa_pairs table with larger text fields"""
        try:
            # Drop table if exists
            self.cursor.execute("DROP TABLE IF EXISTS kubernetes_qa_pairs")
            
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
            self.cursor.execute(create_table_sql)
            self.conn.commit()
            print("✅ Created kubernetes_qa_pairs table with large text fields")
        except mysql.connector.Error as e:
            print(f"❌ Error creating table: {str(e)}")
            self.conn.rollback()
            raise e
    
    def load_csv_data(self, csv_file_path: str):
        """Load CSV data directly into kubernetes_qa_pairs table"""
        try:
            if not os.path.exists(csv_file_path):
                print(f"❌ CSV file not found: {csv_file_path}")
                return False
            
            records_loaded = 0
            
            with open(csv_file_path, "r", encoding="utf-8") as f:
                csv_reader = csv.DictReader(f)
                
                # Prepare the insert statement
                insert_sql = """
                    INSERT INTO kubernetes_qa_pairs 
                    (title, content, question, answer, topic, type, difficulty)
                    VALUES (%(title)s, %(content)s, %(question)s, %(answer)s, %(topic)s, %(type)s, %(difficulty)s)
                """
                
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
                    self.cursor.execute(insert_sql, record)
                    records_loaded += 1
                
                # Commit all insertions
                self.conn.commit()
            
            print(f"✅ Successfully loaded {records_loaded} Q&A pairs from CSV")
            return True
            
        except mysql.connector.Error as e:
            print(f"❌ Database error loading CSV data: {str(e)}")
            self.conn.rollback()
            return False
        except Exception as e:
            print(f"❌ Error loading CSV data: {str(e)}")
            self.conn.rollback()
            return False
    
    def verify_data(self):
        """Verify the data was loaded correctly"""
        try:
            # Check total count
            self.cursor.execute("SELECT COUNT(*) as total FROM kubernetes_qa_pairs")
            result = self.cursor.fetchone()
            total_count = result['total'] if result else 0
            
            # Check difficulty distribution
            self.cursor.execute("""
                SELECT difficulty, COUNT(*) as count 
                FROM kubernetes_qa_pairs 
                GROUP BY difficulty
            """)
            difficulty_results = self.cursor.fetchall()
            
            # Show sample records
            self.cursor.execute("""
                SELECT id, title, topic, difficulty
                FROM kubernetes_qa_pairs 
                LIMIT 5
            """)
            sample_results = self.cursor.fetchall()
            
            print(f"📊 Total records loaded: {total_count}")
            print("📊 Difficulty distribution:")
            for row in difficulty_results:
                print(f"  - {row['difficulty']}: {row['count']} questions")
            
            print("📋 Sample records:")
            for row in sample_results:
                print(f"  ID: {row['id']}, Title: {row['title']}, Topic: {row['topic']}, Difficulty: {row['difficulty']}")
                
        except mysql.connector.Error as e:
            print(f"❌ Error verifying data: {str(e)}")
    
    def run_complete_setup(self, csv_file_path: str):
        """Run complete setup: create table and load data"""
        print("🚀 Setting up kubernetes_qa_pairs from CSV...")
        
        try:
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
        except Exception as e:
            print(f"❌ Setup failed with error: {str(e)}")
            return False
        finally:
            self.close_connection()
    
    def close_connection(self):
        """Close database connection"""
        try:
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()
            print("✅ Database connection closed")
        except Exception as e:
            print(f"⚠️ Error closing connection: {str(e)}")

if __name__ == "__main__":
    # Specify your CSV file path
    csv_path = "./kubernetes_qa_pairs.csv"  # Update this path as needed
    
    try:
        loader = KnowledgeBaseLoader()
        loader.run_complete_setup(csv_path)
    except Exception as e:
        print(f"❌ Failed to run setup: {str(e)}")