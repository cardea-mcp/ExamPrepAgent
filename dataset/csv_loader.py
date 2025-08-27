import csv
import os
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import pooling
from urllib.parse import urlparse
import time

load_dotenv()

class KnowledgeBaseLoader:
    def __init__(self):
        connection_url = os.getenv("TIDB_CONNECTION")
        parsed = urlparse(connection_url)
        
        self.config = {
            'host': parsed.hostname,
            'port': parsed.port or 4000,
            'user': parsed.username,
            'password': parsed.password,
            'database': parsed.path.lstrip('/'),
            'autocommit': False,
            'charset': 'utf8mb4',
            'use_unicode': True,
            'get_warnings': True,

            # Connection timeout settings
            'connection_timeout': 60,  # 60 seconds to establish connection
            
            # Pool settings
            'pool_name': 'kb_loader_pool',
            'pool_size': 5,
            'pool_reset_session': True,
        }
        
        try:
            self.pool = pooling.MySQLConnectionPool(**self.config)
            self.table_name = os.getenv("TIDB_TABLE_NAME")
            print("✅ TiDB connection pool created successfully for KnowledgeBaseLoader")
        except Exception as e:
            print(f"❌ Failed to create TiDB connection pool: {str(e)}")
            raise e

    def get_connection(self):
        """Get a connection from the pool with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                conn = self.pool.get_connection()
                
                # Test the connection
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                cursor.close()
                
                return conn
            except Exception as e:
                print(f"Connection attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    raise e
                time.sleep(1)  # Wait 1 second before retry
        
        raise Exception("Failed to get database connection after retries")

    def execute_query(self, query, params=None, fetch_type='none'):
        """Execute query with connection retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            conn = None
            cursor = None
            try:
                conn = self.get_connection()
                cursor = conn.cursor(dictionary=True)
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                if fetch_type == 'all':
                    result = cursor.fetchall()
                elif fetch_type == 'one':
                    result = cursor.fetchone()
                elif fetch_type == 'none':
                    result = cursor.rowcount
                else:
                    result = cursor.fetchall()
                
                conn.commit()
                return result
                
            except mysql.connector.Error as e:
                if conn:
                    conn.rollback()
                    
                print(f"Database query attempt {attempt + 1} failed: {str(e)}")
                
                # Check if it's a connection error that we should retry
                if e.errno in [2013, 2006, 2055]:  # Connection lost errors
                    if attempt < max_retries - 1:
                        print(f"Retrying query in 2 seconds...")
                        time.sleep(2)
                        continue
                
                raise e
            except Exception as e:
                if conn:
                    conn.rollback()
                print(f"Unexpected error in query attempt {attempt + 1}: {str(e)}")
                raise e
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
        
        raise Exception("Failed to execute query after retries")
    
    def create_table(self):
        f"""Create {self.table_name} table with larger text fields"""
        try:
            # Drop table if exists
            drop_sql = f"DROP TABLE IF EXISTS {self.table_name}"
            self.execute_query(drop_sql)
            
            # Create table with larger text fields
            create_table_sql = f"""
            CREATE TABLE {self.table_name} (
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                content LONGTEXT NOT NULL,
                question TEXT NOT NULL,
                answer LONGTEXT NOT NULL,
                explanation LONGTEXT NOT NULL,
                FULLTEXT INDEX (content) WITH PARSER MULTILINGUAL
            )
            """
            self.execute_query(create_table_sql)
            print(f"✅ Created {self.table_name} table with large text fields")
            
        except Exception as e:
            print(f"❌ Error creating table: {str(e)}")
            raise e
    
    def load_csv_data(self, csv_file_path: str):
        f"""Load CSV data directly into {self.table_name} table"""
        try:
            if not os.path.exists(csv_file_path):
                print(f"❌ CSV file not found: {csv_file_path}")
                return False
            
            records_loaded = 0
            
            with open(csv_file_path, "r", encoding="utf-8-sig") as f:
                csv_reader = csv.DictReader(f)
                
                insert_sql = f"""
                    INSERT INTO {self.table_name}
                    (content, question, answer, explanation)
                    VALUES (%s, %s, %s, %s)
                """
                batch_size = 100
                batch_data = []
                
                for row in csv_reader:
                    content = f"{row['question']} {row['answer']}"

                    record_data = (
                        content,  # Combined for full-text search
                        row['question'],  # Original question
                        row['answer'],
                        row['explanation']
                    )
                    
                    batch_data.append(record_data)
                    records_loaded += 1
                    
                    if len(batch_data) >= batch_size:
                        self.execute_batch_insert(insert_sql, batch_data)
                        batch_data = []
                
                # Insert remaining records
                if batch_data:
                    self.execute_batch_insert(insert_sql, batch_data)
            
            print(f"✅ Successfully loaded {records_loaded} Q&A pairs from CSV")
            return True
            
        except Exception as e:
            print(f"❌ Error loading CSV data: {str(e)}")
            return False

    def execute_batch_insert(self, query, data_batch):
        """Execute batch insert with connection retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            conn = None
            cursor = None
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                cursor.executemany(query, data_batch)
                conn.commit()
                return
                
            except mysql.connector.Error as e:
                if conn:
                    conn.rollback()
                    
                print(f"Batch insert attempt {attempt + 1} failed: {str(e)}")
                
                # Check if it's a connection error that we should retry
                if e.errno in [2013, 2006, 2055]:  # Connection lost errors
                    if attempt < max_retries - 1:
                        print(f"Retrying batch insert in 2 seconds...")
                        time.sleep(2)
                        continue
                
                raise e
            except Exception as e:
                if conn:
                    conn.rollback()
                print(f"Unexpected error in batch insert attempt {attempt + 1}: {str(e)}")
                raise e
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
        
        raise Exception("Failed to execute batch insert after retries")
    
    def verify_data(self):
        """Verify the data was loaded correctly"""
        try:
            count_sql = f"SELECT COUNT(*) as total FROM {self.table_name}"
            result = self.execute_query(count_sql, fetch_type='one')
            total_count = result['total'] if result else 0
            
            print(f"📊 Total records loaded: {total_count}")
            
            if total_count > 0:
                sample_sql = f"SELECT question, answer FROM {self.table_name} LIMIT 1"
                sample = self.execute_query(sample_sql, fetch_type='one')
                if sample:
                    print(f"📄 Sample record:")
                    print(f"   Question: {sample['question'][:100]}...")
                    print(f"   Answer: {sample['answer'][:100]}...")
            
        except Exception as e:
            print(f"❌ Error verifying data: {str(e)}")
            
    def run_complete_setup(self, csv_file_path: str):
        """Run complete setup: create table and load data"""
        print(f"🚀 Setting up {self.table_name} from CSV...")
        
        try:
            self.create_table()

            if self.load_csv_data(csv_file_path):
                self.verify_data()
                print("✅ Knowledge base setup completed successfully!")
                return True
            else:
                print("❌ Knowledge base setup failed!")
                return False
                
        except Exception as e:
            print(f"❌ Setup failed with error: {str(e)}")
            return False

if __name__ == "__main__":
    csv_path = "./qa.csv" 
    
    try:
        loader = KnowledgeBaseLoader()
        loader.run_complete_setup(csv_path)
    except Exception as e:
        print(f"❌ Failed to initialize KnowledgeBaseLoader: {str(e)}")
