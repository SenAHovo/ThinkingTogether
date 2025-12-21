import os
import time
from dotenv import load_dotenv
from langchain_community.chat_models import ChatZhipuAI
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI


# 加载环境变量
load_dotenv()

llm_organizer = ChatZhipuAI(
    model=os.getenv("ZHIPU_MODEL_NAME"),
    api_key=os.getenv("ZHIPU_API_KEY"),
    temperature=0.5,
)
llm_theorist = ChatOpenAI(
    model=os.getenv("MODEL_NAME"),
    api_key=os.getenv("API_KEY"),
    base_url=os.getenv("BASE_URL"),
    temperature=0.5,
)

llm_practitioner = ChatOpenAI(
    model=os.getenv("KM_MODEL_NAME"),
    api_key=os.getenv("KM_API_KEY"),
    base_url=os.getenv("KM_BASE_URL"),
    temperature=0.5,
)
llm_skeptic = ChatOpenAI(
    model=os.getenv("QWEN_MODEL_NAME"),
    api_key=os.getenv("QWEN_API_KEY"),
    base_url=os.getenv("QWEN_BASE_URL"),
    temperature=0.7,
)
