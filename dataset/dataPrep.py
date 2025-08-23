import requests
from bs4 import BeautifulSoup
import openai
import json
import time
import os
import csv
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

            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            title = soup.find('title')
            title_text = title.get_text().strip() if title else "No title found"

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
            
        except requests.RequestException as e:
            raise Exception(f"Error scraping URL {url}: {str(e)}")
        except Exception as e:
            raise Exception(f"Error processing content from {url}: {str(e)}")

class OpenAIQAGenerator:
    """Handles OpenAI API interaction for Q&A generation"""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        """
        Initialize OpenAI client
        
        Args:
            api_key (str): OpenAI API key
            model (str): OpenAI model to use (default: gpt-4.1-mini)
        """
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
    
    def generate_qa_pairs(self, content_data: Dict[str, str]) -> List[Dict[str, str]]:
        """
        Generate Kubernetes certification Q&A pairs from scraped content
        
        Args:
            content_data (Dict): Scraped content with title, content, etc.
            
        Returns:
            List of Q&A dictionaries
        """
        system_prompt, user_prompt = self._create_prompts(content_data)
        
        try:
            print("Generating Kubernetes Q&A pairs with OpenAI...")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            
            if not response.choices[0].message.content:
                raise Exception("Empty response from OpenAI")
            
            qa_pairs = self._parse_openai_response(response.choices[0].message.content, content_data)
            
            print(f"Generated {len(qa_pairs)} Q&A pairs")
            return qa_pairs
            
        except Exception as e:
            raise Exception(f"Error generating Q&A pairs: {str(e)}")
    
    def _create_prompts(self, content_data: Dict[str, str]) -> tuple:
        """Create system and user prompts for OpenAI"""
        
        system_prompt = """You are an expert Kubernetes instructor who creates high-quality certification exam questions. You specialize in creating questions suitable for KCNA, CKA, and CKAD certifications.

Your task is to generate Kubernetes certification-style questions with detailed explanations that help students learn.

Create TWO types of questions:

A) MULTIPLE CHOICE QUESTIONS (MCQs):
- Include 4 options (A, B, C, D) in the question field
- Answer should contain the correct option letter and the option text
- Explanation should explain why the correct answer is right AND why each incorrect option is wrong

B) PRACTICAL COMMAND QUESTIONS:
- Task-based questions asking to create/configure Kubernetes resources
- Answer should be the exact kubectl command(s)
- Explanation should explain what the command does, why each flag is used, and any important notes

Requirements:
- Focus on real Kubernetes certification exam topics
- Mix both MCQ and practical command questions
- Make explanations educational and helpful for learning
- Ensure technical accuracy and use proper Kubernetes terminology

Return ONLY a valid JSON array with the specified format."""

        user_prompt = f"""Based on the following Kubernetes-related content, generate up to 6 high-quality questions suitable for Kubernetes certification exams.

Source Information:
- Title: {content_data['title']}
- URL: {content_data['url']}
- Domain: {content_data['domain']}

Content:
{content_data['content']}

Generate a maximum of 6 questions (generate fewer if content does not support 6 well-formed questions).

Format your response as a JSON array with this exact structure:

[
  {{
    "question": "What is the default restart policy for a Pod in Kubernetes?\\n\\nA) Always\\nB) OnFailure\\nC) Never\\nD) RestartAlways",
    "answer": "A) Always",
    "explanation": "The correct answer is A) Always. This is the default restart policy for Pods in Kubernetes, meaning containers will be restarted whenever they exit, regardless of the exit code. Option B) OnFailure is incorrect because this policy only restarts containers when they exit with a non-zero status code. Option C) Never is incorrect as this policy never restarts containers once they exit. Option D) RestartAlways is incorrect because this is not a valid Kubernetes restart policy name."
  }},
  {{
    "question": "Create a Deployment named 'nginx-deploy' with 3 replicas using the nginx:1.20 image in the default namespace.",
    "answer": "kubectl create deployment nginx-deploy --image=nginx:1.20 --replicas=3",
    "explanation": "This command creates a Deployment resource using the 'kubectl create deployment' command. The '--image=nginx:1.20' flag specifies the container image to use for the pods. The '--replicas=3' flag sets the desired number of pod replicas to 3, ensuring high availability. Since no namespace is specified with '-n' or '--namespace', it will be created in the default namespace. The Deployment will automatically create a ReplicaSet to manage the pods."
  }}
]

Important: Return ONLY the JSON array, no additional text or markdown formatting."""

        return system_prompt, user_prompt

    def _parse_openai_response(self, response_text: str, content_data: Dict[str, str]) -> List[Dict[str, str]]:
        """Parse OpenAI response and return clean Q&A pairs with explanations"""
        try:
            response_text = response_text.strip()
            
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()

            qa_pairs = json.loads(response_text)
            
            if not isinstance(qa_pairs, list):
                raise ValueError("Response is not a list")
            
            # Clean and validate Q&A pairs
            cleaned_pairs = []
            for qa in qa_pairs:
                if 'question' in qa and 'answer' in qa and 'explanation' in qa:
                    cleaned_pairs.append({
                        'question': qa['question'].strip(),
                        'answer': qa['answer'].strip(),
                        'explanation': qa['explanation'].strip()
                    })
            
            return cleaned_pairs
            
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response from OpenAI: {str(e)}")
        except Exception as e:
            raise Exception(f"Error parsing OpenAI response: {str(e)}")

class CSVWriter:
    """Handles writing Q&A pairs to CSV file"""
    
    @staticmethod
    def write_to_csv(qa_pairs: List[Dict[str, str]], filename: str = "kubernetes_qa.csv"):
        """
        Write Q&A pairs to a CSV file (append mode)
        
        Args:
            qa_pairs (List): List of Q&A dictionaries
            filename (str): Output CSV filename
        """
        try:
            print(f"Appending {len(qa_pairs)} Q&A pairs to {filename}")
            
            # Check if file exists to determine if we need headers
            file_exists = os.path.exists(filename)
            
            with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['question', 'answer', 'explanation']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                if not file_exists:
                    writer.writeheader()
                    print(f"Created new CSV file: {filename}")

                for qa in qa_pairs:
                    writer.writerow({
                        'question': qa['question'],
                        'answer': qa['answer'],
                        'explanation': qa['explanation']
                    })
            
            print(f"Successfully appended {len(qa_pairs)} Q&A pairs to {filename}")
            
            total_count = CSVWriter.count_rows_in_csv(filename)
            print(f"Total questions in {filename}: {total_count}")
                    
        except Exception as e:
            raise Exception(f"Error writing to CSV file {filename}: {str(e)}")
    
    @staticmethod
    def count_rows_in_csv(filename: str) -> int:
        """Count total rows in CSV file (excluding header)"""
        try:
            if not os.path.exists(filename):
                return 0
            
            with open(filename, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                row_count = sum(1 for row in reader) - 1
                return max(0, row_count)  # Ensure non-negative
        except Exception:
            return 0

def main():
    """Main function to orchestrate the scraping and Q&A generation"""
    parser = argparse.ArgumentParser(description='Generate Kubernetes certification Q&A pairs from URL content using OpenAI')
    parser.add_argument('url', help='URL to scrape for content')
    parser.add_argument('--api-key', help='OpenAI API key (or set OPENAI_API_KEY env var)')
    parser.add_argument('--model', default='gpt-4.1-mini', help='OpenAI model to use (default: gpt-4)')
    parser.add_argument('--output', default='kubernetes_qa_output.csv', help='Output CSV filename')
    
    args = parser.parse_args()
    
    api_key = args.api_key or os.getenv('API_KEY')
    if not api_key:
        print("Error: OpenAI API key is required.")
        print("Either pass --api-key or set OPENAI_API_KEY environment variable")
        return 1
    
    try:
        scraper = URLScraper()
        generator = OpenAIQAGenerator(api_key, args.model)
        writer = CSVWriter()

        print("Step 1: Scraping URL content...")
        content_data = scraper.scrape_url(args.url)
        print("Scraping complete.")
        print(f"Scraped {content_data['length']} characters from {content_data['domain']}")
        

        print(f"\nStep 2: Generating Kubernetes Q&A pairs using {args.model}...")
        qa_pairs = generator.generate_qa_pairs(content_data)
        
        if not qa_pairs:
            print("Warning: No Q&A pairs were generated")
            return 1
        

        print(f"\nStep 3: Writing to {args.output}...")
        writer.write_to_csv(qa_pairs, args.output)
        
        print(f"\n✅ Successfully generated {len(qa_pairs)} Q&A pairs!")
        print(f"📁 Questions appended to: {args.output}")
        
        print(f"\n📋 Sample questions generated:")
        for i, qa in enumerate(qa_pairs[:2], 1):
            print(f"\nQuestion {i}:")
            print(f"Q: {qa['question'][:100]}...")
            print(f"A: {qa['answer'][:50]}...")
            print(f"E: {qa['explanation'][:100]}...")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())