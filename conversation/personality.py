"""
BuddAI Personality Engine
Natural, context-aware conversational interface
"""

import os
import json
from datetime import datetime, time
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class BuddAIPersonality:
    """
    Manages BuddAI's conversational personality
    
    Features:
    - Context-aware greetings
    - Schedule awareness
    - Natural conversation flow
    - Memory of user preferences
    - Adaptive communication style
    """
    
    def __init__(self, user_profile: Dict = None):
        self.user_profile = user_profile or {}
        self.conversation_history = []
        self.current_mood = 'helpful'
        self.load_personality_traits()
    
    def load_personality_traits(self):
        """Load personality configuration"""
        
        self.traits = {
            'name': 'BuddAI',
            'role': 'Your coding buddy and thinking partner',
            'style': 'direct, technical, enthusiastic',
            'values': [
                'Understands context without explicit instructions',
                'Asks clarifying questions naturally',
                'Remembers previous conversations',
                'Builds ideas iteratively through discussion',
                'Suggests based on past patterns'
            ],
            'communication': {
                'greeting': 'friendly and context-aware',
                'questions': 'natural and purposeful',
                'responses': 'concise with examples',
                'errors': 'helpful and constructive'
            }
        }
    
    def greet(self, context: Dict = None) -> str:
        """
        Generate context-aware greeting
        
        Args:
            context: Current context (time, recent activity, etc.)
        
        Returns:
            Natural greeting string
        """
        
        context = context or {}
        
        # Get current time
        now = datetime.now()
        hour = now.hour
        day_name = now.strftime('%A')
        
        # Determine time of day
        if 5 <= hour < 6:
            time_greeting = "Early start! ☀️"
        elif 6 <= hour < 12:
            time_greeting = f"Good morning! It's {day_name}"
        elif 12 <= hour < 17:
            time_greeting = f"Good afternoon! {day_name}"
        elif 17 <= hour < 21:
            time_greeting = f"Evening, James! {day_name}"
        else:
            time_greeting = "Late night coding session! 🌙"
        
        # Build greeting
        greeting_parts = [f"Hi James! {time_greeting}"]
        
        # Add context-specific questions
        
        # Check if work day
        if day_name in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
            if 8 <= hour < 15:
                greeting_parts.append("At Oxford Pharmagenesis today?")
            elif 15 <= hour < 18:
                greeting_parts.append("How was work?")
        
        # Weekend
        elif day_name in ['Saturday', 'Sunday']:
            if 10 <= hour < 12:
                greeting_parts.append("Weekend build time! 🛠️")
            elif 17 <= hour < 21:
                greeting_parts.append("Evening build session? 🔧")
        
        # Add open-ended question
        greeting_parts.append("\nAnything on your mind today?")
        
        return " ".join(greeting_parts)
    
    def understand_intent(self, user_message: str, context: Dict = None) -> Dict:
        """
        Understand user's intent from natural language
        
        Args:
            user_message: User's input
            context: Current context
        
        Returns:
            Intent analysis with confidence and suggestions
        """
        
        context = context or {}
        message_lower = user_message.lower()
        
        # Detect intent patterns
        intent = {
            'type': 'unknown',
            'confidence': 0.0,
            'entities': [],
            'suggestions': [],
            'requires_clarification': False
        }
        
        # Project-related intents
        if any(word in message_lower for word in ['thinking', 'idea', 'want to', 'planning']):
            intent['type'] = 'idea_exploration'
            intent['confidence'] = 0.8
            intent['requires_clarification'] = True
            
            # Extract topic
            if 'robot' in message_lower or 'bot' in message_lower:
                intent['entities'].append({'type': 'domain', 'value': 'robotics'})
            if 'printer' in message_lower or '3d' in message_lower:
                intent['entities'].append({'type': 'domain', 'value': '3d_printing'})
            if 'web' in message_lower or 'app' in message_lower:
                intent['entities'].append({'type': 'domain', 'value': 'web_development'})
        
        # Continuation intents
        elif any(word in message_lower for word in ['continue', 'carry on', 'keep going']):
            intent['type'] = 'continue_project'
            intent['confidence'] = 0.9
            intent['suggestions'] = ['Load recent project', 'List active projects']
        
        # New project
        elif any(phrase in message_lower for phrase in ['new project', 'start fresh', 'create new']):
            intent['type'] = 'new_project'
            intent['confidence'] = 0.9
            intent['requires_clarification'] = True
        
        # Question/help
        elif message_lower.startswith(('how', 'what', 'why', 'when', 'where')):
            intent['type'] = 'question'
            intent['confidence'] = 0.9
        
        # Code request
        elif any(word in message_lower for word in ['code', 'write', 'generate', 'create']):
            intent['type'] = 'code_request'
            intent['confidence'] = 0.7
            intent['requires_clarification'] = True
        
        return intent
    
    def generate_clarifying_questions(self, intent: Dict, context: Dict = None) -> List[str]:
        """
        Generate natural clarifying questions
        
        Args:
            intent: Detected intent
            context: Current context
        
        Returns:
            List of clarifying questions
        """
        
        context = context or {}
        questions = []
        
        if intent['type'] == 'idea_exploration':
            
            # Check if related to previous work
            entities = intent.get('entities', [])
            domain = next((e['value'] for e in entities if e['type'] == 'domain'), None)
            
            if domain == 'robotics':
                questions.append("Sounds cool! Is this related to GilBot or something completely new?")
                questions.append("Are you thinking ESP32 like usual?")
            
            elif domain == '3d_printing':
                questions.append("Nice! Related to your E3D work or personal project?")
                questions.append("Optimization, new design, or something else?")
            
            elif domain == 'web_development':
                questions.append("Web app idea! Frontend, backend, or full stack?")
                questions.append("Using your HTML/CSS/JS skills from v4.5?")
            
            else:
                questions.append("Tell me more - what domain?")
                questions.append("New idea or building on something existing?")
        
        elif intent['type'] == 'new_project':
            questions.append("What kind of project?")
            questions.append("Want to apply Forge Theory or try something different?")
        
        elif intent['type'] == 'code_request':
            questions.append("What language?")
            questions.append("For which project?")
        
        return questions
    
    def respond_naturally(self, message: str, intent: Dict, context: Dict = None) -> str:
        """
        Generate natural response
        
        Args:
            message: User's message
            intent: Detected intent
            context: Current context
        
        Returns:
            Natural language response
        """
        
        context = context or {}
        
        if intent['type'] == 'idea_exploration':
            response = self._handle_idea_exploration(message, intent, context)
        
        elif intent['type'] == 'continue_project':
            response = self._handle_continue_project(message, intent, context)
        
        elif intent['type'] == 'new_project':
            response = self._handle_new_project(message, intent, context)
        
        elif intent['type'] == 'question':
            response = self._handle_question(message, intent, context)
        
        elif intent['type'] == 'code_request':
            response = self._handle_code_request(message, intent, context)
        
        else:
            response = "I'm listening! Want to tell me more?"
        
        return response
    
    def _handle_idea_exploration(self, message: str, intent: Dict, context: Dict) -> str:
        """Handle idea exploration conversation"""
        
        entities = intent.get('entities', [])
        domain = next((e['value'] for e in entities if e['type'] == 'domain'), None)
        
        response_parts = []
        
        # Acknowledge the idea
        if domain == 'robotics':
            response_parts.append("Ah nice! Robot idea - I love it. 🤖")
            
            # Reference previous work
            if 'spinner' in message.lower() or 'spin' in message.lower():
                response_parts.append("\nSpinner weapon? Those are brutal in combat.")
                response_parts.append("This reminds me of GilBot (your flipper robot).")
            elif 'swarm' in message.lower():
                response_parts.append("\nSwarm robotics! Like the bioelectric mesh idea?")
            else:
                response_parts.append("\nWhat kind of robot?")
        
        elif domain == '3d_printing':
            response_parts.append("3D printing project - right in your wheelhouse! 🖨️")
            response_parts.append("\nRelated to the printer rebuild work or new direction?")
        
        else:
            response_parts.append("Interesting idea!")
            response_parts.append("\nTell me more - what's the domain?")
        
        # Ask clarifying questions
        questions = self.generate_clarifying_questions(intent, context)
        if questions:
            response_parts.append("\n" + questions[0])
        
        return " ".join(response_parts)
    
    def _handle_continue_project(self, message: str, intent: Dict, context: Dict) -> str:
        """Handle project continuation"""
        
        return "Loading your recent projects...\n\nWhich one:\n- GilBot (combat robot)\n- 3D printer rebuild\n- BuddAI v5.0\n\nOr want to see all projects?"
    
    def _handle_new_project(self, message: str, intent: Dict, context: Dict) -> str:
        """Handle new project creation"""
        
        return "New project! Let's do it. 🚀\n\nWhat are we building?\n- Domain/type?\n- Any connection to existing work?"
    
    def _handle_question(self, message: str, intent: Dict, context: Dict) -> str:
        """Handle questions"""
        
        return "Good question! Let me think..."
    
    def _handle_code_request(self, message: str, intent: Dict, context: Dict) -> str:
        """Handle code generation requests"""
        
        return "I can help with that!\n\nBefore I generate code:\n- Which project?\n- What language?\n- Any specific requirements?"
    
    def remember_conversation(self, user_message: str, assistant_response: str, metadata: Dict = None):
        """
        Remember conversation exchange
        
        Args:
            user_message: User's input
            assistant_response: BuddAI's response
            metadata: Additional context
        """
        
        self.conversation_history.append({
            'timestamp': datetime.now().isoformat(),
            'user': user_message,
            'assistant': assistant_response,
            'metadata': metadata or {}
        })
    
    def get_conversation_summary(self, last_n: int = 5) -> str:
        """Get summary of recent conversation"""
        
        recent = self.conversation_history[-last_n:]
        
        summary_parts = [f"Last {len(recent)} exchanges:"]
        
        for i, exchange in enumerate(recent, 1):
            summary_parts.append(f"\n{i}. You: {exchange['user'][:50]}...")
            summary_parts.append(f"   Me: {exchange['assistant'][:50]}...")
        
        return "\n".join(summary_parts)