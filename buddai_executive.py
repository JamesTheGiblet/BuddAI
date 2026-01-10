#!/usr/bin/env python3
from urllib.parse import urlparse
import sys, os, json, logging, sqlite3, re, zipfile, shutil, queue, argparse, io
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Tuple, Union, Generator, Any

try:
    import psutil
except ImportError:
    psutil = None

from core.buddai_analytics import LearningMetrics
from core.buddai_validation import HardwareProfile
from core.buddai_confidence import ConfidenceScorer
from core.buddai_fallback import FallbackClient
from core.buddai_memory import AdaptiveLearner, ShadowSuggestionEngine, SmartLearner
from core.buddai_shared import DATA_DIR, DB_PATH, MODELS, OLLAMA_HOST, OLLAMA_PORT, SERVER_AVAILABLE
from core.buddai_training import ModelFineTuner
from core.buddai_knowledge import RepoManager
from core.buddai_llm import OllamaClient
from core.buddai_prompt_engine import PromptEngine
from core.buddai_personality import PersonalityManager
from core.buddai_storage import StorageManager
from validators.registry import ValidatorRegistry
from skills import load_registry
from languages.language_registry import get_language_registry

# --- Shadow Suggestion Engine ---

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
ALLOWED_TYPES = [
    "application/zip", "application/x-zip-compressed", "application/octet-stream",
    "text/x-python", "text/plain", "text/x-c++src", "text/x-csrc", "text/javascript", "text/html", "text/css"
]
MAX_UPLOAD_FILES = 20

class BuddAI:
    """Executive with task breakdown"""

    def __init__(self, user_id: str = "default", server_mode: bool = False):
        self.user_id = user_id
        self.last_generated_id = None
        self.last_prompt_debug = None
        self.server_mode = server_mode
        self.context_messages = []
        self.storage = StorageManager(self.user_id)
        self.personality_manager = PersonalityManager()
        self.shadow_engine = ShadowSuggestionEngine(DB_PATH, self.user_id)
        self.learner = SmartLearner()
        self.hardware_profile = HardwareProfile()
        self.current_hardware = "Generic"
        self.validator = ValidatorRegistry()
        self.confidence_scorer = ConfidenceScorer()
        self.fallback_client = FallbackClient()
        self.adaptive_learner = AdaptiveLearner()
        self.metrics = LearningMetrics()
        self.fine_tuner = ModelFineTuner()
        self.repo_manager = RepoManager(DB_PATH, self.user_id)
        self.llm = OllamaClient()
        self.prompt_engine = PromptEngine()
        self.skills_registry = load_registry()
        self.language_registry = get_language_registry()
        
        self.display_welcome_message()
        
        print(f"\n{self.personality_manager.get_user_status()}\n")
        
    def display_welcome_message(self):
        """Display the startup banner and status."""
        # Format welcome message with rule count
        welcome_tmpl = self.personality_manager.get_value("communication.welcome_message", "BuddAI Executive v4.5 - Enhanced Learning & Integration")
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM code_rules")
            count = cursor.fetchone()[0]
            conn.close()
            welcome_msg = welcome_tmpl.replace("{rule_count}", str(count))
            welcome_msg = welcome_msg.replace("{schedule_status}", self.personality_manager.get_user_status())
            print(welcome_msg)
        except:
            print(welcome_tmpl.replace("{rule_count}", "0").replace("{schedule_status}", ""))
            
        print("=" * 50)
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
        print("\n🕵️  Scanning repositories for style signature...")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get a sample of code
        cursor.execute("SELECT content FROM repo_index WHERE user_id = ? ORDER BY RANDOM() LIMIT 5", (self.user_id,))
        rows = cursor.fetchall()
        
        if not rows:
            print("❌ No code indexed. Run /index first.")
            conn.close()
            return
            
        code_sample = "\n---\n".join([r[0][:1000] for r in rows])
        
        prompt_template = self.personality_manager.get_value("prompts.style_scan", "Analyze this code sample from {user_name}'s repositories.\nExtract 3 distinct coding preferences or patterns.\n\nCode Sample:\n{code_sample}")
        prompt = prompt_template.format(user_name=self.personality_manager.get_value("identity.user_name", "the user"), code_sample=code_sample)
        
        print("⚡ Analyzing with BALANCED model...")
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
                    "INSERT INTO style_preferences (user_id, category, preference, confidence, extracted_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (self.user_id, category, pref, 0.8, timestamp)
                )
        
        conn.commit()
        conn.close()
        print(f"\n✅ Style Signature Updated:\n{summary}\n")

    def get_recent_context(self, limit: int = 5) -> str:
        """Get recent chat context as a string"""
        return json.dumps(self.context_messages[-limit:])

    def save_correction(self, original_code: str, corrected_code: str, reason: str):
        """Store when James fixes BuddAI's code"""
        conn = sqlite3.connect(DB_PATH)
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
        # user_message is currently unused
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Fetch rules with reasonable confidence
        cursor.execute("SELECT rule_text, confidence FROM code_rules WHERE confidence > 0.6 ORDER BY confidence DESC")
        rows = cursor.fetchall()
        conn.close()
        return [{"rule_text": r[0], "confidence": r[1]} for r in rows]

    def get_style_summary(self) -> str:
        """Get summary of learned style preferences"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT category, preference FROM style_preferences WHERE confidence > 0.6")
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            return "Standard coding style."
        return ", ".join([f"{r[0]}: {r[1]}" for r in rows])

    def teach_rule(self, rule_text: str):
        """Explicitly save a user-taught rule"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO code_rules 
            (rule_text, pattern_find, pattern_replace, confidence, learned_from)
            VALUES (?, ?, ?, ?, ?)
        """, (rule_text, "", "", 1.0, 'user_taught'))
        conn.commit()
        conn.close()

    def log_compilation_result(self, code: str, success: bool, errors: str = ""):
        """Track what compiles vs what fails"""
        conn = sqlite3.connect(DB_PATH)
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
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT rule_text, pattern_find, pattern_replace, confidence FROM code_rules WHERE confidence >= 0.8")
        rows = cursor.fetchall()
        conn.close()
        return [{"rule": r[0], "find": r[1], "replace": r[2], "confidence": r[3]} for r in rows]

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
                enhanced_prompt = self.prompt_engine.build_enhanced_prompt(message, hw_context, self.context_messages)
                
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
            return f"Error: {str(e)}"

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
                    choice = input("Select Tuning Constant [1-3, default 2]: ")
                
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

    def record_feedback(self, message_id: int, feedback: bool, comment: str = "") -> Optional[str]:
        """Learn from user feedback."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO feedback (message_id, positive, comment, timestamp)
            VALUES (?, ?, ?, ?)
        """, (message_id, feedback, comment, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
        # Adjust confidence scores
        self.update_style_confidence(message_id, feedback)
        
        if not feedback:
            self.analyze_failure(message_id)
            return self.regenerate_response(message_id, comment)
        return None

    def regenerate_response(self, message_id: int, comment: str = "") -> str:
        """Regenerate a response, optionally considering feedback comment"""
        conn = sqlite3.connect(DB_PATH)
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
        conn = sqlite3.connect(DB_PATH)
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
        for skill_id, skill in self.skills_registry.items():
            for trigger in skill['triggers']:
                if trigger in msg_lower:
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
        keywords = ["replace", "replacing", "upgrade", "wiring", "pinout", "board", "compatible", "difference", "vs", "printer", "creality", "artillery"]
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
        elif self._is_general_discussion(user_message):
            print("\n⚡ Using BALANCED model (General Context)...")
            return self.call_model("balanced", user_message, hardware_override="General Electronics")
        elif self.prompt_engine.is_simple_question(user_message):
            print("\n⚡ Using FAST model (simple question)...")
            # Don't force code generation prompt for simple greetings or definitions
            msg_lower = user_message.lower().strip()
            is_greeting = any(msg_lower.startswith(w) for w in ['hi', 'hello', 'hey', 'good morning', 'good evening']) and len(user_message.split()) < 6
            is_conceptual = any(msg_lower.startswith(w) for w in ['what is', "what's", 'explain', 'tell me about', 'who is', 'can you explain'])
            # Enable personality/history for greetings to support symbiotic conversation
            use_system_task = is_conceptual and not is_greeting
            return self.call_model("fast", user_message, system_task=use_system_task)
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
            # Enable personality/history for greetings
            use_system_task = is_conceptual and not is_greeting
            iterator = self.call_model("fast", user_message, stream=True, system_task=use_system_task)
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
        return re.findall(r'```(?:\w+)?\n(.*?)```', text, re.DOTALL)

    def handle_slash_command(self, command: str) -> str:
        """Handle slash commands when received via chat interface"""
        cmd = command.lower().strip()
        
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

        if cmd == '/rules':
            conn = sqlite3.connect(DB_PATH)
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
                    f"   Session:  {self.storage.current_session_id}\n"
                    f"   Hardware: {self.current_hardware}\n"
                    f"   Memory:   {mem_usage}\n"
                    f"   Messages: {len(self.context_messages)}")

        if cmd == '/backup':
            success, msg = self.create_backup()
            if success:
                return f"✅ Database backed up to: {msg}"
            return f"❌ Backup failed: {msg}"

        if cmd == '/train':
            result = self.fine_tuner.prepare_training_data()
            return f"✅ {result}"
            
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

    def _extract_code_blocks(self, text: str) -> List[Dict]:
        """Extract code blocks from markdown"""
        pattern = r'```(\w+)?\n(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)
        
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
        if user_message.strip().startswith('/'):
            return self.handle_slash_command(user_message.strip())

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

        prompt_template = self.personality_manager.get_value("prompts.style_reference", "\n[REFERENCE STYLE FROM {user_name}'S PAST PROJECTS]\n")
        user_name = self.personality_manager.get_value("identity.user_name", "the user")
        style_context = self.repo_manager.retrieve_style_context(user_message, prompt_template, user_name)
        if style_context:
            self.context_messages.append({"role": "system", "content": style_context})

        user_msg_id = self.storage.save_message("user", user_message)
        self.context_messages.append({"id": user_msg_id, "role": "user", "content": user_message, "timestamp": datetime.now().isoformat()})

        # Check Skills (High Priority)
        skill_result = self.check_skills(user_message)
        if skill_result:
            msg_id = self.storage.save_message("assistant", skill_result)
            self.last_generated_id = msg_id
            self.context_messages.append({"id": msg_id, "role": "assistant", "content": skill_result, "timestamp": datetime.now().isoformat()})
            return skill_result

        # Direct Schedule Check
        schedule_triggers = self.personality_manager.get_value("work_cycles.schedule_check_triggers", ["my schedule"])
        if any(trigger in user_message.lower() for trigger in schedule_triggers):
            status = self.personality_manager.get_user_status()
            response = f"📅 **Schedule Check**\nAccording to your protocol, you should be: **{status}**"
            print(f"⏰ Schedule check triggered: {status}")
            msg_id = self.storage.save_message("assistant", response)
            self.last_generated_id = msg_id
            self.context_messages.append({"id": msg_id, "role": "assistant", "content": response, "timestamp": datetime.now().isoformat()})
            return response

        response = self._route_request(user_message, force_model, forge_mode)

        # Apply Style Guard
        response = self.apply_style_signature(response)
        
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
                        if not self.fallback_client.is_available(model):
                            continue

                        print(f"🔄 Escalating to {model.upper()}...")
                        result = self.fallback_client.escalate(
                            model, user_message, response, min_confidence,
                            validation_issues=all_issues,
                            hardware_profile=self.current_hardware,
                            style_preferences=style_summary
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

        return response
        
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
        
        conn = sqlite3.connect(DB_PATH)
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
        conn = sqlite3.connect(DB_PATH)
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
            
        conn = sqlite3.connect(DB_PATH)
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

    def run(self) -> None:
        """Main loop"""
        try:
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
                        print("/train - Export corrections for fine-tuning")
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
                        conn = sqlite3.connect(DB_PATH)
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
                    elif cmd == '/train':
                        result = self.fine_tuner.prepare_training_data()
                        print(f"✅ {result}")
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
                    else:
                        print("\nUnknown command. Type /help")
                        continue
                # Chat
                response = self.chat(user_input, force_model)
                print(f"\nBuddAI:\n{response}\n")
                force_model = None
        except KeyboardInterrupt:
            print("\n\n👋 Bye!")
            self.storage.end_session()
