"""
Decoupled Action Agent
Role: Act & Reason (Standard ReAct Tool-Calling Agent)
Completely decoupled from memory logic.
"""

import os
from typing import List, Dict, Any
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage


class ActionAgent:
    """
    Standard autonomous execution agent.
    Takes actions based solely on current prompt and environment feedback.
    """

    def __init__(self, model_name: str = "openai/gpt-oss-120b"):
        self.llm = ChatGroq(
            model=model_name,
            temperature=0.1,
            api_key=os.getenv("GROQ_API_KEY")
        )

    def decide_action(self, system_prompt: str, prompt_text: str) -> str:
        """
        Generates the next action/command.
        Input prompt may contain a prepended reminder if the sidecar injected one.
        """
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=prompt_text)
        ]
        response = self.llm.invoke(messages)
        return response.content.strip()
