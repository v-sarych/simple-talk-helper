from config_descriptioin import LLMConfig
from queue import Queue 
from openai import AsyncOpenAI

class SpeechTranslationAdvisor:
    _llm_config: LLMConfig
    _client: AsyncOpenAI

    def __init__(self, llm_config: LLMConfig):
        self._llm_config = llm_config
        self._client = AsyncOpenAI(
            base_url=llm_config.base_url,
            api_key=llm_config.api_key,
        )

    async def translate(self, context:str, text:str, error_callback) -> str:
        result = ""
        print("llm requested")
        try:
            response = await self._client.chat.completions.create(
                model=self._llm_config.model,
                messages=[{"role": "system", "content": self._llm_config.translator_prompt + context + "\nText: " + text}],
                max_tokens=self._llm_config.max_tokens,
                reasoning_effort="none"
            )
            result = response.choices[0].message.content
        except Exception as e:
            error_callback(f"LLM error: {e}")
        
        print("llm responsed successfully")
            
        return result
    
    async def get_speaking_advice(self, context:str, text:str, error_callback) -> str:
        result = ""
        print("llm requested")
        try:
            response = await self._client.chat.completions.create(
                model=self._llm_config.model,
                messages=[{"role": "system", "content": self._llm_config.advisor_prompt + context + "\nText: " + text}],
                max_tokens=self._llm_config.max_tokens,
                reasoning_effort="none"
            )
            result = response.choices[0].message.content
        except Exception as e:
            error_callback(f"LLM error: {e}")

        print("llm responsed successfully")

        return result