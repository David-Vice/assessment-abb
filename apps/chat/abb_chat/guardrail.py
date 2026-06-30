from enum import StrEnum

from abb_rag import ExternalServiceError
from langchain_core.messages import HumanMessage, SystemMessage

from abb_chat.llm import get_aux_model, message_text
from abb_chat.prompts import GUARDRAIL_SYSTEM


class Verdict(StrEnum):
    ON_TOPIC = "on_topic"
    OFF_TOPIC = "off_topic"
    INJECTION = "injection"


async def classify(question: str) -> Verdict:
    """Gate each question: on-topic ABB banking, off-topic, or injection attempt."""

    messages = [SystemMessage(content=GUARDRAIL_SYSTEM), HumanMessage(content=question)]
    try:
        response = await get_aux_model().ainvoke(messages)
    except Exception as error:
        raise ExternalServiceError(f"guardrail failed: {error}") from error

    label = message_text(response.content).strip().upper()
    if "INJECTION" in label:
        return Verdict.INJECTION
    if "OFF" in label and "TOPIC" in label:
        return Verdict.OFF_TOPIC
    return Verdict.ON_TOPIC
