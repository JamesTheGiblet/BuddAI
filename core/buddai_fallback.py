import os
import logging

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

class FallbackClient:
    """
    Handles escalation to external AI models (Gemini, OpenAI) when local confidence is low.
    """
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        
        self.gemini_client = None
        self.openai_client = None
        
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

    def escalate(self, model_alias: str, original_prompt: str, buddai_attempt: str, confidence: int) -> str:
        """
        Routes the escalation request to the appropriate provider.
        """
        if model_alias == 'gemini':
            return self._call_gemini(original_prompt, buddai_attempt, confidence)
        elif model_alias in ['gpt4', 'chatgpt']:
            return self._call_openai(model_alias, original_prompt, buddai_attempt, confidence)
        
        return f"⚠️ Fallback model '{model_alias}' not supported for active escalation."

    def _call_gemini(self, original_prompt: str, buddai_attempt: str, confidence: int) -> str:
        if not self.gemini_client:
            return f"⚠️ Gemini fallback unavailable (Key missing or init failed)."

        try:
            prompt = self._build_prompt(original_prompt, buddai_attempt, confidence)
            response = self.gemini_client.generate_content(prompt)
            return f"✨ **Gemini Fallback (Confidence: {confidence}%)**\n\n{response.text}"
        except Exception as e:
            return f"❌ Error calling Gemini API: {str(e)}"

    def _call_openai(self, model_alias: str, original_prompt: str, buddai_attempt: str, confidence: int) -> str:
        if not self.openai_client:
            return f"⚠️ OpenAI fallback unavailable (Key missing or init failed)."

        model_map = {
            'gpt4': 'gpt-4',
            'chatgpt': 'gpt-3.5-turbo'
        }
        target_model = model_map.get(model_alias, 'gpt-3.5-turbo')

        try:
            prompt = self._build_prompt(original_prompt, buddai_attempt, confidence)
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

    def _build_prompt(self, original, attempt, confidence):
        return f"""
        [USER REQUEST]: {original}
        [LOCAL ATTEMPT ({confidence}% confidence)]: {attempt}
        [TASK]: Fix issues, apply best practices, and return corrected code.
        """