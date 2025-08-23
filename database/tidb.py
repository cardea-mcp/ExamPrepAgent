import os
import random
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from datetime import datetime
import logging
import uuid
import mysql.connector
from mysql.connector import pooling
from urllib.parse import urlparse
import time

load_dotenv()

class TiDBConnection:
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
            'autocommit': False,  
            
            # Pool settings
            'pool_name': 'tidb_pool',
            'pool_size': 5,
            'pool_reset_session': True,
        }
        
        try:
            self.pool = pooling.MySQLConnectionPool(**self.config)
            self.qa_table = 'k8_qa_pairs_llm'
            print("✅ TiDB connection pool created successfully")
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

    def execute_query(self, query, params=None, fetch_type='all'):
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

    def get_random_qa(self, topic: Optional[str] = None) -> list[dict[str,Any]]:
        try:
            if topic:
                print(f"🔍 Full-text searching content for topic: '{topic}'")
                
                search_sql = """
                SELECT id, question, answer,
                    fts_match_word(%s, content) as _score
                FROM k8_qa_pairs_llm 
                WHERE fts_match_word(%s, content)
                ORDER BY _score DESC 
                LIMIT 3
                """
                
                results = self.execute_query(search_sql, [topic, topic])
                
                if not results:
                    print("❌ No results found for the specified topic")
                    return None
                
                print(f"✅ Found {len(results)} results")
                
                # Select random from top 3 results
                selected_qa = random.choice(results)
                
            else:
                print("🎲 No topic specified, randomly selecting from all questions")
                
                random_sql = """
                SELECT id, question, answer,explanation
                FROM k8_qa_pairs_llm 
                ORDER BY RAND()
                LIMIT 1
                """
                
                results = self.execute_query(random_sql)
                
                if not results:
                    print("❌ No questions found in database")
                    return None
                
                selected_qa = results[0]
                print(f"✅ Randomly selected question from database")
            
            question_answer_chosen = [{
                "question": selected_qa['question'],
                "answer": selected_qa['answer'],
                "explanation": selected_qa['explanation']
            }]
            
            return question_answer_chosen
            
        except Exception as e:
            print(f"❌ Error in get_random_qa: {str(e)}")
            return None

    def search_pair(self, query_text: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Search for relevant Q&A pairs using TiDB full-text search on content field
        """
        try:
            print(f"🔍 Searching content for: '{query_text}'")
            
            search_sql = """
            SELECT id, question, answer,
                fts_match_word(%s, content) as _score
            FROM k8_qa_pairs_llm 
            WHERE fts_match_word(%s, content)
            ORDER BY _score DESC 
            LIMIT %s
            """
            
            results = self.execute_query(search_sql, (query_text, query_text, limit))
            
            qa_list = []
            for result in results:
                qa_dict = {
                    "question": result['question'],
                    "answer": result['answer'],
                    "explanation": result['explanation']
                }
                qa_list.append(qa_dict)
            
            print(f"📋 Returning {len(qa_list)} results")
            return qa_list
            
        except Exception as e:
            print(f"❌ Error in search_pair: {str(e)}")
            return []


    def create_user(self, user_name: str) -> str:
        """Create a new user or get existing user"""
        logger = logging.getLogger(__name__)
        try:
            check_sql = "SELECT id FROM users WHERE name = %s"
            existing_user = self.execute_query(check_sql, (user_name,), 'one')
            
            if existing_user:
                return existing_user['id']
            
            # Create new user
            user_id = str(uuid.uuid4())
            
            insert_sql = "INSERT INTO users (id, name, created_at) VALUES (%s, %s, %s)"
            self.execute_query(insert_sql, (user_id, user_name, datetime.utcnow()), 'none')
            
            return user_id
            
        except Exception as e:
            print(f"❌ Error creating user: {str(e)}")
            raise e



tidb_client = TiDBConnection()
