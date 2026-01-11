"""
BuddAI Abilities & Protocols
Specialized logic handlers for specific interaction types.
"""

from typing import List

class ConversationProtocol:
    """
    Protocol for handling pure conversation, small talk, and pleasantries
    without triggering code generation or technical workflows.
    """
    
    def __init__(self, personality_manager):
        self.personality = personality_manager
        self.triggers = [
            "thank you", "thanks", "thx", "i am well", "doing good", 
            "doing well", "you too", "cool", "awesome", "great", 
            "ok", "okay", "understood", "got it", "bye", "goodbye",
            "see you", "later", "goodnight", "how are you", "what's up",
            "no problem", "appreciate it"
        ]
        self.greetings = ['hi', 'hello', 'hey', 'good morning', 'good evening', 'greetings']
        
        # Words that strongly suggest a technical request (override conversation)
        self.technical_overrides = [
            "code", "generate", "function", "script", "compile", "error", 
            "fix", "debug", "loop", "setup", "variable", "class", "struct"
        ]

    def is_conversational(self, text: str) -> bool:
        """Determine if the input is purely conversational."""
        text_lower = text.lower().strip()
        
        # 1. Safety Check: If it looks like a code request, it's NOT conversation
        if any(ind in text_lower for ind in self.technical_overrides):
            return False
            
        # 2. Check explicit conversational triggers
        if any(trigger in text_lower for trigger in self.triggers):
            return True
            
        # 3. Check greetings (start of message)
        if any(text_lower.startswith(w) for w in self.greetings) and len(text.split()) < 20:
            return True
            
        # 4. Check short affirmations/negations
        words = text_lower.split()
        if len(words) < 5 and words[0] in ["yes", "no", "yep", "nope", "sure", "maybe", "right", "exactly"]:
            return True
            
        return False