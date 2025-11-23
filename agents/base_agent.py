"""
Base agent class with LLM initialization and common methods.

All agents inherit from this base class.
"""

import os
from typing import Dict, Any, Optional, List
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class BaseAgent:
    """
    Base class for all agents.
    
    Provides LLM initialization, common methods, and logging.
    """
    
    def __init__(self, agent_name: str, model: str = "qwen-max"):
        """
        Initialize base agent with Qwen LLM.
        
        Args:
            agent_name: Name of the agent (e.g., "InquiryBookingAgent")
            model: Qwen model to use (default: "qwen-max")
        """
        self.agent_name = agent_name
        self.model = model
        
        # Initialize Qwen client using DashScope API
        api_key = os.getenv("DASHSCOPE_API_KEY")
        base_url = os.getenv("QWEN_API_ENDPOINT", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
        
        if not api_key:
            raise ValueError("DASHSCOPE_API_KEY not found in environment variables")
        
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
    
    def call_llm(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        stream: bool = False
    ) -> Any:
        """
        Call Qwen LLM with messages.
        
        Args:
            messages: List of message dicts with "role" and "content"
            temperature: Temperature for generation (0.0-1.0)
            stream: Whether to stream responses
        
        Returns:
            Completion object or stream iterator
        """
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                stream=stream,
            )
            return completion
        except Exception as e:
            print(f"Error calling LLM: {e}")
            raise
    
    def get_llm_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7
    ) -> str:
        """
        Get a single LLM response (non-streaming).
        
        Args:
            messages: List of message dicts
            temperature: Temperature for generation
        
        Returns:
            Response text as string
        """
        completion = self.call_llm(messages, temperature=temperature, stream=False)
        return completion.choices[0].message.content
    
    def format_system_prompt(self, context: Dict[str, Any]) -> str:
        """
        Format system prompt with context.
        
        Override in subclasses for agent-specific prompts.
        
        Args:
            context: Context dictionary with property/host info
        
        Returns:
            Formatted system prompt
        """
        return f"You are {self.agent_name}, an AI assistant for property management."
    
    def log_action(self, action: str, metadata: Dict[str, Any] = None):
        """
        Log an agent action.
        
        This will be connected to the logging system in later steps.
        
        Args:
            action: Description of the action
            metadata: Additional metadata
        """
        print(f"[{self.agent_name}] {action}")
        if metadata:
            print(f"  Metadata: {metadata}")

