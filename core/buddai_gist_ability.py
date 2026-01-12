"""
BuddAI Gist Ability
Ability to fetch, parse, and search forensic summaries from GitHub gists.
"""
import requests
import re

import os

class BuddAIGistAbility:
    def __init__(self, gist_memory_path=None):
        if gist_memory_path is None:
            gist_memory_path = os.path.join(os.path.dirname(__file__), 'gist_memory.txt')
        self.gist_memory_path = gist_memory_path
        self.gist_urls = self._load_gist_urls()
        self.gist_data = []

    def _load_gist_urls(self):
        urls = []
        if os.path.exists(self.gist_memory_path):
            with open(self.gist_memory_path, 'r') as f:
                for line in f:
                    url = line.strip()
                    if url:
                        urls.append(url)
        return urls

    def fetch_gists(self):
        for url in self.gist_urls:
            raw_url = self._convert_to_raw(url)
            try:
                response = requests.get(raw_url)
                if response.status_code == 200:
                    self.gist_data.append(self._parse_gist(response.text))
            except Exception as e:
                print(f"Error fetching {url}: {e}")

    def _convert_to_raw(self, url):
        # Converts gist URL to raw content URL
        if url.endswith('/raw'):
            return url
        return url.replace('gist.github.com', 'gist.githubusercontent.com').replace('/gist/', '/').replace('/blob/', '/raw/')

    def _parse_gist(self, text):
        # Parse headers, sections, and entries
        summary = {}
        header_match = re.search(r'=+\s*(BUDDAI FORENSIC SUMMARY:.*?)=+', text, re.DOTALL)
        summary['header'] = header_match.group(1).strip() if header_match else ''
        sections = re.split(r'-{3,}\s*SECTION \d+:.*?-{3,}', text)
        section_titles = re.findall(r'-{3,}\s*SECTION \d+:.*?-{3,}', text)
        summary['sections'] = []
        for i, section in enumerate(sections[1:]):
            entries = re.findall(r'/(teach|explain|report|fix):?\s*(.*)', section)
            summary['sections'].append({
                'title': section_titles[i].strip('- '),
                'entries': [{'type': e[0], 'text': e[1].strip()} for e in entries]
            })
        return summary

    def search(self, query):
        results = []
        for gist in self.gist_data:
            for section in gist['sections']:
                for entry in section['entries']:
                    if query.lower() in entry['text'].lower():
                        results.append({
                            'header': gist['header'],
                            'section': section['title'],
                            'type': entry['type'],
                            'text': entry['text']
                        })
        return results
