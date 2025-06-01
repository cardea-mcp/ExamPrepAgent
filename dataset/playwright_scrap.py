from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urlparse
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
    """Handles web scraping with JavaScript rendering using Playwright"""

    def __init__(self):
        pass  # No session needed as Playwright handles browser context

    def scrape_url(self, url: str) -> dict:
        try:
            print(f"Scraping URL with JS rendering: {url}")
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36',
                    viewport={'width': 1280, 'height': 800},
                    java_script_enabled=True
                )
                page = context.new_page()
                page.goto(url, timeout=60000)
                page.wait_for_load_state("networkidle")
                time.sleep(3)  # Give some time for JS to render
                page.screenshot(path="debug.png", full_page=True)  # For debugging
                html = page.content()
                browser.close()


            soup = BeautifulSoup(html, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()

            # Extract title
            title = soup.find('title')
            title_text = title.get_text().strip() if title else "No title found"

            # Extract main content - try multiple selectors
            content_selectors = [
                'main', 'article', '.content', '#content',
                '.post-content', '.entry-content', 'body'
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

            if len(content_text) > 8000:
                content_text = content_text[:8000] + "..."

            return {
                'url': url,
                'title': title_text,
                'content': content_text,
                'domain': urlparse(url).netloc,
                'length': len(content_text)
            }

        except Exception as e:
            raise Exception(f"Error scraping URL with Playwright: {str(e)}")

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
Based on the following content related to Linux systems or commands, generate up to 4 high-quality question and answer pairs suitable for foundational Linux knowledge assessment.

Source Information:
- Title: {content_data['title']}
- URL: {content_data['url']}
- Domain: {content_data['domain']}

Content:
{content_data['content']}

Requirements:
1. Generate a maximum of 4 Q&A pairs (generate fewer if content does not support 4 well-formed questions).
2. Questions should vary in difficulty (beginner to advanced).
3. Focus on Linux concepts, commands, usage, system administration, etc.
4. Ensure the answers are technically accurate and educational.
5. Avoid repetition. If the content is too narrow, generate fewer questions.
6. Try to make questions that are both practical and conceptual.

Format your response **strictly** in the following JSON structure:

[
  {{
    "question": "What does the 'ls' command do in Linux?",
    "answer": "'ls' lists the contents of a directory.",
    "difficulty": "beginner",
    "topic": "commands",
    "question_type": "practical"
  }},
  {{
    "question": "Explain the significance of file permissions in Linux.",
    "answer": "File permissions in Linux determine who can read, write, or execute a file. They are set using chmod and displayed with ls -l.",
    "difficulty": "intermediate",
    "topic": "permissions",
    "question_type": "conceptual"
  }}
]

**Important Instructions**:
- Return only a valid JSON array, nothing else.
- Do not include markdown code blocks or extra text.
- Ensure the JSON is syntactically correct.
- Do not exceed 4 Q&A pairs. Fewer is acceptable based on content.
- Each Q&A object must include: question, answer, difficulty, topic, question_type.
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
    def write_to_file(qa_pairs: List[Dict[str, str]], filename: str = "linux_basic.txt"):
        """
        Write Q&A pairs to a text file
        
        Args:
            qa_pairs (List): List of Q&A dictionaries
            filename (str): Output filename
        """
        try:
            print(f"Writing {len(qa_pairs)} Q&A pairs to {filename}")
            
            with open(filename, 'a', encoding='utf-8') as f:
                f.write("LINUX Q&A PAIRS\n")
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
    def write_to_json(qa_pairs: List[Dict[str, str]], filename: str = "linux_basic.json"):
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
        print("Scraping complete.",content_data)
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