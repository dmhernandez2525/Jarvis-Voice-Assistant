#!/usr/bin/env python3
"""
Smart Query Router for Jarvis

Dynamically routes queries between:
- Moshi (fast, real-time voice AI) - for simple/quick queries
- Ollama (powerful local LLM) - for complex reasoning

Design goals:
- Zero latency for classification (pattern matching first)
- Parallel processing (classify while Moshi responds)
- Seamless handoff between models
"""

import re
import asyncio
import aiohttp
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Callable

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class QueryComplexity(Enum):
    SIMPLE = "simple"      # Moshi handles it
    COMPLEX = "complex"    # Route to Ollama
    UNCERTAIN = "uncertain"  # Let Moshi try, fallback to Ollama if needed


@dataclass
class RouterDecision:
    complexity: QueryComplexity
    confidence: float  # 0.0 to 1.0
    reason: str
    suggested_model: str  # "moshi" or "ollama"


class SmartRouter:
    """
    Routes queries to the appropriate backend based on complexity.
    Uses fast pattern matching first, with optional LLM verification.
    """

    # Patterns that indicate SIMPLE queries (Moshi can handle)
    SIMPLE_PATTERNS = [
        # Greetings
        r"^(hi|hello|hey|good (morning|afternoon|evening)|howdy)\b",
        r"^how are you",
        r"^what'?s up",
        r"^(thanks|thank you|bye|goodbye|see you|later)\b",

        # Simple questions
        r"^what time is it",
        r"^what'?s the (time|date|weather)",
        r"^(yes|no|yeah|nope|okay|ok|sure|alright)\b",

        # Back-channel
        r"^(uh-?huh|hmm|i see|got it|makes sense|right|exactly)\b",

        # Simple commands
        r"^(stop|pause|cancel|nevermind|never mind)\b",
        r"^(repeat that|say that again|what did you say)\b",
    ]

    # Patterns that indicate COMPLEX queries (route to Ollama)
    COMPLEX_PATTERNS = [
        # Reasoning/explanation requests
        r"\b(explain|why|how does|what causes|analyze|compare)\b.*\?",
        r"\b(difference between|pros and cons|advantages|disadvantages)\b",

        # Code/technical
        r"\b(code|program|function|class|bug|error|debug|fix)\b",
        r"\b(python|javascript|swift|rust|java|sql|api)\b",
        r"\b(algorithm|data structure|complexity|optimize)\b",

        # Math/calculations
        r"\b(calculate|compute|solve|equation|formula|math)\b",
        r"\b\d+\s*[\+\-\*\/\^]\s*\d+",  # Math expressions

        # Research/knowledge
        r"\b(research|study|paper|article|source|reference)\b",
        r"\b(history of|origin of|when was|who invented)\b",
        r"\b(definition|meaning of|what is a)\b.{10,}",  # Long definition requests

        # Multi-step tasks
        r"\b(step by step|walk me through|guide|tutorial)\b",
        r"\b(first|then|after that|finally)\b.*\b(and|then)\b",

        # Creative/generation
        r"\b(write|create|generate|compose|draft)\b.{15,}",
        r"\b(story|poem|essay|email|letter|report)\b",

        # Analysis
        r"\b(summarize|summary|key points|main ideas)\b",
        r"\b(review|critique|evaluate|assess)\b",
    ]

    # Keywords that boost complexity score
    COMPLEXITY_KEYWORDS = {
        "explain": 0.3,
        "why": 0.2,
        "how": 0.15,
        "analyze": 0.4,
        "compare": 0.3,
        "code": 0.5,
        "program": 0.4,
        "calculate": 0.3,
        "write": 0.25,
        "create": 0.2,
        "research": 0.3,
        "summarize": 0.35,
        "step by step": 0.4,
        "in detail": 0.3,
        "thoroughly": 0.3,
    }

    def __init__(self, ollama_host: str = "localhost", ollama_port: int = 11434):
        self.ollama_url = f"http://{ollama_host}:{ollama_port}"
        self.ollama_available = False
        self._compiled_simple = [re.compile(p, re.IGNORECASE) for p in self.SIMPLE_PATTERNS]
        self._compiled_complex = [re.compile(p, re.IGNORECASE) for p in self.COMPLEX_PATTERNS]

    async def check_ollama(self) -> bool:
        """Check if Ollama is available."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.ollama_url}/api/tags", timeout=aiohttp.ClientTimeout(total=2)) as resp:
                    self.ollama_available = resp.status == 200
                    return self.ollama_available
        except Exception:
            self.ollama_available = False
            return False

    def classify_fast(self, query: str) -> RouterDecision:
        """
        Fast pattern-based classification. Zero latency.
        Returns immediately with a routing decision.
        """
        query_lower = query.lower().strip()

        # Check for empty or very short queries
        if len(query_lower) < 3:
            return RouterDecision(
                complexity=QueryComplexity.SIMPLE,
                confidence=0.9,
                reason="Very short query",
                suggested_model="moshi"
            )

        # Check simple patterns first
        for pattern in self._compiled_simple:
            if pattern.search(query_lower):
                return RouterDecision(
                    complexity=QueryComplexity.SIMPLE,
                    confidence=0.85,
                    reason=f"Matched simple pattern",
                    suggested_model="moshi"
                )

        # Check complex patterns
        for pattern in self._compiled_complex:
            if pattern.search(query_lower):
                return RouterDecision(
                    complexity=QueryComplexity.COMPLEX,
                    confidence=0.8,
                    reason=f"Matched complex pattern",
                    suggested_model="ollama"
                )

        # Score based on keywords
        complexity_score = 0.0
        matched_keywords = []
        for keyword, weight in self.COMPLEXITY_KEYWORDS.items():
            if keyword in query_lower:
                complexity_score += weight
                matched_keywords.append(keyword)

        # Adjust for query length (longer queries tend to be more complex)
        word_count = len(query_lower.split())
        if word_count > 20:
            complexity_score += 0.2
        elif word_count > 10:
            complexity_score += 0.1

        # Questions are slightly more likely to be complex
        if query.strip().endswith("?"):
            complexity_score += 0.1

        # Make decision based on score
        if complexity_score >= 0.5:
            return RouterDecision(
                complexity=QueryComplexity.COMPLEX,
                confidence=min(0.9, 0.5 + complexity_score),
                reason=f"High complexity score ({complexity_score:.2f}): {matched_keywords}",
                suggested_model="ollama"
            )
        elif complexity_score >= 0.25:
            return RouterDecision(
                complexity=QueryComplexity.UNCERTAIN,
                confidence=0.5,
                reason=f"Medium complexity score ({complexity_score:.2f})",
                suggested_model="moshi"  # Default to moshi, can escalate
            )
        else:
            return RouterDecision(
                complexity=QueryComplexity.SIMPLE,
                confidence=0.7,
                reason=f"Low complexity score ({complexity_score:.2f})",
                suggested_model="moshi"
            )

    async def classify_with_llm(self, query: str, fast_decision: RouterDecision) -> RouterDecision:
        """
        Optional: Use a small LLM to verify uncertain classifications.
        Only called for UNCERTAIN decisions to minimize latency.
        """
        if not self.ollama_available:
            return fast_decision

        if fast_decision.complexity != QueryComplexity.UNCERTAIN:
            return fast_decision

        # Use a fast, small model for classification
        prompt = f"""Classify this query as SIMPLE or COMPLEX.
SIMPLE = casual chat, greetings, quick questions, yes/no answers
COMPLEX = needs reasoning, explanation, code, math, research, detailed response

Query: "{query}"

Respond with only one word: SIMPLE or COMPLEX"""

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": "llama3.2:1b",  # Fast small model
                        "prompt": prompt,
                        "stream": False,
                        "options": {"num_predict": 10}
                    },
                    timeout=aiohttp.ClientTimeout(total=2)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        response = data.get("response", "").strip().upper()
                        if "COMPLEX" in response:
                            return RouterDecision(
                                complexity=QueryComplexity.COMPLEX,
                                confidence=0.75,
                                reason="LLM classified as complex",
                                suggested_model="ollama"
                            )
                        else:
                            return RouterDecision(
                                complexity=QueryComplexity.SIMPLE,
                                confidence=0.75,
                                reason="LLM classified as simple",
                                suggested_model="moshi"
                            )
        except Exception as e:
            logger.debug(f"LLM classification failed: {e}")

        return fast_decision

    async def route(self, query: str, use_llm_verify: bool = False) -> RouterDecision:
        """
        Main routing function. Fast by default.

        Args:
            query: The user's query text
            use_llm_verify: If True, use LLM for uncertain cases (adds ~1-2s latency)
        """
        # Fast classification first
        decision = self.classify_fast(query)
        logger.info(f"Fast classification: {decision.complexity.value} ({decision.confidence:.0%}) - {decision.reason}")

        # Optional LLM verification for uncertain cases
        if use_llm_verify and decision.complexity == QueryComplexity.UNCERTAIN:
            decision = await self.classify_with_llm(query, decision)
            logger.info(f"LLM verification: {decision.complexity.value} ({decision.confidence:.0%})")

        return decision


class HybridConversationManager:
    """
    Manages hybrid conversations between Moshi and Ollama.
    """

    def __init__(self, router: SmartRouter):
        self.router = router
        self.ollama_model = "deepseek-r1:8b"  # Default model for complex queries
        self.current_mode = "moshi"  # Track current active backend

    async def process_query(
        self,
        query: str,
        on_moshi_response: Optional[Callable] = None,
        on_ollama_response: Optional[Callable] = None,
        on_mode_switch: Optional[Callable] = None
    ) -> dict:
        """
        Process a query through the hybrid system.

        Returns dict with:
        - model: which model handled the query
        - response: the text response
        - should_speak: whether to speak the response via TTS
        """
        decision = await self.router.route(query)

        if decision.suggested_model == "moshi" or not self.router.ollama_available:
            # Let Moshi handle it (already happening via WebSocket)
            self.current_mode = "moshi"
            return {
                "model": "moshi",
                "routed": False,
                "decision": decision
            }
        else:
            # Route to Ollama
            self.current_mode = "ollama"
            if on_mode_switch:
                on_mode_switch("ollama")

            response = await self._query_ollama(query)
            if on_ollama_response:
                on_ollama_response(response)

            return {
                "model": "ollama",
                "routed": True,
                "response": response,
                "decision": decision
            }

    async def _query_ollama(self, query: str) -> str:
        """Query Ollama and return the response."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.router.ollama_url}/api/generate",
                    json={
                        "model": self.ollama_model,
                        "prompt": query,
                        "stream": False
                    },
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("response", "I couldn't generate a response.")
                    else:
                        return f"Ollama error: {resp.status}"
        except Exception as e:
            logger.error(f"Ollama query failed: {e}")
            return f"Error querying Ollama: {e}"

    async def stream_ollama(self, query: str, on_token: Callable[[str], None]) -> str:
        """Stream response from Ollama token by token."""
        full_response = ""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.router.ollama_url}/api/generate",
                    json={
                        "model": self.ollama_model,
                        "prompt": query,
                        "stream": True
                    },
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as resp:
                    async for line in resp.content:
                        if line:
                            import json
                            try:
                                data = json.loads(line)
                                token = data.get("response", "")
                                if token:
                                    full_response += token
                                    on_token(token)
                                if data.get("done", False):
                                    break
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            logger.error(f"Ollama streaming failed: {e}")

        return full_response


# Quick test
async def test_router():
    router = SmartRouter()
    await router.check_ollama()
    print(f"Ollama available: {router.ollama_available}")

    test_queries = [
        "Hello!",
        "How are you?",
        "What time is it?",
        "Explain quantum entanglement in detail",
        "Write a Python function to sort a list",
        "What's the weather like?",
        "Compare React and Vue.js for building web apps",
        "Calculate 15% tip on $47.50",
        "Thanks!",
        "Why do birds migrate south for winter?",
    ]

    print("\n" + "="*60)
    for query in test_queries:
        decision = router.classify_fast(query)
        print(f"Query: {query[:50]:<50}")
        print(f"  → {decision.suggested_model.upper():<6} ({decision.complexity.value}, {decision.confidence:.0%})")
        print(f"    Reason: {decision.reason}")
        print()


if __name__ == "__main__":
    asyncio.run(test_router())
