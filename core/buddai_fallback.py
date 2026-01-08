import os
import logging
import difflib

# Optional import for Google Generative AI
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

# Optional import for OpenAI
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

# Optional import for Anthropic
try:
    import anthropic
    HAS_CLAUDE = True
except ImportError:
    HAS_CLAUDE = False

class FallbackClient:
    """
    Handles escalation to external AI models (Gemini, OpenAI) when local confidence is low.
    """
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.claude_key = os.getenv("ANTHROPIC_API_KEY")
        
        self.gemini_client = None
        self.openai_client = None
        self.claude_client = None
        
        # Initialize Gemini
        if self.gemini_key and HAS_GEMINI:
            try:
                genai.configure(api_key=self.gemini_key)
                self.gemini_client = genai.GenerativeModel('gemini-1.5-flash')
            except Exception as e:
                print(f"⚠️ Failed to initialize Gemini client: {e}")

        # Initialize OpenAI
        if self.openai_key and HAS_OPENAI:
            try:
                self.openai_client = OpenAI(api_key=self.openai_key)
            except Exception as e:
                print(f"⚠️ Failed to initialize OpenAI client: {e}")

        # Initialize Claude
        if self.claude_key and HAS_CLAUDE:
            try:
                self.claude_client = anthropic.Anthropic(api_key=self.claude_key)
            except Exception as e:
                print(f"⚠️ Failed to initialize Claude client: {e}")

    def is_available(self, model_alias: str) -> bool:
        """Check if a specific model client is configured and available"""
        if model_alias == 'gemini':
            return self.gemini_client is not None
        elif model_alias in ['gpt4', 'chatgpt']:
            return self.openai_client is not None
        elif model_alias == 'claude':
            return self.claude_client is not None
        return False

    def escalate(self, model_alias: str, original_prompt: str, buddai_attempt: str, confidence: int, **kwargs) -> str:
        """
        Routes the escalation request to the appropriate provider.
        """
        validation_issues = kwargs.get('validation_issues')
        
        # Context injection for prompt builder
        self.hardware_profile = kwargs.get('hardware_profile', 'Generic')
        self.style_preferences = kwargs.get('style_preferences', 'Standard')

        if model_alias == 'gemini':
            return self._call_gemini(original_prompt, buddai_attempt, confidence, validation_issues)
        elif model_alias in ['gpt4', 'chatgpt']:
            return self._call_openai(model_alias, original_prompt, buddai_attempt, confidence, validation_issues)
        elif model_alias == 'claude':
            return self._call_claude(original_prompt, buddai_attempt, confidence, validation_issues)
        
        return f"⚠️ Fallback model '{model_alias}' not supported for active escalation."

    def _call_gemini(self, original_prompt: str, buddai_attempt: str, confidence: int, validation_issues: list = None) -> str:
        if not self.gemini_client:
            return f"⚠️ Gemini fallback unavailable (Key missing or init failed)."

        try:
            prompt = self.build_fallback_prompt(original_prompt, buddai_attempt, confidence, validation_issues)
            response = self.gemini_client.generate_content(prompt)
            return f"✨ **Gemini Fallback (Confidence: {confidence}%)**\n\n{response.text}"
        except Exception as e:
            return f"❌ Error calling Gemini API: {str(e)}"

    def _call_openai(self, model_alias: str, original_prompt: str, buddai_attempt: str, confidence: int, validation_issues: list = None) -> str:
        if not self.openai_client:
            return f"⚠️ OpenAI fallback unavailable (Key missing or init failed)."

        model_map = {
            'gpt4': 'gpt-4',
            'chatgpt': 'gpt-3.5-turbo'
        }
        target_model = model_map.get(model_alias, 'gpt-3.5-turbo')

        try:
            prompt = self.build_fallback_prompt(original_prompt, buddai_attempt, confidence, validation_issues)
            response = self.openai_client.chat.completions.create(
                model=target_model,
                messages=[
                    {"role": "system", "content": "You are a high-precision coding assistant acting as a fallback validator."},
                    {"role": "user", "content": prompt}
                ]
            )
            return f"✨ **{model_alias.upper()} Fallback (Confidence: {confidence}%)**\n\n{response.choices[0].message.content}"
        except Exception as e:
            return f"❌ Error calling OpenAI API: {str(e)}"

    def _call_claude(self, original_prompt: str, buddai_attempt: str, confidence: int, validation_issues: list = None) -> str:
        if not hasattr(self, 'claude_client') or not self.claude_client:
            return f"⚠️ Claude fallback unavailable (Key missing or init failed)."

        try:
            prompt = self.build_fallback_prompt(original_prompt, buddai_attempt, confidence, validation_issues)
            message = self.claude_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            return f"✨ **Claude Fallback (Confidence: {confidence}%)**\n\n{message.content[0].text}"
        except Exception as e:
            return f"❌ Error calling Claude API: {str(e)}"

    def build_fallback_prompt(self, user_request, buddai_code, confidence, validation_issues):
        issues_str = "None"
        if validation_issues:
            issues_str = "\n".join([f"- {i.get('message', str(i))}" for i in validation_issues])
            
        return f"""
    BuddAI attempted this request but confidence is low ({confidence}%).
    
    Original request: {user_request}
    
    BuddAI's attempt:
    {buddai_code}
    
    Validation issues:
    {issues_str}
    
    Please provide improved solution considering:
    - Hardware: {self.hardware_profile}
    - User's style: {self.style_preferences}
    - Forge Theory: Use exponential smoothing where applicable
    """

    def extract_learning_patterns(self, buddai_code: str, fallback_code: str) -> list:
        """
        Compare what BuddAI tried vs what Claude provided
        Extract the key differences
        """
        # Diff the code
        diff = difflib.unified_diff(
            buddai_code.splitlines(),
            fallback_code.splitlines(),
            lineterm=''
        )
        
        patterns = []
        # Identify new patterns
        for line in diff:
            if line.startswith('+') and not line.startswith('+++'):
                patterns.append(line[1:].strip())
        
        # Return learnable rules
        return patterns