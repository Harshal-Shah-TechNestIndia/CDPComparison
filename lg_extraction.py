from langchain_community.llms.bedrock import Bedrock
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

import os
from dotenv import load_dotenv

from pydantic import BaseModel


load_dotenv()

BEDROCK_SERVICE_NAME = os.environ.get("BEDROCK_SERVICE_NAME","")
BEDROCK_REGION_NAME = os.environ.get("BEDROCK_REGION_NAME","")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID","")

class QAExtraction(BaseModel):
    question_no: str
    question_content: str
    answer_content: str


def init_llm_extractor(
    BEDROCK_SERVICE_NAME: str,
    BEDROCK_REGION_NAME: str,
    BEDROCK_MODEL_ID: str,
):
    """
    Initialize a Claude model on Bedrock with:
    - Prompt template
    - Pydantic output parser
    Returns a callable chain: llm.invoke({"query": "<text>"})
    """

    # Initialize model
    llm = Bedrock(
        client=None,                       # optional unless overriding
        model_id=BEDROCK_MODEL_ID,
        region_name=BEDROCK_REGION_NAME,
        service_name=BEDROCK_SERVICE_NAME,
        model_kwargs={
            "max_tokens": 4000,
            "temperature": 0,
        },
    )

    # Parser that converts output → QAExtraction object
    parser = PydanticOutputParser(pydantic_object=QAExtraction)

    # Prompt template for question extraction
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You extract question-answer pairs from raw PDF text. "
         "Return ONLY the structured output in the required JSON format."),
        ("human",
         "Extract the QA from the following text:\n\n{query}\n\n"
         f"Return output in this Pydantic format:\n{parser.get_format_instructions()}")
    ])

    # Build the LCEL chain
    chain = prompt | llm | parser

    return chain