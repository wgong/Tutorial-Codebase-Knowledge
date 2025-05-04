
import os
import logging
import json
from datetime import datetime

# Configure logging
log_directory = os.getenv("LOG_DIR", "logs")
os.makedirs(log_directory, exist_ok=True)
log_file = os.path.join(log_directory, f"llm_calls_{datetime.now().strftime('%Y%m%d')}.log")

# Set up logger
logger = logging.getLogger("llm_logger")
logger.setLevel(logging.INFO)
logger.propagate = False  # Prevent propagation to root logger
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# Simple cache configuration
cache_file = "llm_cache.json"

# By default, we Google Gemini 2.5 pro, as it shows great performance for code understanding
def call_llm(prompt: str, use_cache: bool = True) -> str:
    # Log the prompt
    logger.info(f"PROMPT: {prompt}")
    
    # Check cache if enabled
    if use_cache:
        # Load cache from disk
        cache = {}
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    cache = json.load(f)
            except:
                logger.warning(f"Failed to load cache, starting with empty cache")
        
        # Return from cache if exists
        if prompt in cache:
            logger.info(f"RESPONSE: {cache[prompt]}")
            return cache[prompt]
    
    # Call the LLM if not in cache or cache disabled
    LLM_MODELS = {
        "Google": ["gemini-2.5-pro-exp-03-25"], 
        "Anthropic" : ["claude-3-7-sonnet-20250219"], 
        "OpenAI" : ["gpt-4o-mini"]
    }
    llm_vendor = "Google" # "OpenAI" # 
    llm_model = LLM_MODELS.get(llm_vendor)[0]
    print(f"use LLM model: {llm_vendor} / {llm_model}")
    if llm_vendor == "Google":
        from google import genai
        # Google Gemini
        USE_AI_STUDIO_KEY = True
        if USE_AI_STUDIO_KEY:
            # You can comment the previous line and use the AI Studio key instead:
            client = genai.Client(
                api_key=os.getenv("GEMINI_API_KEY", "your-api_key"),
            )
        else:
            client = genai.Client(
                vertexai=True, 
                # TODO: change to your own project id and location
                project=os.getenv("GEMINI_PROJECT_ID", "your-project-id"),
                location=os.getenv("GEMINI_LOCATION", "us-central1")
            )

        # default Gemini model = Gemini Advanced 2.5 Pro (experimental)
        model = os.getenv("GEMINI_MODEL", llm_model)  

        response = client.models.generate_content(
            model=model,
            contents=[prompt]
        )
        response_text = response.text

    elif llm_vendor == "Anthropic":
        from anthropic import Anthropic
        client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", "your-api-key"))
        response = client.messages.create(
            model=llm_model,  # "claude-3-7-sonnet-20250219",
            max_tokens=21000,
            thinking={
                "type": "enabled",
                "budget_tokens": 20000
            },
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        response_text = response.content[1].text

    elif llm_vendor == "OpenAI":
        from openai import OpenAI
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "your-api-key"))
        r = client.chat.completions.create(
            model=llm_model,  #"gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "text"
            },
            reasoning_effort="medium",
            store=False
        )
        response_text = r.choices[0].message.content
    
    else:
        raise Exception(f"Unsupported LLM vendor: {llm_vendor}")

    # Log the response
    logger.info(f"RESPONSE: {response_text}")
    
    # Update cache if enabled
    if use_cache:
        # Load cache again to avoid overwrites
        cache = {}
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    cache = json.load(f)
            except:
                pass
        
        # Add to cache and save
        cache[prompt] = response_text
        try:
            with open(cache_file, 'w') as f:
                json.dump(cache, f)
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    return response_text

# # Use Anthropic Claude 3.7 Sonnet Extended Thinking
# def call_llm(prompt, use_cache: bool = True):
#     from anthropic import Anthropic
#     client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", "your-api-key"))
#     response = client.messages.create(
#         model="claude-3-7-sonnet-20250219",
#         max_tokens=21000,
#         thinking={
#             "type": "enabled",
#             "budget_tokens": 20000
#         },
#         messages=[
#             {"role": "user", "content": prompt}
#         ]
#     )
#     response_text = response.content[1].text

# # Use OpenAI o1
# def call_llm(prompt, use_cache: bool = True):    
#     from openai import OpenAI
#     client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "your-api-key"))
#     r = client.chat.completions.create(
#         model="o1",
#         messages=[{"role": "user", "content": prompt}],
#         response_format={
#             "type": "text"
#         },
#         reasoning_effort="medium",
#         store=False
#     )
#     response_text = r.choices[0].message.content

if __name__ == "__main__":
    test_prompt = "can you find an arxiv paper titled as A New Exploration into Chinese Characters: from Simplification to Deeper Understanding"
    
    # First call - should hit the API
    print("Making call...")
    response1 = call_llm(test_prompt, use_cache=False)
    print(f"Response: {response1}")
    
