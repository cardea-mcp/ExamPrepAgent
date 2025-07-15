import os
import random
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from pytidb import TiDBClient
from pytidb.schema import TableModel, Field

load_dotenv()

class QAPair(TableModel, table=True):
    __tablename__ = "kubernetes_qa_pairs"
    
    id: int = Field(primary_key=True)
    question: str = Field(max_length=2000)  
    answer: str = Field(max_length=15000) 
    topic: str = Field(max_length=500)
    type: str = Field(max_length=100)
    difficulty: str = Field(max_length=50)

class TiDBConnection:
    def __init__(self):
        self.db = None
        self.table = None
        self.connect()
    
    def connect(self):
        """Connect to TiDB Cloud and initialize QAPair table if not exists"""
        try:
            self.db = TiDBClient.connect(
                host=os.getenv("TIDB_HOST"),
                port=int(os.getenv("TIDB_PORT", 4000)),
                username=os.getenv("TIDB_USERNAME"),
                password=os.getenv("TIDB_PASSWORD"),
                database=os.getenv("TIDB_DATABASE"),
            )

            table_name = QAPair.__tablename__
            if not self.db.has_table(table_name):
                print(f"🛠️ Table '{table_name}' does not exist. Creating it now...")
                self.table = self.db.create_table(schema=QAPair)
            else:
                print(f"📦 Table '{table_name}' exists. Opening it.")
                self.table = self.db.open_table(table_name)

            # Create FTS indexes only if needed
            if not self.table.has_fts_index("question"):
                self.table.create_fts_index("question")
            if not self.table.has_fts_index("answer"):
                self.table.create_fts_index("answer")

            print("✅ Connected to TiDB successfully!")

        except Exception as e:
            print(f"❌ Failed to connect to TiDB: {str(e)}")
            raise e

    


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
            
            # Search in questions
            try:
                question_results = (
                    self.table
                    .search(topic, search_type="fulltext")
                    .text_column("question")
                    .limit(5)
                    .to_list()
                )
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
                answer_results = (
                    self.table
                    .search(topic, search_type="fulltext")
                    .text_column("answer")
                    .limit(5)
                    .to_list()
                )
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
                filters = {}
                if difficulty:
                    filters['difficulty'] = difficulty.lower()
                
                results = self.table.query(filters=filters)
                
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
        Search for relevant Q&A pairs using full-text search on both questions and answers
        
        Parameters:
        query_text (str): Search query
        limit (int): Maximum number of results to return
        
        Returns:
        list: List of matching Q&A pairs with relevance scores
        """
        try:
            results_dict = {}
            
            print(f"🔍 Searching in questions for: '{query_text}'")
            try:
                question_results = (
                    self.table
                    .search(query_text, search_type="fulltext")
                    .text_column("question")
                    .limit(limit)
                    .to_list()
                )
                
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
                answer_results = (
                    self.table
                    .search(query_text, search_type="fulltext")
                    .text_column("answer")
                    .limit(limit)
                    .to_list()
                )
                
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
    
    def insert_qa_pair(self, question: str, answer: str, topic: str, qa_type: str, difficulty: str) -> bool:
        """
        Insert a new Q&A pair into the database
        
        Parameters:
        question (str): The question text
        answer (str): The answer text
        topic (str): The topic/category
        qa_type (str): Type of question
        difficulty (str): Difficulty level
        
        Returns:
        bool: True if successful, False otherwise
        """
        try:
            qa_pair = QAPair(
                question=question,
                answer=answer,
                topic=topic,
                type=qa_type,
                difficulty=difficulty
            )
            
            result = self.table.insert(qa_pair)
            print(f"✅ Inserted Q&A pair with ID: {result.id}")
            return True
            
        except Exception as e:
            print(f"❌ Error inserting Q&A pair: {str(e)}")
            return False
    
    def bulk_insert_qa_pairs(self, qa_pairs_list: List[Dict[str, str]]) -> bool:
        """
        Insert multiple Q&A pairs in bulk
        
        Parameters:
        qa_pairs_list (List[Dict]): List of Q&A pair dictionaries
        
        Returns:
        bool: True if successful, False otherwise
        """
        try:
            qa_objects = []
            for qa_data in qa_pairs_list:
                qa_pair = QAPair(
                    question=qa_data['question'],
                    answer=qa_data['answer'],
                    topic=qa_data['topic'],
                    type=qa_data['type'],
                    difficulty=qa_data['difficulty']
                )
                qa_objects.append(qa_pair)
            
            results = self.table.bulk_insert(qa_objects)
            print(f"✅ Bulk inserted {len(results)} Q&A pairs")
            return True
            
        except Exception as e:
            print(f"❌ Error in bulk insert: {str(e)}")
            return False

tidb_client = TiDBConnection()