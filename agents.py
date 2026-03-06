import base64
import io
import logging
from pypdf import PdfReader
from autogen_ext.models.anthropic import AnthropicBedrockChatCompletionClient, BedrockInfo
from autogen_core.models import ModelInfo
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

from prompts import *
import os
from dotenv import load_dotenv

load_dotenv()

BEDROCK_SERVICE_NAME = os.environ.get("BEDROCK_SERVICE_NAME","")
BEDROCK_REGION_NAME = os.environ.get("BEDROCK_REGION_NAME","")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID","")


AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
# AWS_SESSION_TOKEN = os.environ.get("AWS_SESSION_TOKEN")  # optional for temporary creds


class BaseAgent:
    """Base class for agents with common Bedrock client setup and PDF processing functionality."""
    
    def __init__(self, agent_name: str, system_message: str, save_prefix: str = "result"):
        self.logger = logging.getLogger(__name__)
        # Initialize Bedrock client
        self.client = AnthropicBedrockChatCompletionClient(
            model=BEDROCK_MODEL_ID,
            bedrock_info=BedrockInfo(
                aws_region=BEDROCK_REGION_NAME,
                # aws_access_key_id=AWS_ACCESS_KEY_ID,
                # aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                # aws_session_token=AWS_SESSION_TOKEN,  # may be None
                service_name=BEDROCK_SERVICE_NAME, 

                # AWS credentials should be configured via environment variables or AWS CLI
            ),
            model_info=ModelInfo(
                vision=True,  # Claude 3.7 Sonnet supports vision
                function_calling=True,  # Supports function calling
                json_output=True,
                family="claude-3-7-sonnet",
                structured_output=True,
            )
        )

        # self.client = OpenAIChatCompletionClient(
        #     model="gemini-2.0-flash",
        #     # api_key="sk-...", # Optional if you have an OPENAI_API_KEY environment variable set.
        #     api_key = "AIzaSyBnomj8-0L2BENgg6rqGkufAu0B0sx1Rek",
        #     base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        #     model_info={
        #         "vision": True,
        #         "function_calling": True,
        #         "json_output": True,
        #         "family": "gemini",
        #         "structured_output": True
        #         }
        # )

        # Create the assistant agent
        self.agent = AssistantAgent(
            name=agent_name,
            model_client=self.client,
            system_message=system_message
        )
        
        self.save_prefix = save_prefix

    def extract_text_from_pdf_base64(self, pdf_base64: str) -> str:
        """Extract text from a PDF provided as base64 encoded string."""
        try:
            # Decode base64
            pdf_bytes = base64.b64decode(pdf_base64)
            
            # Create PDF reader from bytes
            pdf_file = io.BytesIO(pdf_bytes)
            pdf_reader = PdfReader(pdf_file)
            
            # Extract text from all pages
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text.strip()
        except Exception as e:
            return f"Error extracting text from PDF: {str(e)}"

    def _extract_text_from_pdf_file(self, file_path: str) -> str:
        """Extract text from a PDF file."""
        try:
            # Open the PDF file directly
            pdf_reader = PdfReader(file_path)
            
            # Extract text from all pages
            pdf_text = ""
            for page in pdf_reader.pages:
                pdf_text += page.extract_text() + "\n"
            
            return pdf_text.strip()
        except Exception as e:
            return f"Error reading PDF file: {str(e)}"

    async def _analyze_extracted_text(self, text: str, query: str = None, default_message: str = None, save_path: str = None) -> str:
        """Analyze extracted text content."""
        # Prepare the message with the extracted text
        if text:
            message = f"Please compare the data from both companies and extract key insights.\n\n\n{text}"
        else:
            message = default_message or f"Please analyze this document and provide key insights:\n\nDocument content:\n{text}"
        
        # Run the agent
        result = await self.agent.run(task=message)
        
        result_content = result.messages[-1].content if result.messages else "No response generated"
        if save_path:
            self.save_result(result_content, save_path)

        return result_content

    async def analyze_pdf_from_file(self, file_path: str, query: str = None, default_message: str = None) -> str:
        """Analyze a PDF document from a file path."""
        # Extract text from PDF
        pdf_text = self._extract_text_from_pdf_file(file_path)
        
        if pdf_text.startswith("Error"):
            return pdf_text
        
        # Analyze the extracted text
        return await self._analyze_extracted_text(pdf_text, query, default_message, file_path)

    # async def analyze_pdf(self, pdf_base64: str, query: str = None) -> str:
    #     """Analyze a PDF document provided as base64 encoded string."""
    #     # Extract text from the base64 encoded PDF
    #     pdf_text = self.extract_text_from_pdf_base64(pdf_base64)
        
    #     if pdf_text.startswith("Error"):
    #         return pdf_text
        
    #     # Prepare the message with the extracted text
    #     if query:
    #         message = f"Please analyze this PDF document and answer the following question: {query}\n\nDocument content:\n{pdf_text}"
    #     else:
    #         message = f"Please analyze this PDF document and provide key insights:\n\nDocument content:\n{pdf_text}"
        
    #     # Run the agent
    #     result = await self.agent.run(task=message)
        
    #     return result.messages[-1].content if result.messages else "No response generated"

    def save_result(self, data: str, pdfpath: str) -> None:
        """Saves the analysis result into a text file in the reports folder"""
        if not data or not isinstance(data, str):
            print("Invalid data provided to save_result")
            return
        
        try:
            # Create reports directory if it doesn't exist
            reports_dir = "reports"
            os.makedirs(reports_dir, exist_ok=True)
            
            base_filename = pdfpath.split("/")[-1].split(".")[0]
            save_filename = f"{self.save_prefix}_{base_filename}.txt"
            full_path = os.path.join(reports_dir, save_filename)
            
            with open(full_path, "w", encoding='utf-8') as f:
                f.write(data)

            print(f"Result Saved to {full_path}")
        except Exception as e:
            print(f"Error saving result: {str(e)}")


class SummarizingAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="summarizing_agent",
            system_message=advisor_agent_prompt,
            save_prefix="acceptance_criteria"
        )

    # define async function
    # result = await self.agent.run(task=message)

    async def summarize_text(self, text: str) -> str:
        """
        Takes a string input and returns a summarized string output.
        """
        if not text or not isinstance(text, str):
            return "Invalid input text."

        query = "Summarize the following content clearly and concisely."

        result = await self._analyze_extracted_text(
            text=text,
            query=query,
            default_message="Provide a concise structured summary of the document."
        )

        return result