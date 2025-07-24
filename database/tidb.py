import os
import random
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from datetime import datetime
import logging
import uuid
import mysql.connector
import json
from urllib.parse import urlparse

load_dotenv()

class TiDBConnection:
    def __init__(self):
        connection_url = os.getenv("TIDB_CONNECTION")

        parsed = urlparse(connection_url)
        
        self.conn = mysql.connector.connect(
            host=parsed.hostname,
            port=parsed.port or 4000,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path.lstrip('/'),
            autocommit=False
        )

       
        self.cursor = self.conn.cursor(dictionary=True)
        self.users_table = "users"
        self.sessions_table = 'chat_sessions'
        self.qa_table = 'kubernetes_qa_pairs'

    def get_random_qa(self, difficulty: Optional[str] = None, topic: Optional[str] = None) -> list[dict[str,Any]]:
        # List of 30 Kubernetes topics
        KUBERNETES_TOPICS = [
            "pods",
            "services", 
            "deployments",
            "replicasets",
            "statefulsets",
            "daemonsets",
            "jobs",
            "cronjobs",
            "namespaces",
            "configmaps",
            "secrets",
            "persistent volumes",
            "persistent volume claims",
            "storage classes",
            "ingress",
            "network policies",
            "service accounts",
            "rbac",
            "cluster roles",
            "role bindings",
            "labels and selectors",
            "annotations",
            "taints and tolerations",
            "node affinity",
            "pod affinity",
            "horizontal pod autoscaler",
            "vertical pod autoscaler",
            "resource quotas",
            "limit ranges",
            "custom resource definitions"
        ]
        
        try:
            results_dict = {}
            
            # If no topic is specified, randomly select one from the predefined list
            if not topic:
                topic = random.choice(KUBERNETES_TOPICS)
                print(f"🎲 No topic specified, randomly selected: '{topic}'")
            
            # Now proceed with topic-based search (topic is guaranteed to exist)
            print(f"🔍 Full-text searching for topic: '{topic}'")
            
            # Search in questions using TiDB full-text search
            try:
                question_search_sql = """
                SELECT id, question, answer, topic, type, difficulty,
                    fts_match_word(%s, question) as _score
                FROM kubernetes_qa_pairs 
                WHERE fts_match_word(%s, question)
                ORDER BY _score DESC 
                LIMIT 5
                """
                self.cursor.execute(question_search_sql, (topic, topic))
                question_results = self.cursor.fetchall()
                
                print("question results -------\n", question_results)
                for result in question_results:
                    results_dict[result['id']] = {
                        "id": result['id'],
                        "question": result['question'],
                        "answer": result['answer'],
                        "topic": result['topic'],
                        "type": result['type'],
                        "difficulty": result['difficulty'],
                        "score": result.get('_score', 1.0),
                        "match_type": "question"
                    }
                print(f"✅ Found {len(question_results)} results in questions")
                
            except Exception as e:
                print(f"⚠️ Question search failed: {str(e)}")
            
            try:
                answer_search_sql = """
                SELECT id, question, answer, topic, type, difficulty,
                    fts_match_word(%s, answer) as _score
                FROM kubernetes_qa_pairs 
                WHERE fts_match_word(%s, answer)
                ORDER BY _score DESC 
                LIMIT 5
                """
                self.cursor.execute(answer_search_sql, (topic, topic))
                answer_results = self.cursor.fetchall()
                
                print("answer results ------ \n", answer_results)
                for result in answer_results:
                    if result['id'] not in results_dict:
                        results_dict[result['id']] = {
                            "id": result['id'],
                            "question": result['question'],
                            "answer": result['answer'],
                            "topic": result['topic'],
                            "type": result['type'],
                            "difficulty": result['difficulty'],
                            "score": result.get('_score', 0.8),
                            "match_type": "answer"
                        }
                    else:
                        results_dict[result['id']]['match_type'] = "both"
                        results_dict[result['id']]['score'] = max(
                            results_dict[result['id']]['score'], 
                            result.get('_score', 0.8)
                        ) + 0.2
                
                print(f"✅ Found {len(answer_results)} results in answers")
                
            except Exception as e:
                print(f"⚠️ Answer search failed: {str(e)}")
            
            qa_list = list(results_dict.values())
            qa_list.sort(key=lambda x: x['score'], reverse=True)
            qa_list = qa_list[:5]
            
            # If no results found from topic search, fall back to regular query
            if not qa_list:
                print(f"❌ No results found for topic '{topic}', falling back to regular query")
                
                fallback_sql = "SELECT id, question, answer, topic, type, difficulty FROM kubernetes_qa_pairs"
                params = []
                
                if difficulty:
                    fallback_sql += " WHERE difficulty = %s"
                    params.append(difficulty.lower())
                
                self.cursor.execute(fallback_sql, params)
                results = self.cursor.fetchall()
                
                if not results:
                    return None

                qa_list = []
                for result in results:
                    qa_dict = {
                        "id": result['id'],
                        "question": result['question'],
                        "answer": result['answer'],
                        "topic": result['topic'],
                        "type": result['type'],
                        "difficulty": result['difficulty'],
                        "score": 1.0, 
                        "match_type": "query"
                    }
                    qa_list.append(qa_dict)
            
            # Apply difficulty filter if specified
            if difficulty and qa_list:
                qa_list = [qa for qa in qa_list if qa['difficulty'].lower() == difficulty.lower()]
            
            if not qa_list:
                print("❌ No results found matching the criteria")
                return None
            
            print(f"🎲 Selecting random from {len(qa_list)} results")
            
            selected_qa = random.choice(qa_list)
            
            print(f"✅ Selected Q&A: ID={selected_qa['id']}, Score={selected_qa['score']}, Match Type={selected_qa['match_type']}")
            print("type of result", type(selected_qa['question']))
            print("selected_qa ----\n", selected_qa['question'])
            question_answer_chosen = []
            question_dict = {
                "question":selected_qa['question'],
                "answer": selected_qa['answer']
            }
            question_answer_chosen.append(question_dict)
            return question_answer_chosen
            
        except Exception as e:
            print(f"❌ Error in get_random_qa: {str(e)}")
            return None
            
    def search_pair(self, query_text: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Search for relevant Q&A pairs using TiDB full-text search on both questions and answers
        """
        try:
            results_dict = {}
            
            print(f"🔍 Searching in questions for: '{query_text}'")
            try:
                question_search_sql = """
                SELECT id, question, answer, topic, type, difficulty,
                    fts_match_word(%s, question) as _score
                FROM kubernetes_qa_pairs 
                WHERE fts_match_word(%s, question)
                ORDER BY _score DESC 
                LIMIT %s
                """
                self.cursor.execute(question_search_sql, (query_text, query_text, limit))
                question_results = self.cursor.fetchall()
                
                print("question_results--------\n", question_results)
                
                for result in question_results:
                    results_dict[result['id']] = {
                        "question": result['question'],
                        "answer": result['answer'],
                        "topic": result['topic'],
                        "type": result['type'],
                        "difficulty": result['difficulty'],
                        "score": result.get('_score', 1.0), 
                        "match_type": "question"
                    }
                print(f"✅ Found {len(question_results)} results in questions")
                
            except Exception as e:
                print(f"⚠️ Question search failed: {str(e)}")
            
            print(f"🔍 Searching in answers for: '{query_text}'")
            try:
                answer_search_sql = """
                SELECT id, question, answer, topic, type, difficulty,
                    fts_match_word(%s, answer) as _score
                FROM kubernetes_qa_pairs 
                WHERE fts_match_word(%s, answer)
                ORDER BY _score DESC 
                LIMIT %s
                """
                self.cursor.execute(answer_search_sql, (query_text, query_text, limit))
                answer_results = self.cursor.fetchall()
                
                print("answer_results--------\n", answer_results)
                
                for result in answer_results:
                    if result['id'] not in results_dict:
                        results_dict[result['id']] = {
                            "question": result['question'],
                            "answer": result['answer'],
                            "topic": result['topic'],
                            "type": result['type'],
                            "difficulty": result['difficulty'],
                            "score": result.get('_score', 0.8), 
                            "match_type": "answer"
                        }
                    else:
                        results_dict[result['id']]['match_type'] = "both"
                        results_dict[result['id']]['score'] = max(
                            results_dict[result['id']]['score'], 
                            result.get('_score', 0.8)
                        ) + 0.2
                
                print(f"✅ Found {len(answer_results)} results in answers")
                
            except Exception as e:
                print(f"⚠️ Answer search failed: {str(e)}")
            
            qa_list = list(results_dict.values())
            qa_list.sort(key=lambda x: x['score'], reverse=True)
            
            qa_list = qa_list[:limit]
            
            print(f"📋 Returning {len(qa_list)} total results")
            return qa_list
            
        except Exception as e:
            print(f"❌ Error in search_pair: {str(e)}")
            return []
    
    def create_user(self, user_name: str) -> str:
        """Create a new user or get existing user"""
        logger = logging.getLogger(__name__)
        try:
            # Check if user already exists
            check_sql = "SELECT id FROM users WHERE name = %s"
            self.cursor.execute(check_sql, (user_name,))
            existing_user = self.cursor.fetchone()
            
            if existing_user:
                return existing_user['id']
            
            logger.info(f"existing users {existing_user}")
            # Create new user
            user_id = str(uuid.uuid4())
            logger.info(f" user id {user_id}")
            
            insert_sql = "INSERT INTO users (id, name, created_at) VALUES (%s, %s, %s)"
            self.cursor.execute(insert_sql, (user_id, user_name, datetime.utcnow()))
            self.conn.commit()
            
            return user_id
            
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Error creating user: {str(e)}")
            raise e
    
    def create_session(self, user_id: str, session_name: Optional[str] = None) -> str:
        """Create a new chat session for a user"""
        try:
            session_id = str(uuid.uuid4())
            
            if not session_name:
                session_name = f"Chat {datetime.utcnow().strftime('%m/%d %H:%M')}"
            
            insert_sql = """
            INSERT INTO chat_sessions (id, user_id, session_name, context, created_at, updated_at) 
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            now = datetime.utcnow()
            self.cursor.execute(insert_sql, (session_id, user_id, session_name, "[]", now, now))
            self.conn.commit()
            
            return session_id
            
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Error creating session: {str(e)}")
            raise e
    
    def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all sessions for a user"""
        try:
            select_sql = """
            SELECT id, session_name, created_at, updated_at 
            FROM chat_sessions 
            WHERE user_id = %s 
            ORDER BY updated_at DESC
            """
            self.cursor.execute(select_sql, (user_id,))
            sessions = self.cursor.fetchall()
            
            # Convert to dict format and sort by updated_at desc
            sessions_list = []
            for session in sessions:
                sessions_list.append({
                    '_id': session['id'],
                    'session_name': session['session_name'],
                    'created_at': session['created_at'].isoformat(),
                    'updated_at': session['updated_at'].isoformat()
                })
            
            return sessions_list
            
        except Exception as e:
            print(f"❌ Error loading sessions: {str(e)}")
            return []
    
    def get_session_context(self, session_id: str) -> List[Dict[str, Any]]:
        """Retrieve session context from TiDB"""
        try:
            select_sql = "SELECT context FROM chat_sessions WHERE id = %s"
            self.cursor.execute(select_sql, (session_id,))
            result = self.cursor.fetchone()
            
            if result and result['context']:
                return json.loads(result['context'])
            else:
                return []
                
        except Exception as e:
            print(f"❌ Error getting session context: {str(e)}")
            return []
    
    def update_session_context(self, session_id: str, context: List[Dict[str, Any]]) -> bool:
        """Update session context in TiDB"""
        try:
            context_json = json.dumps(context)
            
            update_sql = """
            UPDATE chat_sessions 
            SET context = %s, updated_at = %s 
            WHERE id = %s
            """
            self.cursor.execute(update_sql, (context_json, datetime.utcnow(), session_id))
            self.conn.commit()
            
            return True
            
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Error updating session context: {str(e)}")
            return False
    
    def get_user_by_name(self, user_name: str) -> Optional[Dict[str, Any]]:
        """Get user by name"""
        try:
            select_sql = "SELECT id, name, created_at FROM users WHERE name = %s"
            self.cursor.execute(select_sql, (user_name,))
            result = self.cursor.fetchone()
            
            if result:
                return {
                    '_id': result['id'],
                    'name': result['name'],
                    'created_at': result['created_at'].isoformat()
                }
            return None
            
        except Exception as e:
            print(f"❌ Error getting user by name: {str(e)}")
            return None
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        try:
            delete_sql = "DELETE FROM chat_sessions WHERE id = %s"
            self.cursor.execute(delete_sql, (session_id,))
            self.conn.commit()
            
            return self.cursor.rowcount > 0
            
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Error deleting session: {str(e)}")
            return False
    
    def update_session_name(self, session_id: str, new_name: str) -> bool:
        """Update session name"""
        try:
            update_sql = """
            UPDATE chat_sessions 
            SET session_name = %s, updated_at = %s 
            WHERE id = %s
            """
            self.cursor.execute(update_sql, (new_name, datetime.utcnow(), session_id))
            self.conn.commit()
            
            return self.cursor.rowcount > 0
            
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Error updating session name: {str(e)}")
            return False

tidb_client = TiDBConnection()