#!/usr/bin/env python3
"""
LLM File Generator - Create files using Claude API
Supports: Python, HTML, JSON, Markdown, CSV, and more
"""

import json
import os
import sys
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LLMFileGenerator:
    """Generate files using Claude LLM API"""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the file generator with API key"""
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found. Set it as environment variable or pass as parameter.")
        
        self.api_url = "https://api.anthropic.com/v1/messages"
        self.model = "claude-3-5-sonnet-20241022"
        self.output_dir = "generated_files"
        self._create_output_dir()
        
        self.file_templates = {
            'python': {
                'extension': '.py',
                'description': 'Python script',
                'system_prompt': 'Generate production-ready Python code. Include error handling, type hints, and docstrings.'
            },
            'javascript': {
                'extension': '.js',
                'description': 'JavaScript file',
                'system_prompt': 'Generate modern JavaScript (ES6+) with proper error handling and comments.'
            },
            'html': {
                'extension': '.html',
                'description': 'HTML file',
                'system_prompt': 'Generate valid HTML5 with semantic markup and inline CSS styling.'
            },
            'json': {
                'extension': '.json',
                'description': 'JSON file',
                'system_prompt': 'Generate valid JSON with proper formatting and structure.'
            },
            'markdown': {
                'extension': '.md',
                'description': 'Markdown file',
                'system_prompt': 'Generate well-formatted Markdown with proper headers, lists, and formatting.'
            },
            'csv': {
                'extension': '.csv',
                'description': 'CSV file',
                'system_prompt': 'Generate valid CSV data with proper escaping and headers.'
            },
            'sql': {
                'extension': '.sql',
                'description': 'SQL file',
                'system_prompt': 'Generate valid SQL with proper syntax, comments, and indexing.'
            },
            'yaml': {
                'extension': '.yaml',
                'description': 'YAML configuration',
                'system_prompt': 'Generate valid YAML with proper indentation and structure.'
            }
        }
        
        logger.info("LLMFileGenerator initialized successfully")

    def _create_output_dir(self):
        """Create output directory if it doesn't exist"""
        os.makedirs(self.output_dir, exist_ok=True)
        logger.info(f"Output directory: {self.output_dir}")

    def generate_content(self, file_type: str, prompt: str) -> Optional[str]:
        """Generate file content using Claude API"""
        
        if file_type not in self.file_templates:
            logger.error(f"Unsupported file type: {file_type}")
            logger.info(f"Supported types: {', '.join(self.file_templates.keys())}")
            return None

        template = self.file_templates[file_type]
        
        full_prompt = f"""Generate {template['description']}.

Requirements: {prompt}

Provide ONLY the {file_type} code/content, no explanations or markdown formatting."""

        try:
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key
            }

            payload = {
                "model": self.model,
                "max_tokens": 4000,
                "messages": [
                    {"role": "user", "content": full_prompt}
                ]
            }

            logger.info(f"Calling Claude API for {file_type}...")
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code != 200:
                logger.error(f"API error {response.status_code}: {response.text}")
                return None

            data = response.json()
            content = data['content'][0]['text'].strip()
            
            # Remove markdown code blocks if present
            content = content.replace(f"```{file_type}\n", "").replace("\n```", "")
            content = content.replace("```python\n", "").replace("\n```", "")
            content = content.replace("```\n", "").replace("\n```", "")
            content = content.strip()
            
            logger.info(f"Successfully generated {file_type} content")
            return content

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            return None
        except (KeyError, json.JSONDecodeError) as e:
            logger.error(f"Response parsing error: {str(e)}")
            return None

    def create_file(self, file_type: str, prompt: str, filename: Optional[str] = None) -> Optional[str]:
        """Generate and save file"""
        
        if file_type not in self.file_templates:
            logger.error(f"Unsupported file type: {file_type}")
            return None

        # Generate content
        content = self.generate_content(file_type, prompt)
        if not content:
            logger.error("Failed to generate content")
            return None

        # Create filename
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{file_type}_{timestamp}"

        extension = self.file_templates[file_type]['extension']
        if not filename.endswith(extension):
            filename = filename + extension

        filepath = os.path.join(self.output_dir, filename)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"File saved: {filepath}")
            return filepath
        except IOError as e:
            logger.error(f"Error saving file: {str(e)}")
            return None

    def batch_generate(self, requests_list: list) -> Dict[str, Any]:
        """Generate multiple files in batch"""
        results = {
            "total": len(requests_list),
            "successful": 0,
            "failed": 0,
            "files": []
        }

        for req in requests_list:
            file_type = req.get('type')
            prompt = req.get('prompt')
            filename = req.get('filename')

            filepath = self.create_file(file_type, prompt, filename)
            if filepath:
                results["successful"] += 1
                results["files"].append({
                    "type": file_type,
                    "filepath": filepath,
                    "status": "success"
                })
            else:
                results["failed"] += 1
                results["files"].append({
                    "type": file_type,
                    "prompt": prompt[:50] + "...",
                    "status": "failed"
                })

        return results

    def list_generated_files(self) -> list:
        """List all generated files"""
        try:
            files = os.listdir(self.output_dir)
            logger.info(f"Found {len(files)} generated files")
            return sorted(files)
        except OSError as e:
            logger.error(f"Error listing files: {str(e)}")
            return []

    def get_file_path(self, filename: str) -> str:
        """Get full path of a generated file"""
        return os.path.join(self.output_dir, filename)


def main():
    """Example usage"""
    
    print("=" * 60)
    print("LLM File Generator - Claude API")
    print("=" * 60)
    
    try:
        generator = LLMFileGenerator()
        
        # Example 1: Generate Python file
        print("\n[1] Generating Python file...")
        python_prompt = "Create a function to calculate factorial with memoization and error handling"
        python_file = generator.create_file('python', python_prompt, 'factorial_calculator')
        
        if python_file:
            print(f"✓ Python file created: {python_file}")
            with open(python_file, 'r') as f:
                print("\nPreview:")
                print("-" * 40)
                print(f.read()[:500] + "...\n")
        
        # Example 2: Generate JSON file
        print("\n[2] Generating JSON file...")
        json_prompt = "Create sample user profile data with name, email, age, address, and preferences"
        json_file = generator.create_file('json', json_prompt, 'user_profile')
        
        if json_file:
            print(f"✓ JSON file created: {json_file}")
            with open(json_file, 'r') as f:
                print("\nPreview:")
                print("-" * 40)
                print(f.read()[:300] + "...\n")
        
        # Example 3: Generate Markdown file
        print("\n[3] Generating Markdown file...")
        md_prompt = "Create a README for a Python web scraping project with installation and usage instructions"
        md_file = generator.create_file('markdown', md_prompt, 'README')
        
        if md_file:
            print(f"✓ Markdown file created: {md_file}")
            with open(md_file, 'r') as f:
                print("\nPreview:")
                print("-" * 40)
                print(f.read()[:300] + "...\n")
        
        # Example 4: Batch generation
        print("\n[4] Batch generating multiple files...")
        batch_requests = [
            {
                'type': 'html',
                'prompt': 'Create a responsive contact form with validation',
                'filename': 'contact_form'
            },
            {
                'type': 'sql',
                'prompt': 'Create database schema for a blog with users, posts, and comments',
                'filename': 'blog_schema'
            },
            {
                'type': 'csv',
                'prompt': 'Generate sample product inventory data with 10 items',
                'filename': 'inventory'
            }
        ]
        
        batch_results = generator.batch_generate(batch_requests)
        print(f"\nBatch Generation Results:")
        print(f"  Total: {batch_results['total']}")
        print(f"  Successful: {batch_results['successful']}")
        print(f"  Failed: {batch_results['failed']}")
        
        # List all generated files
        print("\n[5] Generated files:")
        files = generator.list_generated_files()
        for file in files:
            filepath = generator.get_file_path(file)
            size = os.path.getsize(filepath) / 1024  # KB
            print(f"  • {file} ({size:.1f} KB)")
        
        print("\n" + "=" * 60)
        print(f"All files saved in: {os.path.abspath(generator.output_dir)}")
        print("=" * 60)

    except ValueError as e:
        logger.error(f"Configuration error: {str(e)}")
        print("\nTo use this script:")
        print("1. Set ANTHROPIC_API_KEY environment variable:")
        print("   export ANTHROPIC_API_KEY='your-api-key-here'")
        print("\n2. Or pass it to LLMFileGenerator(api_key='your-api-key')")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
