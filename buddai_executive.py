#!/usr/bin/env python3
from urllib.parse import urlparse
import sys, os, json, logging, sqlite3, re, zipfile, shutil, queue, argparse, io
import urllib.request
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Tuple, Union, Generator, Any

from core.workflow_detector import WorkflowDetector

try:
    import psutil
except ImportError:
    psutil = None

from core.buddai_analytics import LearningMetrics
from core.buddai_validation import HardwareProfile
from core.buddai_confidence import ConfidenceScorer
from core.buddai_fallback import FallbackClient
from core.buddai_abilities import ConversationProtocol
from core.buddai_memory import AdaptiveLearner, ShadowSuggestionEngine, SmartLearner
from core.buddai_shared import DATA_DIR, DB_PATH, MODELS, OLLAMA_HOST, OLLAMA_PORT, SERVER_AVAILABLE
from core.buddai_training import ModelFineTuner
from core.buddai_knowledge import RepoManager
from core.buddai_llm import OllamaClient
from core.buddai_prompt_engine import PromptEngine
from core.buddai_personality import PersonalityManager
from conversation.personality import BuddAIPersonality
from conversation.project_memory import get_project_memory, Project
from core.buddai_storage import StorageManager
from validators.registry import ValidatorRegistry
from skills import load_registry
from languages.language_registry import get_language_registry
from training import get_training_registry

logger = logging.getLogger(__name__)

# --- Shadow Suggestion Engine ---

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
ALLOWED_TYPES = [
    "application/zip", "application/x-zip-compressed", "application/octet-stream",
    "text/x-python", "text/plain", "text/x-c++src", "text/x-csrc", "text/javascript", "text/html", "text/css"
]
MAX_UPLOAD_FILES = 20

class ChatResponse(str):
    """String subclass that carries metadata"""
    def __new__(cls, content, model=None, intent=None):
        obj = super().__new__(cls, content)
        obj.model = model
        obj.intent = intent
        return obj

class BuddAI:
    """Executive with task breakdown"""

    def __init__(self, user_id: str = "default", server_mode: bool = False, db_path: str = None):
        self.user_id = user_id
        self.db_path = db_path or DB_PATH
        self.last_generated_id = None
        self.last_prompt_debug = None
        self.server_mode = server_mode
        self.context_messages = []
        self.storage = StorageManager(self.user_id)
        self.personality_manager = PersonalityManager()
        self.personality_engine = BuddAIPersonality()
        self.shadow_engine = ShadowSuggestionEngine(self.db_path, self.user_id)
        self.learner = SmartLearner()
        self.hardware_profile = HardwareProfile()
        self.current_hardware = "Generic"
        self.validator = ValidatorRegistry()
        self.confidence_scorer = ConfidenceScorer()
        self.fallback_client = FallbackClient()
        self.adaptive_learner = AdaptiveLearner()
        self.metrics = LearningMetrics()
        self.training_registry = get_training_registry()
        self.fine_tuner = ModelFineTuner()
        self.conversation_protocol = ConversationProtocol(self.personality_manager)
        self.repo_manager = RepoManager(self.db_path, self.user_id)
        self.llm = OllamaClient()
        self.prompt_engine = PromptEngine()
        self.skills_registry = load_registry()
        self.language_registry = get_language_registry()
        self.workflow_detector = WorkflowDetector()
        
        # Conversational systems
        self.personality = BuddAIPersonality()
        self.project_memory = get_project_memory()
        self.current_project = None  # Active project context
        self.default_mode = 'balanced'
        
        logger.info("Conversational systems initialized")
        
        # Auto-index Gists on startup
        threading.Thread(target=self.repo_manager.index_gists, kwargs={'silent': True}, daemon=True).start()
        
        # Auto-register James's Personality Gist
        def _load_james_personality():
            url = "https://gist.githubusercontent.com/JamesTheGiblet/ead7080eb60e1e3b465a37a3cd8eeed1/raw/007a8758417b8ee1af4b946f038ec23d69920155/gistfile1.txt"
            success, msg = self.register_knowledge_source(url, "James")
            if success:
                try:
                    count = msg.split("Learned ")[1].split(" rules")[0]
                    print(f"🧠 Personality Synced: {count} rules loaded from James's Gist")
                except IndexError:
                    print(f"🧠 Personality Synced: James's Gist loaded")

        threading.Thread(target=_load_james_personality, daemon=True).start()
        
        self.display_welcome_message()
        
        print(f"\n{self.personality_manager.get_user_status()}\n")

    def close(self):
        """Cleanup resources and connections"""
        if hasattr(self, 'storage'):
            try:
                self.storage.conn.close()
            except:
                pass
    
    def index_local_repositories(self, path: str):
        """Wrapper for repo_manager indexing to satisfy architecture expectations"""
        self.repo_manager.index_local_repositories(path)
        
    def display_welcome_message(self):
        """Display the startup banner and status."""
        # Get personality greeting
        greeting = self.personality.greet()
        
        print("\n" + "="*50)
        print(greeting)
        print("="*50)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM code_rules")
            count = cursor.fetchone()[0]
            conn.close()
            print(f"🧠 Learned Rules: {count}")
        except:
            pass
        
        # Show recent projects if any
        recent = self.project_memory.get_recent_projects(n=3)
        if recent:
            print("\n📁 Recent Projects:")
            for proj in recent:
                status_icon = "▶️" if proj.status == 'active' else "⏸️"
                print(f"  {status_icon} {proj.name} ({proj.project_type})")
            print("\nType /projects to see all, or /open <name> to continue\n")
        
        print(f"Session: {self.storage.current_session_id}")
        print(f"🧩 Smart Skills: {len(self.skills_registry)} loaded")
        print(f"🛡️  Validators:   {len(self.validator.validators)} loaded")
        print(f"🌐 Languages:    {len(self.language_registry.get_supported_languages())} loaded")
        print(f"FAST (5-10s) | BALANCED (15-30s)")
        print(f"Smart task breakdown for complex requests")
        print("=" * 50)
        print("\nCommands: /fast, /balanced, /help, exit\n")
        
    def scan_style_signature(self) -> None:
        """V3.0: Analyze repo_index to extract style preferences."""
        self._print("\n🕵️  Scanning repositories for style signature...")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get a sample of code
        cursor.execute("SELECT content FROM repo_index WHERE user_id = ? ORDER BY RANDOM() LIMIT 5", (self.user_id,))
        rows = cursor.fetchall()
        
        if not rows:
            self._print("❌ No code indexed. Run /index first.")
            conn.close()
            return
            
        code_sample = "\n---\n".join([r[0][:1000] for r in rows])
        
        prompt_template = self.personality_manager.get_value("prompts.style_scan", "Analyze this code sample from {user_name}'s repositories.\nExtract 3 distinct coding preferences or patterns.\n\nCode Sample:\n{code_sample}")
        prompt = prompt_template.format(user_name=self.personality_manager.get_value("identity.user_name", "the user"), code_sample=code_sample)
        
        self._print("⚡ Analyzing with BALANCED model...")
        summary = self.call_model("balanced", prompt, system_task=True)
        
        # Store in DB
        timestamp = datetime.now().isoformat()
        lines = summary.split('\n')
        for line in lines:
            if ':' in line:
                parts = line.split(':', 1)
                category = parts[0].strip('- *')
                pref = parts[1].strip()
                cursor.execute(
                    "INSERT INTO style_preferences (user_id, category, preference, confidence, extracted_at) VALUES (?, ?, ?, ?, ?)",
                    (self.user_id, category, pref, 0.8, timestamp)
                )
        
        conn.commit()
        conn.close()
        self._print(f"\n✅ Style Signature Updated:\n{summary}\n")

    def get_recent_context(self, limit: int = 5) -> str:
        """Get recent chat context as a string"""
        return json.dumps(self.context_messages[-limit:])

    def save_correction(self, original_code: str, corrected_code: str, reason: str):
        """Store when James fixes BuddAI's code"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS corrections (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                original_code TEXT,
                corrected_code TEXT,
                reason TEXT,
                context TEXT
            )
        """)
        
        cursor.execute("""
            INSERT INTO corrections 
            (timestamp, original_code, corrected_code, reason, context)
            VALUES (?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            original_code,
            corrected_code,
            reason,
            self.get_recent_context()
        ))
        
        conn.commit()
        conn.close()

    def detect_hardware(self, message: str) -> str:
        """Wrapper to detect hardware from message or return current default"""
        hw = self.hardware_profile.detect_hardware(message)
        return hw if hw else self.current_hardware

    def get_applicable_rules(self, user_message: str) -> List[Dict]:
        """Get rules relevant to the user message"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Fetch rules with reasonable confidence
        # Added id to select for recency boosting
        cursor.execute("SELECT rule_text, confidence, id FROM code_rules WHERE confidence > 0.6 ORDER BY confidence DESC")
        rows = cursor.fetchall()
        conn.close()
        
        all_rules = [{"rule_text": r[0], "confidence": r[1], "id": r[2]} for r in rows]
        
        if not user_message:
            return all_rules[:50]
            
        # Filter and rank rules by relevance to prevent context flooding
        msg_lower = user_message.lower()
        # Limit to first 100 words to avoid performance hit on large pastes
        words = re.findall(r'\w+', msg_lower)[:100]
        keywords = set(words) - {'what', 'is', 'my', 'the', 'and', 'a', 'to', 'of', 'in', 'for', 'are', 'do', "what's"}
        
        scored_rules = []
        max_id = max([r['id'] for r in all_rules]) if all_rules else 1
        
        for rule in all_rules:
            rule_text = rule['rule_text'].lower()
            score = rule['confidence'] * 10.0
            
            # Keyword matching
            matches = sum(1 for kw in keywords if kw in rule_text)
            score += matches * 5.0
            
            # High relevance boost: If rule contains significant portion of query keywords
            if len(keywords) > 0 and matches >= len(keywords) * 0.4:
                score += 15.0
            
            # Personal context boost
            if "my " in msg_lower or " i " in msg_lower:
                # Boost rules that start with "my" or "i" if they contain query keywords
                if (rule_text.startswith("my ") or rule_text.startswith("i ")) and matches > 0:
                    score += 15.0
                
                if any(p in rule_text for p in ["i work", "my job", "my plan", "i am", "my company", "exit plan"]):
                    score += 10.0
            
            # Recency boost (Newer rules are more likely to be relevant corrections)
            score += (rule['id'] / max_id) * 5.0
            
            scored_rules.append((score, rule))
            
        # Sort by relevance and limit to top 50
        scored_rules.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in scored_rules[:50]]

    def get_style_summary(self) -> str:
        """Get summary of learned style preferences"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT category, preference FROM style_preferences WHERE confidence > 0.6")
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            return "Standard coding style."
        return ", ".join([f"{r[0]}: {r[1]}" for r in rows])

    def teach_rule(self, rule_text: str, source: str = 'user_taught') -> bool:
        """Explicitly save a user-taught rule. Returns True if new, False if duplicate."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check for duplicate to prevent spamming from auto-discovery
        cursor.execute("SELECT 1 FROM code_rules WHERE rule_text = ?", (rule_text,))
        if cursor.fetchone():
            conn.close()
            return False

        cursor.execute("""
            INSERT INTO code_rules 
            (rule_text, pattern_find, pattern_replace, confidence, learned_from)
            VALUES (?, ?, ?, ?, ?)
        """, (rule_text, "", "", 1.0, source))
        conn.commit()
        conn.close()
        return True

    def log_compilation_result(self, code: str, success: bool, errors: str = ""):
        """Track what compiles vs what fails"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS compilation_log (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                code TEXT,
                success BOOLEAN,
                errors TEXT,
                hardware TEXT
            )
        """)
        
        cursor.execute("""
            INSERT INTO compilation_log 
            (timestamp, code, success, errors, hardware)
            VALUES (?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            code,
            success,
            errors,
            "ESP32-C3"  # Your target hardware
        ))
        
        conn.commit()
        conn.close()

    def get_learned_rules(self) -> List[Dict]:
        """Retrieve high-confidence rules"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT rule_text, pattern_find, pattern_replace, confidence FROM code_rules WHERE confidence >= 0.8")
            rows = cursor.fetchall()
            conn.close()
            return [{"rule": r[0], "find": r[1], "replace": r[2], "confidence": r[3]} for r in rows]
        except Exception as e:
            logger.error(f"Error retrieving learned rules: {e}")
            return []

    def _get_current_mode_note(self) -> Optional[str]:
        """Retrieve the note for the current work cycle mode"""
        now = datetime.now()
        current_hour = now.hour + (now.minute / 60.0)
        day_of_week = now.weekday()
        
        schedule = self.personality_manager.get_value("work_cycles.schedule")
        if not schedule:
            return None
            
        # Determine day group
        day_group = "weekdays" if day_of_week < 5 else "weekends"
        group_schedule = schedule.get(day_group, {})
        
        # Find specific day config
        day_config = None
        for key, config in group_schedule.items():
            if '-' in key:
                start, end = map(int, key.split('-'))
                if start <= day_of_week <= end:
                    day_config = config
                    break
            elif str(day_of_week) == key:
                day_config = config
                break
        
        if not day_config:
            return None
            
        # Find time slot
        for time_range, settings in day_config.items():
            if '-' in time_range:
                try:
                    start, end = map(float, time_range.split('-'))
                    if start <= current_hour < end:
                        return settings.get("note")
                except ValueError:
                    continue
                    
        return day_config.get("default", {}).get("note")

    def _ingest_teach_commands(self, content: str, source_tag: str) -> int:
        """Extract and learn /teach commands from text content"""
        count = 0
        for line in content.splitlines():
            if line.strip().startswith('/teach'):
                # Strip comments (e.g. "Rule text # comment")
                clean_line = line.split('#')[0].strip()
                rule = clean_line[6:].strip()
                if rule:
                    if self.teach_rule(rule, source=f"gist:{source_tag}"):
                        count += 1
        return count

    def register_knowledge_source(self, url: str, tag: str) -> Tuple[bool, str]:
        """Register a secret gist or knowledge source"""
        try:
            # Handle raw URL conversion for GitHub Gists
            if 'gist.github.com' in url and '/raw' not in url:
                url = url.rstrip('/') + '/raw'
            
            req = urllib.request.Request(url, headers={'User-Agent': 'BuddAI/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status != 200:
                    return False, f"HTTP {response.status}"
                content = response.read().decode('utf-8')
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_sources (
                    id INTEGER PRIMARY KEY,
                    url TEXT UNIQUE,
                    tag TEXT,
                    content TEXT,
                    added_at TEXT
                )
            """)
            
            cursor.execute("""
                INSERT OR REPLACE INTO knowledge_sources (url, tag, content, added_at)
                VALUES (?, ?, ?, ?)
            """, (url, tag.lower(), content, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            # Auto-ingest rules from the content
            learned = self._ingest_teach_commands(content, tag)
            
            return True, f"Indexed {len(content)} bytes. Learned {learned} rules from '{tag}'."
        except Exception as e:
            return False, str(e)

    def get_knowledge_context(self, message: str) -> str:
        """Retrieve context from knowledge sources based on tags"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_sources'")
            if not cursor.fetchone():
                conn.close()
                return ""
                
            # Simple tag matching
            msg_lower = message.lower()
            cursor.execute("SELECT tag, content FROM knowledge_sources")
            rows = cursor.fetchall()
            conn.close()
            
            hits = []
            for tag, content in rows:
                # Check if tag is referenced (handle underscores as spaces too)
                tag_normalized = tag.replace('_', ' ').lower()
                is_triggered = tag in msg_lower or tag_normalized in msg_lower
                
                # Smart Section Filtering based on user's header format
                section_match = self._extract_relevant_section(content, message)
                
                if is_triggered:
                    if section_match:
                        hits.append(f"[{tag.upper()} KNOWLEDGE BASE - RELEVANT SECTION]\n{section_match}\n")
                    else:
                        # Limit content length to avoid context overflow
                        snippet = content[:3000] 
                        hits.append(f"[{tag.upper()} KNOWLEDGE BASE]\n{snippet}\n")
                elif section_match:
                    # Auto-discovery: If section title strongly matches query, include it even without tag
                    hits.append(f"[{tag.upper()} KNOWLEDGE BASE - AUTO-DETECTED SECTION]\n{section_match}\n")
            
            return "\n".join(hits)
        except Exception:
            return ""

    def _extract_relevant_section(self, content: str, query: str) -> Optional[str]:
        """Extract specific section from content based on query keywords"""
        # Regex for the user's specific header format:
        # # ==================================================
        # # SECTION 1: WORK & PROFESSIONAL IDENTITY
        # # ==================================================
        # Improved regex to handle whitespace, newlines, and potential variations
        section_pattern = r'(#\s*={10,}\s*[\r\n]+#\s*SECTION\s*\d+\s*:\s*(.*?)\s*[\r\n]+#\s*={10,})'
        matches = list(re.finditer(section_pattern, content, re.IGNORECASE))
        
        if not matches:
            return None
            
        query_lower = query.lower()
        scored_sections = []
        
        # Synonyms for better matching
        synonyms = {
            'job': ['work', 'career', 'role', 'position', 'company'],
            'work': ['job', 'career', 'business', 'company'],
            'company': ['business', 'work', 'organization', 'startup', 'enterprise', 'commercial'],
            'business': ['commercial', 'company', 'strategy', 'market'],
            'commercial': ['business', 'sales', 'market', 'relationship'],
            'product': ['project', 'creation', 'invention', 'tool', 'platform'],
            'plan': ['strategy', 'roadmap', 'goals'],
            'exit': ['leaving', 'transition', 'future'],
            'relationship': ['partner', 'connection', 'contact', 'business', 'discussion', 'negotiation', 'prospect'],
            'philosophy': ['approach', 'values', 'beliefs', 'principles', 'core', 'mindset'],
            'approach': ['philosophy', 'method', 'style', 'way']
        }
        
        # Expand query with synonyms
        query_words = set(re.findall(r'\w+', query_lower))
        expanded_query = set(query_words)
        for word in query_words:
            if word in synonyms:
                expanded_query.update(synonyms[word])
        
        for i, match in enumerate(matches):
            title = match.group(2).lower()
            start_pos = match.start()
            
            # Determine end pos (start of next section or end of string)
            end_pos = matches[i+1].start() if i < len(matches) - 1 else len(content)
            section_text = content[start_pos:end_pos]
            
            # Clean up /teach commands for better LLM consumption
            section_text = re.sub(r'^\s*/teach\s+', '', section_text, flags=re.MULTILINE)
            
            # Score based on title match
            score = 0
            
            # Title word match
            title_words = [w for w in title.split() if len(w) > 3]
            for w in title_words:
                if w in expanded_query:
                    score += 15
                elif w in query_lower:
                    score += 10
            
            # Content scanning for specific phrases in query
            if "exit plan" in query_lower and "exit plan" in section_text.lower():
                score += 30
            if "current job" in query_lower and "current" in section_text.lower():
                score += 10
            
            # Specific boost for business/commercial queries matching Business Strategy section
            if ("commercial" in query_lower or "business" in query_lower) and "business" in title:
                score += 40

            # Specific boost for philosophy/approach queries
            if ("philosophy" in query_lower or "approach" in query_lower or "values" in query_lower) and ("philosophy" in title or "approach" in title):
                score += 40

            # Phrase matching for high specificity
            if "commercial relationship" in query_lower and "commercial relationship" in section_text.lower():
                score += 50

            # Specific boost for relationship/partner queries
            # Only apply high boost if BOTH query and text confirm business context
            is_business_query = "commercial" in query_lower or "business" in query_lower or "partner" in query_lower
            has_business_content = "commercial" in section_text.lower() or "business" in section_text.lower() or "partner" in section_text.lower()
            
            if ("relationship" in query_lower or "partner" in query_lower) and ("relationship" in section_text.lower() or "partner" in section_text.lower()):
                score += 30 if (is_business_query and has_business_content) else 5

            # Boost if query words appear in content (not just title)
            for word in expanded_query:
                if len(word) > 4 and word in section_text.lower():
                    score += 5

            # General overlap
            content_words = set(re.findall(r'\w+', section_text.lower()))
            overlap = len(expanded_query.intersection(content_words))
            score += overlap  # 1 point per word overlap
            
            if score >= 10:
                scored_sections.append((score, section_text.strip()))
        
        if not scored_sections:
            return None
            
        # Sort by score descending
        scored_sections.sort(key=lambda x: x[0], reverse=True)
        
        # Dynamic Threshold: Only keep sections that are relevant compared to the top match
        top_score = scored_sections[0][0]
        filtered_sections = [s for s in scored_sections if s[0] >= top_score * 0.3 or s[0] > 30]
        
        # Refine content: If a section is large, try to extract only relevant lines
        final_sections = []
        query_tokens = [w for w in query_lower.split() if len(w) > 3]
        
        for section_score, text in filtered_sections[:3]:
            lines = text.split('\n')
            # If section is short, just keep it all to preserve context
            if len(lines) <= 5:
                final_sections.append(text)
                continue
                
            scored_lines = []
            header_lines = []
            
            for line in lines:
                # Keep headers and empty lines for structure
                if line.strip().startswith('#') or not line.strip():
                    header_lines.append(line)
                    continue
                
                line_score = 0
                line_lower = line.lower()
                
                # Exact phrase match (high value)
                if query_lower in line_lower:
                    line_score += 50
                
                # Token match
                for token in query_tokens:
                    if token in line_lower:
                        line_score += 10
                
                scored_lines.append((line_score, line))
            
            # If we found lines with relevance
            if scored_lines:
                max_line_score = max(l[0] for l in scored_lines)
                
                # Only filter if we have a strong match (>= 20 means at least 2 tokens or exact phrase)
                if max_line_score >= 20:
                    # Keep lines that are relevant (at least 50% of max score)
                    relevant_lines = [l[1] for l in scored_lines if l[0] >= max_line_score * 0.5]
                    
                    # If we filtered out a significant portion (e.g. kept < 70%), use filtered version
                    if len(relevant_lines) < len(scored_lines) * 0.7:
                        final_sections.append("\n".join(header_lines + relevant_lines))
                        continue
            
            # Default: keep whole section if no specific lines stood out
            final_sections.append(text)
            
        return "\n\n".join(final_sections)

    def call_model(self, model_name: str, message: str, stream: bool = False, system_task: bool = False, hardware_override: Optional[str] = None) -> Union[str, Generator[str, None, None]]:
        """Call specified model"""
        try:
            messages = []
            
            if system_task:
                # Direct prompt, no history, no enhancement
                messages.append({"role": "user", "content": message})
            else:
                # Use enhanced prompt builder
                hw_context = hardware_override if hardware_override else self.current_hardware
                
                if hw_context == "Conversational":
                    # Bypass PromptEngine for pure conversation to avoid code bias
                    persona = self.personality_manager.get_value("identity.persona_description", "You are BuddAI.")
                    user_name = self.personality_manager.get_value("identity.user_name", "User")
                    
                    # Inject Forge Theory context for conversational awareness
                    ft_desc = self.personality_manager.get_value("forge_theory.description", "")
                    ft_formula = self.personality_manager.get_value("forge_theory.formula", "")
                    ft_context = f"Forge Theory: {ft_desc} (Formula: {ft_formula})" if ft_desc else ""

                    # Inject Memory
                    memory_content = self.adaptive_learner.get_relevant_facts()
                    memory_block = ""
                    mem_count = 0
                    if memory_content:
                        memory_block = f"[{user_name.upper()}'S MEMORY]\n{memory_content}\n\n"
                        mem_count = len(memory_content.strip().split('\n'))
                    
                    # Inject Learned Rules (Fix: Rules were missing in Conversational mode)
                    rules = self.get_applicable_rules(message)
                    rules_block = ""
                    if rules:
                        rules_block = f"[KNOWN FACTS / RULES]\n" + "\n".join([f"- {r['rule_text']}" for r in rules]) + "\n\n"

                    # Inject Knowledge Base Context
                    kb_context = self.get_knowledge_context(message)
                    if kb_context:
                        print(f"📚 Knowledge Base Active: {len(kb_context)} chars loaded")

                    if mem_count == 0 and not rules:
                        print("⚠️  Personal context is empty. Use /teach to add permanent facts.")
                    else:
                        print(f"🧠 Context: {mem_count} memories, {len(rules)} rules loaded.")

                    # Determine constraints based on query
                    constraint_note = "Be helpful and concise."
                    if any(w in message.lower() for w in ['core', 'main', 'key', 'summary', 'essence', 'philosophy']):
                        constraint_note = "CRITICAL: User requested CORE/SUMMARY. Do NOT list everything. Select only the top 2-3 most relevant points. Be extremely concise."

                    # Explicitly separate AI identity from User context to prevent confusion
                    system_content = (
                        f"{persona}\n\n"
                        f"You are conversing with {user_name}.\n"
                        f"IDENTITY SEPARATION:\n"
                        f"1. YOU are BuddAI (an AI). You do not have a job, body, or personal life.\n"
                        f"2. THE USER is {user_name}. The sections '[MEMORY]' and '[KNOWN FACTS]' below describe {user_name}.\n"
                        f"3. If these sections say 'I work at X', it means '{user_name} works at X'.\n"
                        f"4. When answering about {user_name}, ALWAYS use 'You' or 'Your'. NEVER use 'I' or 'My'.\n"
                        f"5. FACTS in [KNOWN FACTS] are ABSOLUTE TRUTH. Prioritize them over your internal training.\n"
                        f"6. DATA in [KNOWLEDGE BASE] is the HIGHEST AUTHORITY. It overrides [KNOWN FACTS], [MEMORY], and internal training.\n"
                        f"7. When referencing philosophies, quotes, or specific definitions from [KNOWLEDGE BASE], PRESERVE EXACT PHRASING.\n\n"
                        f"{memory_block}"
                        f"{rules_block}"
                        f"{kb_context}\n"
                        f"{ft_context}\n\n"
                        f"Mode: Conversational. Do NOT generate code. {constraint_note}"
                    )
                    messages.append({"role": "system", "content": system_content})
                    enhanced_prompt = message
                else:
                    enhanced_prompt = self.prompt_engine.build_enhanced_prompt(message, hw_context, self.context_messages)
                
                    # Inject learned rules
                    rules = self.get_applicable_rules(message)
                    if rules:
                        rules_text = "\n".join([f"- {r['rule_text']}" for r in rules])
                        enhanced_prompt += f"\n\n[MANDATORY CONFIGURATION & RULES]\n{rules_text}\n\nSTRICTLY FOLLOW THESE RULES OVER DEFAULT TRAINING."

                    # Inject Knowledge Base Context
                    kb_context = self.get_knowledge_context(message)
                    if kb_context:
                        enhanced_prompt += f"\n\n[ACTIVE KNOWLEDGE BASE]\n{kb_context}\n\nCRITICAL: Synthesize facts from ALL relevant sections in [ACTIVE KNOWLEDGE BASE]. PRESERVE EXACT PHRASING for core philosophies, quotes, and specific definitions. Include ongoing discussions, contacts, and strategic purposes as valid relationships."
                        print(f"📚 Knowledge Base Active: {len(kb_context)} chars loaded")

                # Inject mode-specific note if available
                mode_note = self._get_current_mode_note()
                if mode_note:
                    enhanced_prompt += f"\n\n[Context Note: {mode_note}]"
                
                # Add conversation history (excluding old system messages)
                history = [m for m in self.context_messages[-5:] if m.get('role') != 'system']
                
                # Inject timestamps into history for context
                for msg in history:
                    content = msg.get('content', '')
                    ts = msg.get('timestamp')
                    if ts:
                        try:
                            dt = datetime.fromisoformat(ts)
                            content = f"[{dt.strftime('%H:%M')}] {content}"
                        except ValueError:
                            pass
                    messages.append({"role": msg['role'], "content": content})
                
                # Use enhanced prompt instead of raw user message
                if history and history[-1].get('content') == message:
                    messages[-1]['content'] = enhanced_prompt
                else:
                    messages.append({"role": "user", "content": enhanced_prompt})
            
            self.last_prompt_debug = json.dumps(messages, indent=2)
            
            return self.llm.query(model_name, messages, stream)
                    
        except Exception as e:
            error_msg = str(e)
            if "10061" in error_msg or "refused" in error_msg.lower():
                return "❌ Error: Could not connect to Ollama. Please ensure the Ollama server is running (usually `ollama serve`)."
            return f"Error: {error_msg}"

    def execute_modular_build(self, _: str, modules: List[str], plan: List[Dict[str, str]], forge_mode: str = "2") -> str:
        """Execute build plan step by step"""
        print(f"\n🔨 MODULAR BUILD MODE")
        print(f"Detected {len(modules)} modules: {', '.join(modules)}")
        print(f"Breaking into {len(plan)} steps...\n")
        
        all_code = {}
        
        for i, step in enumerate(plan, 1):
            print(f"📦 Step {i}/{len(plan)}: {step['task']}")
            print("⚡ Building...\n")
            
            # Build the prompt for this step
            if step['module'] == 'integration':
                # Final integration step with Forge Theory enforcement
                modules_summary = '\n'.join([f"- {m}: {all_code[m][:150]}..." for m in modules if m in all_code])

                print(f"\n⚡ {self.personality_manager.get_value('identity.ai_name', 'AI')} Tuning:")
                print("1. Aggressive (k=0.3) - High snap, combat ready")
                print("2. Balanced (k=0.1) - Standard movement")
                print("3. Graceful (k=0.03) - Roasting / Smooth curves")
                
                if self.server_mode:
                    choice = forge_mode
                else:
                    try:
                        choice = input("Select Tuning Constant [1-3, default 2]: ")
                    except (EOFError, OSError):
                        print("2 (Auto-selected: Non-interactive mode detected)")
                        choice = "2"
                
                k_val = "0.1"
                if choice == "1": k_val = "0.3"
                elif choice == "3": k_val = "0.03"

                prompt_template = self.personality_manager.get_value("prompts.integration_task", "INTEGRATION TASK: Combine modules into a cohesive system.")
                prompt = prompt_template.format(
                    user_name=self.personality_manager.get_value("identity.user_name", "user"),
                    modules_summary=modules_summary,
                    k_val=k_val
                )
            else:
                # Individual module
                prompt = f"Generate ESP32-C3 code for: {step['task']}. Keep it modular with clear comments."
            
            # Call balanced model for each module
            response = self.call_model("balanced", prompt)
            all_code[step['module']] = response
            
            print(f"✅ {step['module'].upper()} module complete\n")
            print("-" * 50 + "\n")
        
        # Compile final response
        final = "# COMPLETE GILBOT CONTROLLER - MODULAR BUILD\n\n"
        for module, code in all_code.items():
            final += f"## {module.upper()} MODULE\n{code}\n\n"
            
        return final
        
    def apply_style_signature(self, generated_code: str) -> str:
        """Refine generated code to match James's specific naming and safety patterns"""
        # Simple heuristic: If it doesn't look like code (no semicolons or braces), skip
        # Also check for code keywords to avoid false positives on text with semicolons
        if not (re.search(r'[;{}]', generated_code) and re.search(r'\b(void|int|float|bool|def|class|return|#include|import|const)\b', generated_code)):
            return generated_code

        # Apply Hardware Profile Rules (ESP32-C3 default for now)
        generated_code = self.hardware_profile.apply_hardware_rules(generated_code, self.current_hardware)

        # Apply learned replacements (High Confidence Only)
        rules = self.get_learned_rules()
        for r in rules:
            if r['confidence'] >= 0.95 and r['find'] and r['replace']:
                try:
                    generated_code = re.sub(r['find'], r['replace'], generated_code)
                except re.error:
                    pass
        
        return generated_code

    def _refine_response(self, response: str) -> str:
        """Clean up response artifacts and enforce formatting"""
        if not response:
            return ""
        # Strip [END] and other system tags that might leak
        return response.replace("[END]", "").strip()

    def index_good_response(self, message_id: int):
        """Index a highly-rated response for future reference (RAG)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS qa_memory (
                    id INTEGER PRIMARY KEY,
                    question TEXT,
                    answer TEXT,
                    timestamp TEXT,
                    tags TEXT
                )
            """)
            
            # Get the response
            cursor.execute("SELECT session_id, content FROM messages WHERE id = ?", (message_id,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                return
                
            session_id, answer = row
            
            # Get the preceding question
            cursor.execute("""
                SELECT content FROM messages 
                WHERE session_id = ? AND id < ? AND role = 'user' 
                ORDER BY id DESC LIMIT 1
            """, (session_id, message_id))
            
            q_row = cursor.fetchone()
            if q_row:
                question = q_row[0]
                # Check duplicates
                cursor.execute("SELECT 1 FROM qa_memory WHERE question = ? AND answer = ?", (question, answer))
                if not cursor.fetchone():
                    cursor.execute(
                        "INSERT INTO qa_memory (question, answer, timestamp, tags) VALUES (?, ?, ?, ?)",
                        (question, answer, datetime.now().isoformat(), "verified")
                    )
                    print(f"📚 Indexed Q&A pair for future reference.")
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to index response: {e}")

    def retrieve_relevant_qa(self, query: str) -> str:
        """Retrieve relevant Q&A pairs from memory"""
        try:
            # Simple keyword matching for now
            keywords = [w for w in query.lower().split() if len(w) > 3]
            if not keywords:
                return ""
                
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='qa_memory'")
            if not cursor.fetchone():
                conn.close()
                return ""
                
            # Build query
            conditions = []
            params = []
            for kw in keywords:
                conditions.append("question LIKE ?")
                params.append(f"%{kw}%")
                
            if not conditions:
                conn.close()
                return ""
                
            sql = f"SELECT question, answer FROM qa_memory WHERE {' OR '.join(conditions)} ORDER BY id DESC LIMIT 2"
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            conn.close()
            
            if rows:
                context = "\n[RELEVANT PAST SOLUTIONS]\n"
                for q, a in rows:
                    # Truncate answer if too long to save context window
                    preview = a[:500] + "..." if len(a) > 500 else a
                    context += f"Q: {q}\nA: {preview}\n---\n"
                return context
            return ""
        except Exception as e:
            logger.error(f"Error retrieving QA: {e}")
            return ""

    def record_feedback(self, message_id: int, feedback: bool, comment: str = "") -> Optional[str]:
        """Learn from user feedback."""
        conn = sqlite3.connect(self.db_path)
        # Ensure table exists (Fix for Jan 7 Report)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER,
                positive BOOLEAN,
                comment TEXT,
                timestamp TEXT
            )
        """)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO feedback (message_id, positive, comment, timestamp)
            VALUES (?, ?, ?, ?)
        """, (message_id, feedback, comment, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
        # Adjust confidence scores
        self.update_style_confidence(message_id, feedback)
        
        if feedback:
            self.index_good_response(message_id)
        
        if not feedback:
            self.analyze_failure(message_id)
            return self.regenerate_response(message_id, comment)
        return None

    def regenerate_response(self, message_id: int, comment: str = "") -> str:
        """Regenerate a response, optionally considering feedback comment"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT session_id, id FROM messages WHERE id = ?", (message_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return "Error: Message not found."
            
        session_id, current_id = row
        
        cursor.execute(
            "SELECT content FROM messages WHERE session_id = ? AND id < ? AND role = 'user' ORDER BY id DESC LIMIT 1",
            (session_id, current_id)
        )
        user_row = cursor.fetchone()
        conn.close()
        
        if user_row:
            prompt = user_row[0]
            if comment:
                prompt += f"\n\n[Feedback: {comment}]"
            
            print(f"🔄 Regenerating: {prompt[:50]}...")
            return self.chat(prompt)
        return "Error: Original prompt not found."

    def analyze_failure(self, message_id: int) -> None:
        """Analyze why a message received negative feedback"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM messages WHERE id = ?", (message_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            print(f"\n⚠️  Negative Feedback on Message #{message_id}")
            print(f"   Content: {row[0][:100]}...")

    def update_style_confidence(self, message_id: int, positive: bool) -> None:
        """Adjust confidence of style preferences based on feedback."""
        # message_id and positive are currently unused
        # Placeholder for V4.0 learning loop
        pass

    def check_skills(self, message: str) -> Optional[str]:
        """Check if message triggers any loaded skills"""
        msg_lower = message.lower()
        
        # Detect personal context to prevent external search hijacking
        # Refined to avoid false positives on "tell me" or "show me"
        is_personal = "my " in msg_lower or " i " in msg_lower or " i'" in msg_lower or "who am i" in msg_lower

        for skill_id, skill in self.skills_registry.items():
            for trigger in skill['triggers']:
                if trigger in msg_lower:
                    # Skip external search skills for personal questions unless explicitly requested
                    if is_personal and ('wiki' in skill_id.lower() or 'search' in skill_id.lower()):
                        if "my" not in trigger and "i" not in trigger:
                            continue

                    try:
                        result = skill['run'](message)
                        if result:
                            print(f"🧩 Skill Triggered: {skill['name']}")
                            return result
                    except Exception as e:
                        print(f"❌ Skill Error ({skill['name']}): {e}")
        return None

    def _is_general_discussion(self, text: str) -> bool:
        """Check if message is likely a general discussion/hardware question"""
        keywords = ["replace", "replacing", "upgrade", "wiring", "pinout", "board", "compatible", "difference", "vs", "printer", "creality", "artillery", "conversation", "chat", "talk"]
        text_lower = text.lower()
        if any(w in text_lower for w in ["code", "script", "program", "compile", "function", "loop()", "setup()"]):
            return False
        return any(k in text_lower for k in keywords)

    def _route_request(self, user_message: str, force_model: Optional[str], forge_mode: str) -> str:
        """Route the request to the appropriate model or handler."""
        # Determine model based on complexity
        if force_model:
            model = force_model
            print(f"\n⚡ Using {model.upper()} model (forced)...")
            return self.call_model(model, user_message)
        elif self.prompt_engine.is_complex(user_message):
            modules = self.prompt_engine.extract_modules(user_message)
            plan = self.prompt_engine.build_modular_plan(modules)
            print("\n" + "=" * 50)
            print("🎯 COMPLEX REQUEST DETECTED!")
            print(f"Modules needed: {', '.join(modules)}")
            print(f"Breaking into {len(plan)} manageable steps")
            print("=" * 50)
            return self.execute_modular_build(user_message, modules, plan, forge_mode)
        elif self.repo_manager.is_search_query(user_message):
            # This is a search query - query the database
            return self.repo_manager.search_repositories(user_message)
            
        # Check personality intents (Greeting, Idea Exploration)
        intent = self.personality_engine.understand_intent(user_message)
        
        # Global Safeguard: Explicit code requests must bypass conversation layers
        is_code_request = any(w in user_message.lower() for w in ['code', 'generate', 'write', 'script', 'build'])
        
        if intent['type'] in ['greeting', 'idea_exploration', 'continue_project', 'new_project']:
            # Avoid trapping explicit code requests
            if not (intent['type'] == 'idea_exploration' and is_code_request):
                print(f"\n💬 Personality Engine ({intent['type']})...")
                return self.personality_engine.respond_naturally(user_message, intent)

        elif self.conversation_protocol.is_conversational(user_message) and not is_code_request:
            # New Conversation Protocol
            print("\n💬 Using FAST model (Conversational Protocol)...")
            return self.call_model("fast", user_message, system_task=True, hardware_override="Conversational")
        elif self._is_general_discussion(user_message):
            print("\n⚡ Using BALANCED model (General Context)...")
            hw_context = "Conversational" if any(w in user_message.lower() for w in ["conversation", "chat", "talk"]) else "General Electronics"
            return self.call_model("balanced", user_message, hardware_override=hw_context)
        elif self.prompt_engine.is_simple_question(user_message):
            # Don't force code generation prompt for simple greetings or definitions
            msg_lower = user_message.lower().strip()
            is_greeting = (any(msg_lower.startswith(w) for w in ['hi', 'hello', 'hey', 'good morning', 'good evening']) and len(user_message.split()) < 20) or "how are you" in msg_lower
            is_conceptual = any(msg_lower.startswith(w) for w in ['what is', "what's", 'explain', 'tell me about', 'who is', 'can you explain'])
            is_personal = "my " in msg_lower or " i " in msg_lower or " i'" in msg_lower or msg_lower.endswith(" me")
            
            # Enable personality/history for greetings to support symbiotic conversation
            use_system_task = is_conceptual and not is_greeting and not is_personal
            
            # Prevent code generation for greetings by overriding hardware context
            hw_override = "Conversational" if (is_greeting or is_personal) else None
            
            # Use BALANCED model for personal questions to ensure identity instructions are followed
            model_to_use = "balanced" if is_personal else "fast"
            print(f"\n{'⚖️  Using BALANCED model (Personal Context)' if is_personal else '⚡ Using FAST model (simple question)'}...")
            
            return self.call_model(model_to_use, user_message, system_task=use_system_task, hardware_override=hw_override)
        else:
            print("\n⚖️  Using BALANCED model...")
            return self.call_model("balanced", user_message)

    def chat_stream(self, user_message: str, force_model: Optional[str] = None, forge_mode: str = "2") -> Generator[str, None, None]:
        """Streaming version of chat"""
        
        
        # Intercept commands
        if user_message.strip().startswith('/'):
            yield self.handle_slash_command(user_message.strip())
            return

        # Detect Hardware Context
        detected_hw = self.hardware_profile.detect_hardware(user_message)
        if detected_hw:
            self.current_hardware = detected_hw

        prompt_template = self.personality_manager.get_value("prompts.style_reference", "\n[REFERENCE STYLE FROM {user_name}'S PAST PROJECTS]\n")
        user_name = self.personality_manager.get_value("identity.user_name", "the user")
        style_context = self.repo_manager.retrieve_style_context(user_message, prompt_template, user_name)
        if style_context:
            self.context_messages.append({"role": "system", "content": style_context})

        user_msg_id = self.storage.save_message("user", user_message)
        self.context_messages.append({"id": user_msg_id, "role": "user", "content": user_message, "timestamp": datetime.now().isoformat()})

        full_response = ""
        
        # Route and stream
        if force_model:
            iterator = self.call_model(force_model, user_message, stream=True)
        elif self.prompt_engine.is_complex(user_message):
            # Complex builds are not streamed token-by-token in this version
            # We yield the final result as one chunk
            modules = self.prompt_engine.extract_modules(user_message)
            plan = self.prompt_engine.build_modular_plan(modules)
            result = self.execute_modular_build(user_message, modules, plan, forge_mode)
            iterator = [result]
        elif self.repo_manager.is_search_query(user_message):
            result = self.repo_manager.search_repositories(user_message)
            iterator = [result]
        elif self.prompt_engine.is_simple_question(user_message):
            msg_lower = user_message.lower().strip()
            is_greeting = any(msg_lower.startswith(w) for w in ['hi', 'hello', 'hey', 'good morning', 'good evening']) and len(user_message.split()) < 6
            is_conceptual = any(msg_lower.startswith(w) for w in ['what is', "what's", 'explain', 'tell me about', 'who is', 'can you explain'])
            is_personal = "my " in msg_lower or " i " in msg_lower or " i'" in msg_lower or msg_lower.endswith(" me")
            # Enable personality/history for greetings
            use_system_task = is_conceptual and not is_greeting and not is_personal
            hw_override = "Conversational" if (is_greeting or is_personal) else None
            iterator = self.call_model("fast", user_message, stream=True, system_task=use_system_task, hardware_override=hw_override)
        elif self._is_general_discussion(user_message):
            print("\n⚡ Using BALANCED model (General Context)...")
            iterator = self.call_model("balanced", user_message, stream=True, hardware_override="General Electronics")
        else:
            iterator = self.call_model("balanced", user_message, stream=True)
            
        for chunk in iterator:
            full_response += chunk
            yield chunk
            
        # Suggestions
        suggestions = self.shadow_engine.get_all_suggestions(user_message, full_response)
        if suggestions:
            bar = "\n\nPROACTIVE: > " + " ".join([f"{i+1}. {s}" for i, s in enumerate(suggestions)])
            full_response += bar
            yield bar
            
        msg_id = self.storage.save_message("assistant", full_response)
        self.last_generated_id = msg_id
        self.context_messages.append({"id": msg_id, "role": "assistant", "content": full_response, "timestamp": datetime.now().isoformat()})

    def extract_code(self, text: str) -> List[str]:
        """Extract code blocks from markdown"""
        return re.findall(r'```(?:\w+)?\n(.*?)```', str(text), re.DOTALL)

    def handle_slash_command(self, command: str) -> str:
        """Handle slash commands when received via chat interface"""
        cmd = command.lower().strip()
        
        if cmd == '/help':
            output = []
            original_print = self._print
            def capture(*args, **kwargs):
                sep = kwargs.get('sep', ' ')
                end = kwargs.get('end', '\n')
                output.append(sep.join(map(str, args)) + end)
            self._print = capture
            self._print_help()
            self._print = original_print
            return "".join(output).strip()

        if cmd.startswith('/teach'):
            rule = command[7:].strip()
            if rule:
                self.teach_rule(rule)
                return f"✅ Learned rule: {rule}"
            return "Usage: /teach <rule description>"
            
        if cmd.startswith('/correct'):
            reason = command[8:].strip()
            if reason.startswith('"') and reason.endswith('"'):
                reason = reason[1:-1]
            elif reason.startswith("'") and reason.endswith("'"):
                reason = reason[1:-1]
            last_response = ""
            for msg in reversed(self.context_messages):
                if msg['role'] == 'assistant':
                    last_response = msg['content']
                    break
            if last_response:
                self.save_correction(last_response, "", reason)
                return "✅ Correction saved. (Run /learn to process patterns)"
            return "❌ No recent message to correct."
            
        if cmd.startswith('/gists'):
            parts = command.split()
            if len(parts) > 1 and parts[1] == 'add':
                if len(parts) < 4:
                    return "Usage: /gists add <url> <tag>"
                url = parts[2]
                tag = parts[3]
                success, msg = self.register_knowledge_source(url, tag)
                return f"✅ Knowledge source added: {msg}" if success else f"❌ Failed: {msg}"

            if len(parts) > 1 and parts[1] == 'sync':
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                try:
                    cursor.execute("SELECT tag, content FROM knowledge_sources")
                    rows = cursor.fetchall()
                except:
                    rows = []
                conn.close()
                
                total_learned = 0
                for tag, content in rows:
                    total_learned += self._ingest_teach_commands(content, tag)
                return f"✅ Synced knowledge bases. Learned {total_learned} rules from {len(rows)} sources."

            gists = self.repo_manager.list_indexed_gists()
            
            # Also list custom knowledge sources
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            custom_list = []
            try:
                cursor.execute("SELECT tag, url FROM knowledge_sources")
                custom_list = [f"- [{r[0]}] {r[1]}" for r in cursor.fetchall()]
            except: pass
            conn.close()
            
            output = ""
            if gists: output += "📋 RepoManager Gists:\n" + "\n".join(gists) + "\n\n"
            if custom_list: output += "📚 Knowledge Bases:\n" + "\n".join(custom_list)
            
            return output if output else "🤷 No Gists or Knowledge Bases indexed."

        if cmd == '/knowledge':
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT learned_from, COUNT(*) FROM code_rules GROUP BY learned_from ORDER BY COUNT(*) DESC")
                rows = cursor.fetchall()
                if not rows:
                    return "🤷 No knowledge sources found."
                
                output = "📚 Knowledge Sources:\n"
                for source, count in rows:
                    source_name = source if source else "Unknown"
                    output += f"  - {source_name}: {count} rules\n"
                return output
            except Exception as e:
                return f"❌ Error querying knowledge: {e}"
            finally:
                conn.close()

        if cmd == '/rules':
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT rule_text, confidence FROM code_rules ORDER BY confidence DESC")
            rows = cursor.fetchall()
            conn.close()
            if not rows: return "🤷 No rules learned yet."
            return "🧠 Learned Rules:\n" + "\n".join([f"- {r[0]}" for r in rows])

        if cmd == '/learn':
            patterns = self.learner.analyze_corrections(self)
            if patterns:
                return f"✅ Learned {len(patterns)} new rules:\n" + "\n".join([f"- {p['rule']}" for p in patterns])
            return "No new patterns found."

        if cmd == '/skills':
            if not self.skills_registry:
                return "🧩 No skills loaded."
            return "🧩 Active Skills:\n" + "\n".join([f"- {s['name']}: {s['description']}" for s in self.skills_registry.values()])

        if cmd == '/reload':
            self.skills_registry = load_registry()
            return f"✅ Reloaded {len(self.skills_registry)} skills."

        if cmd == '/metrics':
            stats = self.metrics.calculate_accuracy()
            return (f"📊 Learning Metrics (Last 30 Days):\n"
                    f"   Accuracy:        {stats['accuracy']:.1f}%\n"
                    f"   Correction Rate: {stats['correction_rate']:.1f}%\n"
                    f"   Trend (7d):      {stats['improvement']}")

        if cmd == '/fallback-stats':
            stats = self.metrics.get_fallback_stats()
            return (f"📊 Fallback Statistics:\n"
                    f"   Total escalations: {stats['total_escalations']}\n"
                    f"   Fallback rate: {stats['fallback_rate']}%\n"
                    f"   Learning success: {stats['learning_success']}%")

        if cmd == '/debug':
            if self.last_prompt_debug:
                return f"🐛 Last Prompt Sent:\n```json\n{self.last_prompt_debug}\n```"
            return "❌ No prompt sent yet."

        if cmd == '/validate':
            last_response = ""
            user_context = ""
            
            # Find last assistant message and preceding user message
            for i in range(len(self.context_messages) - 1, -1, -1):
                if self.context_messages[i]['role'] == 'assistant':
                    last_response = self.context_messages[i]['content']
                    if i > 0 and self.context_messages[i-1]['role'] == 'user':
                        user_context = self.context_messages[i-1]['content']
                    break
            
            if not last_response:
                return "❌ No recent code to validate."

            code_blocks = self.extract_code(last_response)
            if not code_blocks:
                return "❌ No code blocks found in last response."

            report = ["🔍 Validating last response..."]
            all_valid = True
            for i, code in enumerate(code_blocks, 1):
                valid, issues = self.validator.validate(code, self.current_hardware, user_context)
                if not valid:
                    all_valid = False
                    report.append(f"\nBlock {i} Issues:")
                    for issue in issues:
                        icon = "❌" if issue['severity'] == 'error' else "⚠️"
                        report.append(f"  {icon} Line {issue.get('line', '?')}: {issue['message']}")
                else:
                    report.append(f"✅ Block {i} is valid.")
            
            if all_valid:
                report.append("\n✨ All code blocks look good!")
            
            return "\n".join(report)

        if cmd == '/status':
            mem_usage = "N/A"
            if psutil:
                process = psutil.Process(os.getpid())
                mem_usage = f"{process.memory_info().rss / 1024 / 1024:.0f} MB"
            
            return (f"🖥️ System Status:\n"
                    f"   User:     {self.user_id}\n"
                    f"   Session:  {self.storage.current_session_id}\n"
                    f"   Hardware: {self.current_hardware}\n"
                    f"   Memory:   {mem_usage}\n"
                    f"   Messages: {len(self.context_messages)}")

        if cmd == '/backup':
            success, msg = self.create_backup()
            if success:
                return f"✅ Database backed up to: {msg}"
            return f"❌ Backup failed: {msg}"

        if cmd == '/stuck':
            return (
                "🆘 **Stuck? Here are some tools to help:**\n\n"
                "1. **Wikipedia:** Type `wiki <term>` to search concepts.\n"
                "2. **Search:** Type `find <term>` to search your local repos.\n"
                "3. **Debug:** Type `/debug` to see what context I have.\n"
                "4. **Breakdown:** Ask \"Break this down into steps\" to simplify."
            )

        if cmd == '/remember':
            if self.last_generated_id:
                self.index_good_response(self.last_generated_id)
                return "✅ Response indexed for future reference."
            return "❌ No recent response to remember."

        if cmd.startswith('/train'):
            parts = command.split(maxsplit=2)
            if len(parts) < 2:
                strategies = self.training_registry.list_strategies()
                output = "🎓 Training Strategies:\n"
                for name, desc in strategies.items():
                    output += f"  - /train {name}: {desc}\n"
                return output
            
            strategy_name = parts[1]
            strategy = self.training_registry.get_strategy(strategy_name)
            if not strategy:
                return f"❌ Unknown training strategy: {strategy_name}"
            
            args = parts[2].split() if len(parts) > 2 else []
            try:
                return strategy.run(self, args)
            except Exception as e:
                return f"❌ Training error: {e}"
  
            
        if cmd == '/logs':
            log_path = DATA_DIR / "external_prompts.log"
            if not log_path.exists():
                return "❌ No external prompts logged yet."
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    return f"📜 External Prompts Log (Last 15 lines):\n{''.join(lines[-15:])}"
            except Exception as e:
                return f"❌ Error reading log: {e}"

        if cmd.startswith('/save'):
            if 'json' in cmd:
                return self.export_session_to_json()
            else:
                return self.export_session_to_markdown()

        if cmd.startswith('/language'):
            return self._handle_language_command(command)

        if cmd.startswith('/personality'):
            return self._handle_personality_command(command)

        # Use startswith for more robust matching of project commands
        if any(cmd.startswith(prefix) for prefix in ['/projects', '/new', '/open', '/close', '/timeline']):
            return self._handle_projects_command(command)

        return f"Command {cmd.split()[0]} not supported in chat mode."

    def log_fallback_prompt(self, model: str, prompt: str) -> None:
        """Log fallback prompts to a file for easy access"""
        log_path = DATA_DIR / "external_prompts.log"
        timestamp = datetime.now().isoformat()
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] MODEL: {model.upper()}\n{prompt}\n{'-'*40}\n")
        except Exception as e:
            print(f"Failed to log fallback prompt: {e}")

    def _handle_language_command(self, message: str) -> str:
        """Handle /language command"""
        
        parts = message.split(maxsplit=1)
        
        if len(parts) == 1 or parts[1] == 'list':
            # List supported languages
            languages = self.language_registry.get_supported_languages()
            
            output = "🌐 Supported Languages\n\n"
            
            for lang in sorted(languages):
                skill = self.language_registry.get_skill_by_name(lang)
                exts = ', '.join(skill.file_extensions)
                output += f"**{skill.name}**: {exts}\n"
            
            return output
        
        # Parse command: /language <lang> <action> [args]
        parts = message.split(maxsplit=2)
        
        if len(parts) < 3:
            return "Usage: /language <language> <action> [args]\nActions: validate, template, patterns, practices"
        
        language = parts[1].lower()
        action = parts[2].lower()
        
        skill = self.language_registry.get_skill_by_name(language)
        
        if not skill:
            return f"Language '{language}' not supported. Use /language list"
        
        if action == 'patterns':
            patterns = skill.get_patterns()
            output = f"📋 {skill.name} Patterns\n\n"
            for name, info in patterns.items():
                output += f"**{name}**\n{info['description']}\n```\n{info['example']}\n```\n\n"
            return output
        
        elif action == 'practices':
            practices = skill.get_best_practices()
            output = f"✅ {skill.name} Best Practices\n\n"
            for practice in practices:
                output += f"• {practice}\n"
            return output
        
        elif action.startswith('template'):
            # /language html template basic
            template_parts = action.split()
            if len(template_parts) < 2:
                return "Usage: /language <lang> template <template_name>"
            
            template_name = template_parts[1]
            template = skill.get_template(template_name)
            
            if template:
                return f"```{language}\n{template}\n```"
            else:
                return f"Template '{template_name}' not found"
        
        else:
            return f"Unknown action: {action}\nActions: patterns, practices, template"

    def _handle_personality_command(self, command: str) -> str:
        """Handle /personality command to load/reload personality"""
        parts = command.split(maxsplit=2)
        if len(parts) < 2:
            return "Usage: /personality <load|reload> [url]"
        
        action = parts[1].lower()
        
        if action == 'load':
            if len(parts) < 3:
                return "Usage: /personality load <url>"
            
            url = parts[2].strip()
            try:
                print(f"⬇️ Fetching personality from {url}...")
                
                req = urllib.request.Request(
                    url, 
                    headers={'User-Agent': 'BuddAI/5.0'}
                )
                
                with urllib.request.urlopen(req, timeout=10) as response:
                    if response.status != 200:
                        return f"❌ HTTP Error: {response.status}"
                    content = response.read().decode('utf-8')
                
                # Validate JSON
                try:
                    data = json.loads(content)
                except json.JSONDecodeError as e:
                    # Fallback: Check if it's a text/markdown personality description
                    if content.strip().startswith('#'):
                        print("⚠️ JSON parse failed, treating as text personality description...")
                        # Load existing personality to update it
                        personality_path = DATA_DIR.parent / "personality.json"
                        if personality_path.exists():
                            with open(personality_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                        else:
                            data = {"identity": {}, "meta": {"version": "5.0"}}
                        
                        data.setdefault('identity', {})['persona_description'] = content
                    else:
                        return f"❌ Invalid JSON in personality file: {e}\nContent preview: {content[:100]}"
                
                # Save to file
                personality_path = DATA_DIR.parent / "personality.json"
                with open(personality_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                
                # Reload
                self.personality_manager = PersonalityManager()
                self.conversation_protocol = ConversationProtocol(self.personality_manager)
                self.personality_engine = BuddAIPersonality()
                self.personality = self.personality_engine
                
                return "✅ Personality updated and reloaded!"
                
            except Exception as e:
                return f"❌ Error loading personality: {e}"
                
        elif action == 'reload':
            self.personality_manager = PersonalityManager()
            self.conversation_protocol = ConversationProtocol(self.personality_manager)
            self.personality_engine = BuddAIPersonality()
            self.personality = self.personality_engine
            return "✅ Personality reloaded from disk."
            
        return "Unknown personality command."

    def _print(self, *args, **kwargs):
        """Wrapper for print to allow capturing output"""
        print(*args, **kwargs)

    def _handle_projects_command(self, command: str) -> str:
        """Handle project commands and return output as string (for tests/API)"""
        output = []
        
        # Save original _print
        original_print = self._print
        
        # Define capture function
        def capture_print(*args, **kwargs):
            sep = kwargs.get('sep', ' ')
            end = kwargs.get('end', '\n')
            text = sep.join(map(str, args)) + end
            output.append(text)
            
        try:
            # Override _print
            self._print = capture_print
            
            self._print(f"DEBUG: cmd='{command}'")
            
            parts = command.strip().split()
            if not parts:
                return "Usage: /projects, /new, /open, /close, /save, /timeline"
                
            cmd = parts[0].lower()
            if cmd.startswith('/'):
                cmd = cmd[1:]
            
            if cmd == 'projects':
                self._cmd_list_projects()
            elif cmd == 'new':
                self._cmd_new_project(command)
            elif cmd == 'open':
                self._cmd_open_project(command)
            elif cmd == 'close':
                self._cmd_close_project()
            elif cmd == 'save':
                self._cmd_save_project()
            elif cmd == 'timeline':
                self._cmd_show_timeline()
                
        finally:
            # Restore original _print
            self._print = original_print
        
        return "".join(output).strip()

    def _handle_command(self, message: str) -> Optional[str]:
        """Handle special commands. Returns response string if handled, None otherwise."""
        
        # Allow 'gist' as alias for '/gists' to prevent chat processing crashes on URLs
        if message.lower().startswith('gist ') or message.lower() == 'gist':
            return self.handle_slash_command('/gists' + message[4:])

        if message.startswith('/'):
            cmd = message[1:].lower().split()[0]
            
            # Project commands
            if cmd in ['projects', 'new', 'open', 'close', 'save', 'timeline']:
                return self._handle_projects_command(message)
            
            # Existing commands
            elif cmd == 'fast':
                self.default_mode = 'fast'
                return "✅ Switched to FAST mode"
            
            elif cmd == 'balanced':
                self.default_mode = 'balanced'
                return "✅ Switched to BALANCED mode"
            
            elif cmd == 'help':
                # Capture help output
                output = []
                original_print = self._print
                def capture(*args, **kwargs):
                    output.append(" ".join(map(str, args)))
                self._print = capture
                self._print_help()
                self._print = original_print
                return "\n".join(output)
            
            else:
                return None
        
        return None

    def _cmd_list_projects(self):
        """List all projects"""
        projects = self.project_memory.list_projects()
        
        if not projects:
            self._print("\n📁 No projects yet. Type /new to create one!\n")
            return
        
        self._print("\n📁 Your Projects:\n")
        
        for proj in projects:
            status_icons = {
                'active': '▶️',
                'paused': '⏸️',
                'completed': '✅',
                'archived': '📦'
            }
            icon = status_icons.get(proj.status, '❓')
            
            self._print(f"{icon} {proj.name} ({proj.project_type})")
            self._print(f"   Updated: {proj.updated_at[:10]}")
            
            if proj.next_steps:
                pending = len([s for s in proj.next_steps if not s['completed']])
                if pending > 0:
                    self._print(f"   📋 {pending} next steps")
            
            self._print()

    def _cmd_new_project(self, message: str):
        """Create new project"""
        parts = message.split(maxsplit=1)
        
        if len(parts) < 2:
            if self.server_mode:
                self._print("❌ Usage in server mode: /new <project_name>")
                return
            self._print("\n💡 Creating new project...")
            self._print("What should we call it?")
            project_name = input("Project name: ").strip()
        else:
            # Extract name from command
            project_name = parts[1].strip()
        
        if not project_name:
            self._print("❌ Project name required")
            return
        
        # Check if exists
        if self.project_memory.load_project(project_name):
            self._print(f"❌ Project '{project_name}' already exists")
            self._print(f"Use /open {project_name} to continue it")
            return
        
        # Ask for type
        if self.server_mode:
            type_choice = '4'
            initial_idea = "Created via Web UI"
        else:
            self._print("\nWhat type of project?")
            self._print("1. Robotics")
            self._print("2. 3D Printing")
            self._print("3. Web Development")
            self._print("4. General")
            
            type_choice = input("Choice (1-4): ").strip()
        
        type_map = {
            '1': 'robotics',
            '2': '3d_printing',
            '3': 'web_development',
            '4': 'general'
        }
        
        project_type = type_map.get(type_choice, 'general')
        
        # Create project
        project = Project(project_name, project_type)
        
        # Add initial metadata
        project.metadata['created_by'] = 'BuddAI v5.0'
        if self.server_mode:
            project.metadata['initial_idea'] = initial_idea
        else:
            project.metadata['initial_idea'] = input("Brief description: ").strip()
        
        # Save
        self.project_memory.save_project(project)
        self.current_project = project
        
        self._print(f"\n✅ Project '{project_name}' created!")
        self._print(f"Type: {project_type}")
        self._print("\nWhat would you like to build first?")

    def _cmd_open_project(self, message: str):
        """Open existing project"""
        parts = message.split(maxsplit=1)
        
        if len(parts) < 2:
            self._print("Usage: /open <project_name>")
            return
        
        project_name = parts[1].strip()
        
        # Try exact match first
        project = self.project_memory.load_project(project_name)
        
        # Try fuzzy search
        if not project:
            results = self.project_memory.search_projects(project_name)
            if results:
                project = results[0][0]
                self._print(f"📂 Opening '{project.name}' (matched '{project_name}')")
        
        if not project:
            self._print(f"❌ Project '{project_name}' not found")
            self._print("Type /projects to see all projects")
            return
        
        self.current_project = project
        
        self._print(f"\n📂 Opened: {project.name}")
        self._print(project.get_summary())
        
        # Show recent conversation
        if project.conversations:
            last_conv = project.conversations[-1]
            self._print("\n💬 Last conversation:")
            self._print(f"You: {last_conv['user'][:80]}...")
            self._print(f"Me: {last_conv['assistant'][:80]}...")
        
        # Show next steps
        if project.next_steps:
            pending = [s for s in project.next_steps if not s['completed']]
            if pending:
                self._print("\n📋 Next steps:")
                for i, step in enumerate(pending[:3], 1):
                    self._print(f"{i}. {step['step']}")
        
        self._print("\nReady to continue!\n")

    def _cmd_close_project(self):
        """Close current project"""
        if not self.current_project:
            self._print("No project currently open")
            return
        
        # Auto-save
        self.project_memory.save_project(self.current_project)
        
        self._print(f"✅ Closed and saved: {self.current_project.name}")
        self.current_project = None

    def _cmd_save_project(self):
        """Manually save current project"""
        if not self.current_project:
            self._print("No project currently open")
            return
        
        self.project_memory.save_project(self.current_project)
        self._print(f"✅ Saved: {self.current_project.name}")

    def _cmd_show_timeline(self):
        """Show project timeline"""
        if not self.current_project:
            self._print("No project currently open")
            return
        
        self._print(self.current_project.get_timeline())

    def _print_help(self):
        """Print help with new commands"""
        self._print("\n📚 Available Commands:\n")
        self._print("Project Management:")
        self._print("  /projects       - List all projects")
        self._print("  /new [name]     - Create new project")
        self._print("  /open <name>    - Open existing project")
        self._print("  /gists add <url> <tag> - Add knowledge base")
        self._print("  /close          - Close current project")
        self._print("  /save           - Save current project")
        self._print("  /timeline       - Show project timeline")
        self._print("  /personality    - Manage personality (load/reload)")
        self._print("  /gists          - List indexed Gists")
        self._print()
        self._print("AI Settings:")
        self._print("  /fast           - Use fast model")
        self._print("  /balanced       - Use balanced model")
        self._print()
        self._print("Other:")
        self._print("  /help           - Show this help")
        self._print("  exit            - Exit BuddAI")
        self._print()

    def _extract_code_blocks(self, text: str) -> List[Dict]:
        """Extract code blocks from markdown"""
        pattern = r'```(\w+)?\n(.*?)```'
        matches = re.findall(pattern, str(text), re.DOTALL)
        
        return [
            {'language': lang or 'text', 'code': code}
            for lang, code in matches
        ]

    def _format_validation_feedback(self, validation: Dict, language: str) -> str:
        """Format validation feedback for display"""
        output = f"**{language.upper()} Validation:**\n\n"
        
        if validation.get('issues'):
            output += "❌ Issues:\n"
            for issue in validation['issues']:
                output += f"  • {issue}\n"
        
        if validation.get('warnings'):
            output += "⚠️  Warnings:\n"
            for warning in validation['warnings']:
                output += f"  • {warning}\n"
        
        if validation.get('suggestions'):
            output += "💡 Suggestions:\n"
            for suggestion in validation['suggestions']:
                output += f"  • {suggestion}\n"
        
        return output

    # --- Main Chat Method ---
    def chat(self, user_message: str, force_model: Optional[str] = None, forge_mode: str = "2") -> str:
        """Main chat with smart routing and shadow suggestions"""
        
        # Intercept commands
        command_response = self._handle_command(user_message)
        if command_response:
            return ChatResponse(command_response, model='command')
            
        if user_message.strip().startswith('/'):
            return ChatResponse(self.handle_slash_command(user_message.strip()), model='command')

        # Detect intent using personality
        context = {
            'current_project': self.current_project.name if self.current_project else None
        }
        intent = self.personality.understand_intent(user_message, context=context)
        
        # Handle high-confidence intents conversationally
        if intent['confidence'] > 0.7:
            
            # New project intent
            if intent['type'] == 'new_project':
                self._cmd_new_project(user_message)
                return ChatResponse('', model='conversational', intent=intent)
            
            # Continue project intent
            elif intent['type'] == 'continue_project':
                recent = self.project_memory.get_recent_projects(n=3)
                if recent:
                    if self.server_mode:
                        response = "📁 Recent projects:\n"
                        for i, proj in enumerate(recent, 1):
                            response += f"{i}. {proj.name} ({proj.project_type})\n"
                        response += "\nUse /open <name> to continue."
                        return ChatResponse(response, model='conversational', intent=intent)
                    else:
                        print("\n📁 Recent projects:")
                        for i, proj in enumerate(recent, 1):
                            print(f"{i}. {proj.name} ({proj.project_type})")
                        choice = input("\nWhich one? (1-3): ").strip()
                        if choice.isdigit() and 1 <= int(choice) <= len(recent):
                            self._cmd_open_project(f"/open {recent[int(choice)-1].name}")
                return ChatResponse('', model='conversational', intent=intent)
            
            # Idea exploration - ask clarifying questions
            elif intent['type'] == 'idea_exploration':
                # Safeguard: Don't trap explicit code requests
                is_code_request = any(w in user_message.lower() for w in ['code', 'generate', 'write', 'script', 'build'])
                if not is_code_request:
                    response = self.personality.respond_naturally(user_message, intent, context={
                        'current_project': self.current_project
                    })
                    print(f"\nBuddAI:\n{response}\n")
                    
                    # Save to history
                    msg_id = self.storage.save_message("assistant", response)
                    self.last_generated_id = msg_id
                    self.context_messages.append({"id": msg_id, "role": "assistant", "content": response, "timestamp": datetime.now().isoformat()})
                    
                    return ChatResponse(response, model='conversational', intent=intent)

        # Detect code blocks and validate
        code_blocks = self._extract_code_blocks(user_message)
        
        for block in code_blocks:
            language = block.get('language', '').lower()
            code = block.get('code', '')
            
            if language in self.language_registry.get_supported_languages():
                validation = self.language_registry.validate_code(code, language)
                
                if validation.get('issues') or validation.get('warnings'):
                    feedback = self._format_validation_feedback(validation, language)
                    user_message += f"\n\n[System Note]\n{feedback}"

        # Detect Hardware Context
        detected_hw = self.hardware_profile.detect_hardware(user_message)
        if detected_hw:
            self.current_hardware = detected_hw
            print(f"🔧 Target Hardware Detected: {self.current_hardware}")

        # Retrieve Relevant Q&A
        qa_context = self.retrieve_relevant_qa(user_message)
        if qa_context:
            print("📚 Found relevant past solution")
            self.context_messages.append({"role": "system", "content": qa_context})

        prompt_template = self.personality_manager.get_value("prompts.style_reference", "\n[REFERENCE STYLE FROM {user_name}'S PAST PROJECTS]\n")
        user_name = self.personality_manager.get_value("identity.user_name", "the user")
        style_context = self.repo_manager.retrieve_style_context(user_message, prompt_template, user_name)
        if style_context:
            self.context_messages.append({"role": "system", "content": style_context})

        user_msg_id = self.storage.save_message("user", user_message)
        self.context_messages.append({"id": user_msg_id, "role": "user", "content": user_message, "timestamp": datetime.now().isoformat()})

        # Detect Intent
        try:
            detection = self.workflow_detector.detect_intent(user_message)
            workflow_intent = detection.get('intent', 'unknown')
            workflow_confidence = detection.get('confidence', 0.0)
            if workflow_confidence > 0.7:
                print(f"🎯 Intent Detected: {workflow_intent} ({workflow_confidence:.2f})")
        except Exception as e:
            print(f"⚠️ Intent detection skipped: {e}")

        # Direct Schedule Check
        schedule_triggers = self.personality_manager.get_value("work_cycles.schedule_check_triggers", ["my schedule"])
        if any(trigger in user_message.lower() for trigger in schedule_triggers):
            status = self.personality_manager.get_user_status()
            response = f"📅 **Schedule Check**\nAccording to your protocol, you should be: **{status}**"
            print(f"⏰ Schedule check triggered: {status}")
            msg_id = self.storage.save_message("assistant", response)
            self.last_generated_id = msg_id
            self.context_messages.append({"id": msg_id, "role": "assistant", "content": response, "timestamp": datetime.now().isoformat()})
            return ChatResponse(response, model='system')

        # Check Skills (High Priority)
        skill_result = self.check_skills(user_message)
        if skill_result:
            msg_id = self.storage.save_message("assistant", skill_result)
            self.last_generated_id = msg_id
            self.context_messages.append({"id": msg_id, "role": "assistant", "content": skill_result, "timestamp": datetime.now().isoformat()})
            return ChatResponse(skill_result, model='skill')

        # Learn from conversation (Memory)
        self.adaptive_learner.extract_conversational_facts(user_message, self)

        response = self._route_request(user_message, force_model, forge_mode)
        if response is None:
            response = ""

        # Apply Style Guard
        response = self.apply_style_signature(response)
        
        # Refine Response (Clean artifacts)
        response = self._refine_response(response)
        
        # Extract code blocks
        code_blocks = self.extract_code(response)
        
        # Confidence Setup
        min_confidence = 100
        rules = [r['rule'] for r in self.get_learned_rules()] if code_blocks else []
        context = {'hardware': self.current_hardware, 'user_message': user_message, 'learned_rules': rules}
        all_issues = []

        # Validate each code block
        for code in code_blocks:
            valid, issues = self.validator.validate(code, self.current_hardware, user_message)
            if issues:
                all_issues.extend(issues)
            
            # Score block
            block_conf = self.confidence_scorer.calculate_confidence(code, context, (valid, issues))
            min_confidence = min(min_confidence, block_conf)

            if not valid:
                # Auto-fix critical issues
                fixed_code = self.validator.auto_fix(code, issues)
                response = response.replace(code, fixed_code)
                
                # Sanitize explanation text based on fixes
                for issue in issues:
                    if "Debouncing detected" in issue['message']:
                        response = re.sub(r'(?i)(\*\*?Debouncing\*\*?:?|Debouncing)', r'~~\1~~ (Removed)', response)
                
                # Append explanation
                response += "\n\n⚠️  **Auto-corrected:**\n"
                for issue in issues:
                    if issue['severity'] == 'error':
                        response += f"- {issue['message']}\n"
        
        # Flag Low Confidence / Fallback
        fallback_cfg = self.personality_manager.get_value("ai_fallback", {})
        threshold = fallback_cfg.get("confidence_threshold", 70)

        if code_blocks and self.confidence_scorer.should_escalate(min_confidence, threshold):
            if fallback_cfg.get("enabled", False):
                models = fallback_cfg.get("fallback_models", ["external"])
                prompts_map = fallback_cfg.get("prompts", {})
                
                response += f"\n\n🔄 **Fallback Triggered** (Confidence {min_confidence}% < {threshold}%)\n"
                
                active_fallbacks = ["gemini", "gpt4", "chatgpt", "claude"]
                style_summary = self.get_style_summary()

                for model in models:
                    if model in active_fallbacks:
                        # Check if client is actually configured before announcing escalation
                        if hasattr(self.fallback_client, 'is_available') and not self.fallback_client.is_available(model):
                            continue

                        print(f"🔄 Escalating to {model.upper()}...")
                        
                        # Check if escalate supports extended arguments to avoid TypeError
                        import inspect
                        sig = inspect.signature(self.fallback_client.escalate)
                        if 'validation_issues' in sig.parameters:
                            result = self.fallback_client.escalate(
                                model, user_message, response, min_confidence,
                                validation_issues=all_issues,
                                hardware_profile=self.current_hardware,
                                style_preferences=style_summary
                            )
                        else:
                            result = self.fallback_client.escalate(
                                model, user_message, response, min_confidence
                            )
                        
                        if "⚠️" not in result and "❌" not in result:
                            print(f"✅ Received improved solution from {model.upper()}")
                            
                            # Learning Loop: Extract patterns from fallback success
                            fallback_blocks = self.extract_code(result)
                            if fallback_blocks and code_blocks:
                                patterns = self.fallback_client.extract_learning_patterns(code_blocks[0], fallback_blocks[0])
                                learned_count = 0
                                for p in patterns:
                                    if len(p.strip()) > 5:  # Filter noise
                                        self.learner.store_rule(p, 0.6, f"fallback_{model}")
                                        learned_count += 1
                                if learned_count > 0:
                                    print(f"🧠 Learned {learned_count} patterns from {model.upper()} fallback.")
                            
                        response += f"\n{result}\n"
                        continue
                    
                    tmpl = prompts_map.get(model, f"System: Fallback ({model}). Context: {{context}}")
                    prompt = tmpl.format(context=user_message)
                    response += f"\n   **{model.upper()} Prompt**:\n   > {prompt}\n"
                    self.log_fallback_prompt(model, prompt)
                
                response += f"\n(Prompts logged to external_prompts.log)"
            else:
                response += f"\n\n⚠️ **Low Confidence ({min_confidence}%)**: Please verify generated code."
        
        # Generate Suggestion Bar
        suggestions = self.shadow_engine.get_all_suggestions(user_message, response)
        if suggestions:
            bar = "\n\nPROACTIVE: > " + " ".join([f"{i+1}. {s}" for i, s in enumerate(suggestions)])
            response += bar

        msg_id = self.storage.save_message("assistant", response)
        self.last_generated_id = msg_id
        self.context_messages.append({"id": msg_id, "role": "assistant", "content": response, "timestamp": datetime.now().isoformat()})
        
        result = ChatResponse(response, model=force_model or 'balanced', intent=intent)

        # After getting AI response, save to project
        if self.current_project:
            self.current_project.add_conversation(
                user_message, 
                result,
                {'model': getattr(result, 'model', 'unknown'), 'intent': intent}
            )
            self.project_memory.save_project(self.current_project)
            
        return result
        
    def get_sessions(self, limit: int = 20) -> List[Dict[str, str]]:
        return self.storage.get_sessions(limit)

    def rename_session(self, session_id: str, new_title: str) -> None:
        self.storage.rename_session(session_id, new_title)

    def delete_session(self, session_id: str) -> None:
        self.storage.delete_session(session_id)

    def clear_current_session(self) -> None:
        self.storage.clear_current_session()
        self.context_messages = []

    def load_session(self, session_id: str) -> List[Dict[str, str]]:
        self.context_messages = self.storage.load_session(session_id)
        return self.context_messages

    def start_new_session(self) -> str:
        """Reset context and start new session"""
        self.storage.start_new_session()
        self.context_messages = []
        return self.storage.current_session_id

    def reset_gpu(self) -> str:
        """Force unload models from GPU to free VRAM"""
        return self.llm.reset_gpu()

    def export_session_to_markdown(self, session_id: str = None) -> str:
        """Export session history to a Markdown file"""
        sid = session_id or self.storage.current_session_id
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT role, content, timestamp FROM messages WHERE session_id = ? ORDER BY id ASC", (sid,))
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return "No history found."
            
        filename = f"session_{sid}.md"
        filepath = DATA_DIR / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# BuddAI Session: {sid}\n\n")
            for role, content, ts in rows:
                f.write(f"### {role.upper()} ({ts})\n\n{content}\n\n---\n\n")
                
        return f"✅ Session exported to: {filepath}"

    def get_session_export_data(self, session_id: str = None) -> Dict:
        """Get session data as a dictionary for export"""
        sid = session_id or self.storage.current_session_id
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT role, content, timestamp FROM messages WHERE session_id = ? ORDER BY id ASC", (sid,))
        rows = cursor.fetchall()
        conn.close()
        
        return {
            "session_id": sid,
            "exported_at": datetime.now().isoformat(),
            "messages": [{"role": r, "content": c, "timestamp": t} for r, c, t in rows]
        }

    def export_session_to_json(self, session_id: str = None) -> str:
        """Export session history to a JSON file"""
        data = self.get_session_export_data(session_id)
        if not data["messages"]:
            return "No history found."
            
        filename = f"session_{data['session_id']}.json"
        filepath = DATA_DIR / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
                
        return f"✅ Session exported to: {filepath}"

    def import_session_from_json(self, data: Dict) -> str:
        """Import a session from JSON data"""
        session_id = data.get("session_id")
        messages = data.get("messages", [])
        
        if not session_id or not messages:
            raise ValueError("Invalid session JSON format")
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if session exists to avoid collision
        cursor.execute("SELECT 1 FROM sessions WHERE session_id = ? AND user_id = ?", (session_id, self.user_id))
        if cursor.fetchone():
            # Generate new ID
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_id = f"{session_id}_imp_{timestamp}"
        
        # Determine start time
        started_at = datetime.now().isoformat()
        if messages and "timestamp" in messages[0]:
            started_at = messages[0]["timestamp"]
            
        cursor.execute(
            "INSERT INTO sessions (session_id, user_id, started_at, title) VALUES (?, ?, ?, ?)",
            (session_id, self.user_id, started_at, f"Imported: {data.get('session_id')}")
        )
        
        # Insert messages
        for msg in messages:
            cursor.execute(
                "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (session_id, msg.get("role"), msg.get("content"), msg.get("timestamp", datetime.now().isoformat()))
            )
            
        conn.commit()
        conn.close()
        
        return session_id

    def create_backup(self) -> Tuple[bool, str]:
        return self.storage.create_backup()

    def initiate_conversation(self) -> None:
        """BuddAI starts the conversation based on context"""
        status = self.personality_manager.get_user_status()
        user_name = self.personality_manager.get_value("identity.user_name", "User")
        
        prompt = f"""
        Task: Initiate conversation with {user_name}.
        Current Context: {status}
        Time: {datetime.now().strftime('%H:%M')}
        
        Generate a brief, context-aware opening message. 
        If it's a build session, be ready to work.
        If it's rest time, be casual.
        Keep it under 2 sentences.
        """
        
        # Use fast model for greeting
        greeting = self.call_model("fast", prompt, system_task=True, hardware_override="Conversational")
        
        if isinstance(greeting, str):
            greeting = greeting.strip('"').strip()
            print(f"\nBuddAI:\n{greeting}\n")
            
            # Save to history
            msg_id = self.storage.save_message("assistant", greeting)
            self.context_messages.append({"id": msg_id, "role": "assistant", "content": greeting, "timestamp": datetime.now().isoformat()})

    def run(self) -> None:
        """Main loop"""
        try:
            self.initiate_conversation()
            force_model = None
            while True:
                user_name = self.personality_manager.get_value("identity.user_name", "User")
                user_input = input(f"\n{user_name}: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ['exit', 'quit']:
                    print("\n👋 Later!")
                    self.storage.end_session()
                    break
                if user_input.startswith('/'):
                    cmd = user_input.lower()
                    if cmd == '/fast':
                        force_model = "fast"
                        print("⚡ Next: FAST model")
                        continue
                    elif cmd == '/balanced':
                        force_model = "balanced"
                        print("⚖️  Next: BALANCED model")
                        continue
                    elif cmd == '/help':
                        print("\n💡 Commands:")
                        print("/fast - Use fast model")
                        print("/balanced - Use balanced model")
                        print("/index <path> - Index local repositories")
                        print("/gists - List indexed Gists")
                        print("/projects - Manage projects (list, new, open)")
                        print("/scan - Scan style signature (V3.0)")
                        print("/learn - Extract patterns from corrections")
                        print("/analyze - Analyze session for implicit feedback")
                        print("/correct <reason> - Mark previous response wrong")
                        print("/good - Mark previous response correct")
                        print("/teach <rule> - Explicitly teach a rule")
                        print("/skills - List active smart skills")
                        print("/reload - Reload skills registry")
                        print("/validate - Re-validate last response")
                        print("/rules - Show learned rules")
                        print("/metrics - Show improvement stats")
                        print("/train [strategy] - Run training strategies (public_db, auto_discovery, etc)")
                        print("/save - Export chat to Markdown")
                        print("/backup - Backup database")
                        print("/help - This message")
                        print("exit - End session\n")
                        continue
                    elif cmd.startswith('/index'):
                        parts = user_input.split(maxsplit=1)
                        if len(parts) > 1:
                            self.repo_manager.index_local_repositories(parts[1])
                        else:
                            print("Usage: /index <path_to_repos>")
                        continue
                    elif cmd == '/scan':
                        self.scan_style_signature()
                        continue
                    elif cmd == '/learn':
                        print("🧠 Analyzing corrections for patterns...")
                        patterns = self.learner.analyze_corrections(self)
                        if patterns:
                            print(f"✅ Learned {len(patterns)} new rules:")
                            for p in patterns:
                                print(f"  - {p['rule']}")
                        else:
                            print("No new patterns found.")
                        continue
                    elif cmd == '/analyze':
                        self.adaptive_learner.learn_from_session(self.storage.current_session_id)
                        continue
                    elif cmd.startswith('/correct'):
                        reason = user_input[8:].strip()
                        if reason.startswith('"') and reason.endswith('"'):
                            reason = reason[1:-1]
                        elif reason.startswith("'") and reason.endswith("'"):
                            reason = reason[1:-1]
                        last_response = ""
                        # Find last assistant message
                        for msg in reversed(self.context_messages):
                            if msg['role'] == 'assistant':
                                last_response = msg['content']
                                break
                        self.save_correction(last_response, "", reason)
                        print("✅ Correction saved. Run /learn to process it.")
                        continue
                    elif cmd == '/good':
                        if self.last_generated_id:
                            self.record_feedback(self.last_generated_id, True)
                            print("✅ Feedback recorded: Positive")
                        else:
                            print("❌ No recent message to rate.")
                        continue
                    elif cmd == '/remember':
                        if self.last_generated_id:
                            self.index_good_response(self.last_generated_id)
                            print("✅ Response indexed for future reference.")
                        else:
                            print("❌ No recent response to remember.")
                        continue
                    elif cmd.startswith('/teach'):
                        rule = user_input[7:].strip()
                        if rule:
                            self.teach_rule(rule)
                            print(f"✅ Learned rule: {rule}")
                        else:
                            print("Usage: /teach <rule description>")
                        continue
                    elif cmd == '/validate':
                        last_response = ""
                        user_context = ""
                        
                        # Find last assistant message and preceding user message
                        for i in range(len(self.context_messages) - 1, -1, -1):
                            if self.context_messages[i]['role'] == 'assistant':
                                last_response = self.context_messages[i]['content']
                                if i > 0 and self.context_messages[i-1]['role'] == 'user':
                                    user_context = self.context_messages[i-1]['content']
                                break
                        
                        if not last_response:
                            print("❌ No recent code to validate.")
                            continue

                        code_blocks = self.extract_code(last_response)
                        if not code_blocks:
                            print("❌ No code blocks found in last response.")
                            continue

                        print("\n🔍 Validating last response...")
                        all_valid = True
                        for i, code in enumerate(code_blocks, 1):
                            valid, issues = self.validator.validate(code, self.current_hardware, user_context)
                            if not valid:
                                all_valid = False
                                print(f"\nBlock {i} Issues:")
                                for issue in issues:
                                    icon = "❌" if issue['severity'] == 'error' else "⚠️"
                                    print(f"  {icon} Line {issue.get('line', '?')}: {issue['message']}")
                            else:
                                print(f"✅ Block {i} is valid.")
                        
                        if all_valid:
                            print("\n✨ All code blocks look good!")
                        continue
                    elif cmd == '/rules':
                        conn = sqlite3.connect(self.db_path)
                        cursor = conn.cursor()
                        cursor.execute("SELECT rule_text, confidence, learned_from FROM code_rules ORDER BY confidence DESC")
                        rows = cursor.fetchall()
                        conn.close()
                        
                        if not rows:
                            print("🤷 No rules learned yet.")
                        else:
                            print(f"\n🧠 Learned Rules ({len(rows)}):")
                            for rule, conf, source in rows:
                                print(f"  - [{conf:.1f}] {rule} ({source})")
                        continue
                    elif cmd == '/skills':
                        if not self.skills_registry:
                            print("🧩 No skills loaded.")
                        else:
                            print(f"\n🧩 Active Skills ({len(self.skills_registry)}):")
                            for s in self.skills_registry.values():
                                print(f"  - {s['name']}: {s['description']}")
                        continue
                    elif cmd == '/reload':
                        self.skills_registry = load_registry()
                        print(f"✅ Reloaded {len(self.skills_registry)} skills.")
                        continue
                    elif cmd == '/metrics':
                        stats = self.metrics.calculate_accuracy()
                        print("\n📊 Learning Metrics (Last 30 Days):")
                        print(f"   Accuracy:        {stats['accuracy']:.1f}%")
                        print(f"   Correction Rate: {stats['correction_rate']:.1f}%")
                        print(f"   Trend (7d):      {stats['improvement']}")
                        print("")
                        continue
                    elif cmd == '/fallback-stats':
                        stats = self.metrics.get_fallback_stats()
                        print(f"📊 Fallback Statistics:")
                        print(f"   Total escalations: {stats['total_escalations']}")
                        print(f"   Fallback rate: {stats['fallback_rate']}%")
                        print(f"   Learning success: {stats['learning_success']}%")
                        continue
                    elif cmd == '/debug':
                        if self.last_prompt_debug:
                            print(f"\n🐛 Last Prompt Sent:\n{self.last_prompt_debug}\n")
                        else:
                            print("❌ No prompt sent yet.")
                        continue
                    elif cmd.startswith('/train'):
                        parts = user_input.split(maxsplit=2)
                        if len(parts) < 2:
                            strategies = self.training_registry.list_strategies()
                            print("\n🎓 Training Strategies:")
                            for name, desc in strategies.items():
                                print(f"  - /train {name}: {desc}")
                            print("")
                        else:
                            # Delegate to handle_slash_command for execution
                            result = self.handle_slash_command(user_input)
                            print(result)
                        continue
                    elif cmd == '/backup':
                        success, msg = self.create_backup()
                        if success:
                            print(f"✅ Database backed up to: {msg}")
                        else:
                            print(f"❌ Backup failed: {msg}")
                        continue
                    elif cmd.startswith('/save'):
                        if 'json' in user_input.lower():
                            print(self.export_session_to_json())
                        else:
                            print(self.export_session_to_markdown())
                        continue
                # Chat
                result = self.chat(user_input, force_model)
                response = str(result)
                if response:
                    print(f"\nBuddAI:\n{response}\n")
                force_model = None
        except KeyboardInterrupt:
            print("\n\n👋 Bye!")
            self.storage.end_session()
