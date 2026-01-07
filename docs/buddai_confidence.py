import re

class ConfidenceScorer:
    """
    Calculates confidence scores for generated code based on validation results,
    pattern familiarity, hardware alignment, and context completeness.
    """

    def calculate_confidence(self, code: str, context: dict, validation_results: tuple) -> int:
        """
        Calculates a 0-100 confidence score based on multiple factors.

        Args:
            code (str): The generated code to evaluate.
            context (dict): Context dictionary containing hardware, rules, etc.
            validation_results (tuple): A tuple of (success: bool, issues: list).

        Returns:
            int: A confidence score between 0 and 100.
        """
        score = 0.0

        # 1. Validation pass rate (0-40 points)
        score += self._score_validation(validation_results)

        # 2. Pattern familiarity (0-30 points)
        score += self._score_patterns(code, context)

        # 3. Hardware match (0-20 points)
        score += self._score_hardware(code, context)

        # 4. Context completeness (0-10 points)
        score += self._score_context(context)

        return int(min(100, max(0, score)))

    def should_escalate(self, confidence: int, threshold: int = 70) -> bool:
        """
        Determines if the generation should be escalated or flagged for review.

        Args:
            confidence (int): The calculated confidence score.
            threshold (int): The score below which escalation is triggered.

        Returns:
            bool: True if confidence is below threshold, False otherwise.
        """
        return confidence < threshold

    def _score_validation(self, validation_results: tuple) -> float:
        """
        Calculates score based on validation results (Max 40 points).
        """
        if not validation_results:
            return 0.0

        success, issues = validation_results

        if not success:
            return 0.0

        # Start with full points for success
        score = 40.0

        # Deduct points for non-critical issues/warnings
        if issues:
            # Deduct 5 points per warning, but don't go below 10 if successful
            penalty = len(issues) * 5.0
            score = max(10.0, score - penalty)

        return score

    def _score_patterns(self, code: str, context: dict) -> float:
        """
        Calculates score based on pattern familiarity (Max 30 points).
        Checks if learned rules or preferred patterns appear in the code.
        """
        learned_rules = context.get('learned_rules', [])
        if not learned_rules:
            # If no rules are known/provided, return a neutral baseline
            return 15.0

        matches = 0
        code_lower = code.lower()

        for rule in learned_rules:
            # Heuristic: Check if key terms from the rule exist in the code.
            rule_text = rule if isinstance(rule, str) else str(rule)
            # Extract significant words (simple heuristic)
            keywords = [w.lower() for w in re.split(r'\W+', rule_text) if len(w) > 4]
            
            if keywords and any(k in code_lower for k in keywords):
                matches += 1

        if not matches:
            return 0.0

        # Calculate score proportional to matches, capped at 30
        match_ratio = matches / len(learned_rules)
        # Boost factor (1.5) allows full score even if not 100% of context rules apply
        return min(30.0, match_ratio * 30.0 * 1.5)

    def _score_hardware(self, code: str, context: dict) -> float:
        """
        Calculates score based on hardware match (Max 20 points).
        """
        target_hardware = context.get('hardware', '').lower()
        code_lower = code.lower()

        if not target_hardware or target_hardware == 'generic':
            return 10.0

        # Check for hardware alignment
        if target_hardware in code_lower:
            return 20.0
            
        return 10.0

    def _score_context(self, context: dict) -> float:
        """
        Calculates score based on context completeness (Max 10 points).
        """
        score = 0.0
        if context.get('hardware'): score += 3.0
        if context.get('user_message') or context.get('intent'): score += 3.0
        if context.get('history') or context.get('learned_rules'): score += 4.0
        return min(10.0, score)