import os
import aiohttp
import logging
from typing import Optional
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

class BaseLLM:
    async def ask(self, question: str, context: Optional[str] = None) -> str:
        raise NotImplementedError

class GroqLLM(BaseLLM):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"

    async def ask(self, question: str, context: Optional[str] = None) -> str:
        messages = []
        if context:
            messages.append({"role": "system", "content": context})
        messages.append({"role": "user", "content": question})

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": 500
                    }
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data['choices'][0]['message']['content']
                    else:
                        logger.error(f"Groq API error: {resp.status}")
                        return "Sorry, I couldn't process your request."
        except Exception as e:
            logger.error(f"Groq request failed: {e}")
            return "An error occurred."

class OpenAILLM(BaseLLM):
    def __init__(self, api_key: str, model: str):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def ask(self, question: str, context: Optional[str] = None) -> str:
        try:
            messages = []
            if context:
                messages.append({"role": "system", "content": context})
            messages.append({"role": "user", "content": question})
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI request failed: {e}")
            return "Sorry, I couldn't process your request."

class FallbackLLM(BaseLLM):
    async def ask(self, question: str, context: Optional[str] = None) -> str:
        q = question.lower()
        if "bitcoin" in q and "price" in q:
            return "Bitcoin price is volatile. Check /btc for current data."
        if "ethereum" in q:
            return "Ethereum is a smart contract platform. Use /coin ethereum for details."
        if "halving" in q:
            return "Bitcoin halving occurs approximately every 4 years, reducing block rewards."
        return "I'm a crypto assistant. Please ask about cryptocurrencies, news, or market trends."

class LLMService:
    def __init__(self):
        provider = os.getenv("LLM_PROVIDER", "groq").lower()
        self.use_fallback = os.getenv("USE_LLAMA_FALLBACK", "true").lower() == "true"
        self._provider = None

        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self._provider = OpenAILLM(api_key, os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"))
                logger.info("OpenAI LLM initialized")
            else:
                logger.warning("OpenAI selected but no API key. Fallback?")
        else:  # default groq
            api_key = os.getenv("GROQ_API_KEY")
            if api_key:
                self._provider = GroqLLM(api_key, os.getenv("GROQ_MODEL", "llama3-70b-8192"))
                logger.info("Groq LLM initialized")
            else:
                logger.warning("Groq selected but no API key. Fallback?")

        if self._provider is None and self.use_fallback:
            self._provider = FallbackLLM()
            logger.info("Using fallback LLM (no API key)")

    async def ask(self, question: str, context: Optional[str] = None) -> str:
        if self._provider is None:
            return "LLM service not configured and fallback disabled."
        return await self._provider.ask(question, context)

llm = LLMService()
