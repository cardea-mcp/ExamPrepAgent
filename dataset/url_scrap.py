#!/usr/bin/env python3
"""
URL Scraper and Q&A Generator using Gemini
Scrapes content from a URL and generates 30 Kubernetes-related Q&A pairs
"""

import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import json
import time
import os
from urllib.parse import urlparse
import argparse
from typing import List, Dict, Optional
from dotenv import load_dotenv
load_dotenv()
class URLScraper:
    """Handles web scraping with proper error handling and content extraction"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def scrape_url(self, url: str) -> Dict[str, str]:
        """
        Scrape content from a given URL
        
        Args:
            url (str): URL to scrape
            
        Returns:
            Dict containing title, content, and metadata
        """
        try:
            print(f"Scraping URL: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Extract title
            title = soup.find('title')
            title_text = title.get_text().strip() if title else "No title found"
            
            # Extract main content - try multiple selectors
            content_selectors = [
                'main', 
                'article', 
                '.content', 
                '#content',
                '.post-content',
                '.entry-content',
                'body'
            ]
            
            content_text = ""
            for selector in content_selectors:
                content_element = soup.select_one(selector)
                if content_element:
                    content_text = content_element.get_text(separator='\n', strip=True)
                    break
            
            if not content_text:
                content_text = soup.get_text(separator='\n', strip=True)
            
            # Clean and limit content length
            content_lines = [line.strip() for line in content_text.split('\n') if line.strip()]
            content_text = '\n'.join(content_lines)
            
            # Limit content to ~8000 characters to avoid token limits
            if len(content_text) > 8000:
                content_text = content_text[:8000] + "..."
            
            return {
                'url': url,
                'title': title_text,
                'content': content_text,
                'domain': urlparse(url).netloc,
                'length': len(content_text)
            }
            
        except requests.RequestException as e:
            raise Exception(f"Error scraping URL {url}: {str(e)}")
        except Exception as e:
            raise Exception(f"Error processing content from {url}: {str(e)}")

class GeminiQAGenerator:
    """Handles Gemini API interaction for Q&A generation"""
    
    def __init__(self, api_key: str):
        """
        Initialize Gemini client
        
        Args:
            api_key (str): Google AI API key
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def generate_qa_pairs(self, content_data: Dict[str, str]) -> List[Dict[str, str]]:
        """
        Generate 30 Q&A pairs from scraped content
        
        Args:
            content_data (Dict): Scraped content with title, content, etc.
            
        Returns:
            List of Q&A dictionaries
        """
        prompt = self._create_prompt(content_data)
        
        try:
            print("Generating Q&A pairs with Gemini...")
            response = self.model.generate_content(prompt)
            
            if not response.text:
                raise Exception("Empty response from Gemini")
            
            qa_pairs = self._parse_gemini_response(response.text, content_data)
            
            print(f"Generated {len(qa_pairs)} Q&A pairs")
            return qa_pairs
            
        except Exception as e:
            raise Exception(f"Error generating Q&A pairs: {str(e)}")
    
    def _create_prompt(self, content_data: Dict[str, str]) -> str:
        """Create the prompt for Gemini"""
        return f'''
Based on the following content about Kubernetes/Cloud Native technologies, generate exactly 30 high-quality question and answer pairs suitable for KCNA (Kubernetes and Cloud Native Associate) certification preparation.

Source Information:
- Title: {content_data['title']}
- URL: {content_data['url']}
- Domain: {content_data['domain']}

Content:
{content_data['content']}

Requirements:
1. Generate exactly 30 question-answer pairs
2. Questions should cover different difficulty levels (beginner, intermediate, advanced)
3. Focus on Kubernetes and cloud native concepts
4. Include practical scenarios and theoretical knowledge
5. Ensure answers are accurate and educational
6. Cover various topics like: pods, services, deployments, namespaces, RBAC, networking, storage, etc.

Format your response as a JSON array with this exact structure:
[
  {{
    "question": "What is a Kubernetes Pod?",
    "answer": "A Pod is the smallest deployable unit in Kubernetes that contains one or more containers...",
    "difficulty": "beginner",
    "topic": "workloads",
    "question_type": "conceptual"
  }},
  {{
    "question": "How do you scale a deployment in Kubernetes?",
    "answer": "You can scale a deployment using kubectl scale command...",
    "difficulty": "intermediate", 
    "topic": "operations",
    "question_type": "practical"
  }}
]

Important: 
- Return ONLY the JSON array, no additional text
- Ensure valid JSON format
- Generate exactly 30 pairs
- Make questions educational and relevant to KCNA certification
- Base content on the provided source material but ensure originality
'''

    def _parse_gemini_response(self, response_text: str, content_data: Dict[str, str]) -> List[Dict[str, str]]:
        """Parse Gemini response and add metadata"""
        try:
            # Clean response text
            response_text = response_text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            # Parse JSON
            qa_pairs = json.loads(response_text)
            
            if not isinstance(qa_pairs, list):
                raise ValueError("Response is not a list")
            
            # Add metadata to each Q&A pair
            for i, qa in enumerate(qa_pairs):
                qa['id'] = i + 1
                qa['source_url'] = content_data['url']
                qa['source_title'] = content_data['title']
                qa['source_domain'] = content_data['domain']
                qa['generated_date'] = time.strftime('%Y-%m-%d')
                
                # Ensure required fields
                if 'difficulty' not in qa:
                    qa['difficulty'] = 'intermediate'
                if 'topic' not in qa:
                    qa['topic'] = 'general'
                if 'question_type' not in qa:
                    qa['question_type'] = 'conceptual'
            
            return qa_pairs
            
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response from Gemini: {str(e)}")
        except Exception as e:
            raise Exception(f"Error parsing Gemini response: {str(e)}")

class QAFileWriter:
    """Handles writing Q&A pairs to files"""
    
    @staticmethod
    def write_to_file(qa_pairs: List[Dict[str, str]], filename: str = "kubernetes_basic.txt"):
        """
        Write Q&A pairs to a text file
        
        Args:
            qa_pairs (List): List of Q&A dictionaries
            filename (str): Output filename
        """
        try:
            print(f"Writing {len(qa_pairs)} Q&A pairs to {filename}")
            
            with open(filename, 'a', encoding='utf-8') as f:
                f.write("KUBERNETES AND CLOUD NATIVE Q&A PAIRS\n")
                f.write("=" * 50 + "\n\n")
                
                if qa_pairs:
                    f.write(f"Source: {qa_pairs[0]['source_title']}\n")
                    f.write(f"URL: {qa_pairs[0]['source_url']}\n")
                    f.write(f"Generated: {qa_pairs[0]['generated_date']}\n")
                    f.write(f"Total Questions: {len(qa_pairs)}\n\n")
                
                for i, qa in enumerate(qa_pairs, 1):
                    f.write(f"Q{i}: {qa['question']}\n")
                    f.write(f"A{i}: {qa['answer']}\n")
                    f.write(f"Difficulty: {qa.get('difficulty', 'N/A')}\n")
                    f.write(f"Topic: {qa.get('topic', 'N/A')}\n")
                    f.write(f"Type: {qa.get('question_type', 'N/A')}\n")
                    f.write("-" * 50 + "\n\n")
            
            print(f"Successfully wrote Q&A pairs to {filename}")
                    
        except Exception as e:
            raise Exception(f"Error writing to file {filename}: {str(e)}")
    
    @staticmethod
    def write_to_json(qa_pairs: List[Dict[str, str]], filename: str = "kubernetes_basic.json"):
        """Write Q&A pairs to JSON file for database import"""
        try:
            json_filename = filename.replace('.txt', '.json')
            
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(qa_pairs, f, indent=2, ensure_ascii=False)
            
            print(f"Also saved as JSON: {json_filename}")
            
        except Exception as e:
            print(f"Warning: Could not save JSON file: {str(e)}")

def main():
    """Main function to orchestrate the scraping and Q&A generation"""
    parser = argparse.ArgumentParser(description='Generate Kubernetes Q&A pairs from URL content')
    parser.add_argument('url', help='URL to scrape for content')
    parser.add_argument('--api-key', help='Google AI API key (or set GOOGLE_AI_API_KEY env var)')
    parser.add_argument('--output', default='kubernetes_basic.txt', help='Output filename')
    
    args = parser.parse_args()
    
    # Get API key
    api_key = args.api_key or os.getenv('GOOGLE_AI_API_KEY')
    if not api_key:
        print("Error: Google AI API key is required.")
        print("Either pass --api-key or set GOOGLE_AI_API_KEY environment variable")
        return 1
    
    try:
        # Initialize components
        scraper = URLScraper()
        generator = GeminiQAGenerator(api_key)
        writer = QAFileWriter()
        
        # Step 1: Scrape URL
        print("Step 1: Scraping URL content...")
        content_data = scraper.scrape_url(args.url)
        print(f"Scraped {content_data['length']} characters from {content_data['domain']}")
        
        # Step 2: Generate Q&A pairs
        print("\nStep 2: Generating Q&A pairs...")
        qa_pairs = generator.generate_qa_pairs(content_data)
        
        if len(qa_pairs) != 30:
            print(f"Warning: Generated {len(qa_pairs)} pairs instead of 30")
        
        # Step 3: Write to file
        print(f"\nStep 3: Writing to {args.output}...")
        writer.write_to_file(qa_pairs, args.output)
        writer.write_to_json(qa_pairs, args.output)
        
        print(f"\n✅ Successfully generated {len(qa_pairs)} Q&A pairs!")
        print(f"📁 Output saved to: {args.output}")
        
        # Summary
        difficulty_counts = {}
        topic_counts = {}
        
        for qa in qa_pairs:
            diff = qa.get('difficulty', 'unknown')
            topic = qa.get('topic', 'unknown')
            difficulty_counts[diff] = difficulty_counts.get(diff, 0) + 1
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        print(f"\n📊 Summary:")
        print(f"Difficulty distribution: {difficulty_counts}")
        print(f"Topic distribution: {topic_counts}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())