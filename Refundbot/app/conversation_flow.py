"""
Conversation flow management for guided customer interactions.
Ensures step-by-step information gathering without overwhelming users.
"""
import re
from typing import Optional, Dict, Tuple


class ConversationFlow:
    """
    Manages conversation state to enforce natural step-by-step flow.
    Prevents information dumping and guides agent through structured dialogue.
    """
    
    # Max words per response (enforce brevity)
    MAX_RESPONSE_WORDS = 50
    
    # Conversation steps for returns/refunds
    RETURN_STEPS = [
        "item_selection",      # Which item to return?
        "reason_collection",   # Why are you returning it?
        "policy_check",        # Check policy details
        "process_or_escalate"  # Take action
    ]
    
    def __init__(self, context: Dict):
        """
        Initialize flow tracker.
        
        Args:
            context: Session context with collected information
        """
        self.context = context
    
    def get_next_step(self) -> str:
        """
        Determine next conversation step based on what's been collected.
        
        Returns:
            Step identifier (e.g., "item_selection")
        """
        # Check what information we have
        has_item = bool(self.context.get("selected_item_id"))
        has_reason = bool(self.context.get("return_reason"))
        policy_checked = bool(self.context.get("policy_checked"))
        
        # Return next needed step
        if not has_item:
            return "item_selection"
        if not has_reason:
            return "reason_collection"
        if not policy_checked:
            return "policy_check"
        return "process_or_escalate"
    
    def enforce_brevity(self, response: str) -> str:
        """
        Enforce word limit on responses to prevent information dumping.
        
        Args:
            response: Agent's generated response
            
        Returns:
            Truncated response if too long
        """
        words = response.split()
        if len(words) <= self.MAX_RESPONSE_WORDS:
            return response
        
        # Truncate to complete sentences within limit
        sentences = response.split('. ')
        truncated = []
        word_count = 0
        
        for sentence in sentences:
            sentence_words = len(sentence.split())
            if word_count + sentence_words <= self.MAX_RESPONSE_WORDS:
                truncated.append(sentence)
                word_count += sentence_words
            else:
                break
        
        return '. '.join(truncated) + '.'
    
    def enforce_single_question(self, response: str) -> str:
        """
        Keep only the first question if multiple exist.
        
        Args:
            response: Agent's generated response
            
        Returns:
            Response with at most one question
        """
        sentences = response.split('. ')
        questions = [s for s in sentences if '?' in s]
        
        if len(questions) <= 1:
            return response
        
        # Keep only first question
        non_questions = [s for s in sentences if '?' not in s]
        return '. '.join(non_questions + [questions[0]])
    
    def sanitize_internal_details(self, response: str) -> str:
        """
        Remove references to internal thresholds and business logic.
        
        Args:
            response: Agent's generated response
            
        Returns:
            Sanitized response
        """
        # Remove specific dollar amounts that might reveal caps
        response = re.sub(r'\$\d{3,}', '[amount]', response)
        
        # Remove threshold language
        threshold_patterns = [
            (r'exceeds \[amount\] (limit|cap|threshold)', 'requires additional review'),
            (r'(above|over) \[amount\]', 'requires review'),
            (r'limit of \[amount\]', 'policy limit'),
            (r'if.*exceeds.*may need to', 'may need to'),
            (r'because.*\[amount\]', 'due to policy'),
        ]
        
        for pattern, replacement in threshold_patterns:
            response = re.sub(pattern, replacement, response, flags=re.IGNORECASE)
        
        return response
    
    def post_process(self, response: str) -> str:
        """
        Apply all post-processing rules to agent response.
        
        Args:
            response: Raw agent response
            
        Returns:
            Cleaned, conversational response
        """
        # Step 1: Enforce brevity
        response = self.enforce_brevity(response)
        
        # Step 2: Single question only
        response = self.enforce_single_question(response)
        
        # Step 3: Remove internal details
        response = self.sanitize_internal_details(response)
        
        return response


def should_post_process(tool_calls_made: list) -> bool:
    """
    Determine if response needs post-processing based on tools called.
    
    Args:
        tool_calls_made: List of tool names called in this turn
        
    Returns:
        True if post-processing should be applied
    """
    # Always post-process if policy or refund tools were called
    risky_tools = ["get_return_policy", "process_refund", "get_order"]
    return any(tool in risky_tools for tool in tool_calls_made)
