import urllib.request
import urllib.parse
import json
import re

def run_wikipedia(message: str):
    """Search Wikipedia for a query extracted from the message."""
    
    triggers = ["wiki", "wikipedia", "define", "what is"]
    query = None
    trigger_used = None
    
    lower_msg = message.lower()
    
    # Identify trigger and extract query
    for trigger in triggers:
        if trigger in lower_msg:
            pattern = re.compile(re.escape(trigger), re.IGNORECASE)
            match = pattern.search(message)
            if match:
                potential_query = message[match.end():].strip()
                potential_query = potential_query.strip('?.!')
                if potential_query:
                    query = potential_query
                    trigger_used = trigger
                    break
    
    if not query:
        if "wiki" in lower_msg:
             return "ℹ️ Usage: wiki <search term>"
        return None

    # Heuristic: Avoid triggering on complex questions for "what is"
    if trigger_used in ["what is", "define"] and len(query.split()) > 5:
        return None

    print(f"🔍 Searching Wikipedia for: {query}")

    try:
        # 1. Search for the page
        search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&format=json"
        
        req = urllib.request.Request(
            search_url, 
            headers={'User-Agent': 'BuddAI/5.0 (Educational AI)'}
        )
        
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        if not data.get('query', {}).get('search'):
            if trigger_used in ["wiki", "wikipedia"]:
                return f"🤷 No Wikipedia results found for '{query}'."
            return None
            
        title = data['query']['search'][0]['title']
        
        # 2. Get the summary
        summary_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&exintro&explaintext&titles={urllib.parse.quote(title)}&format=json"
        
        req_sum = urllib.request.Request(
            summary_url, 
            headers={'User-Agent': 'BuddAI/5.0 (Educational AI)'}
        )
        
        with urllib.request.urlopen(req_sum, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        pages = data['query']['pages']
        page_id = list(pages.keys())[0]
        
        if page_id == "-1":
             if trigger_used in ["wiki", "wikipedia"]:
                return f"🤷 Could not retrieve content for '{title}'."
             return None
             
        extract = pages[page_id].get('extract', '')
        
        if not extract:
            return f"📚 **{title}**\n(No summary available)"

        limit = 600
        if len(extract) > limit:
            extract = extract[:limit].rsplit('.', 1)[0] + "."
            
        url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title)}"
        
        return f"📚 **Wikipedia: {title}**\n\n{extract}\n\n🔗 {url}"

    except Exception as e:
        if trigger_used in ["wiki", "wikipedia"]:
            return f"❌ Wikipedia Error: {str(e)}"
        return None

skill = {
    "name": "Wikipedia Search",
    "description": "Search Wikipedia (Usage: wiki <term>)",
    "triggers": ["wiki", "wikipedia", "define", "what is"],
    "run": run_wikipedia
}