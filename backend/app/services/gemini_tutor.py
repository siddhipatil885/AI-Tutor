import os
from groq import Groq
from app.config import get_settings

settings = get_settings()
# We will use the provided Groq API key or fallback to environment variables
api_key = settings.groq_api_key or os.environ.get("GROQ_API_KEY")
if not api_key:
    # Handle missing key gracefully or provide a dummy for initialization
    api_key = "gsk_dummy_key_please_configure"

if "GROQ_API_KEY" not in os.environ:
    os.environ["GROQ_API_KEY"] = api_key

_client = None

def get_groq_client():
    global _client
    if _client is None:
        _client = Groq(api_key=api_key)
    return _client

def generate_hint(
    task_prompt: str, 
    expected_answer: str,
    user_code: str, 
    misconception_name: str, 
    misconception_description: str,
    past_submissions: list[str]
) -> str:
    """
    Generate a pedagogical hint using Groq (Llama).
    """
    client = get_groq_client()
    
    system_instruction = (
        "You are an expert, encouraging programming tutor. "
        "Your goal is to guide the student towards the correct answer using Socratic questioning and pedagogical hints. "
        "Do NOT just give them the correct code. "
        "Help them understand their conceptual misunderstanding."
    )
    
    history_str = "\n".join([f"Attempt {i+1}: {code}" for i, code in enumerate(past_submissions)])
    if not history_str:
        history_str = "None (First attempt)"
        
    prompt = f"""
The student is working on the following task:
{task_prompt}

The correct solution approach should result in:
{expected_answer}

The student submitted this code:
```python
{user_code}
```

An ML diagnosis model has identified that the student suffers from the following misconception:
{misconception_name}: {misconception_description}

Here is the student's previous history of attempts for this problem:
{history_str}

Please provide a gentle, helpful, and concise hint that guides the student's intuition away from their misconception and towards the right solution.
Keep your response short (2-3 sentences), encouraging, and strictly focused on the identified misconception. 
Format your response in Markdown if you want to highlight code syntax.
"""
    
    try:
        completion = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=200,
        )
        return completion.choices[0].message.content
    except Exception as groq_e:
        print(f"Groq API Error: {groq_e}")
        print("Falling back to Gemini...")
        try:
            from google import genai
            
            gemini_key = settings.gemini_api_key or os.environ.get("GEMINI_API_KEY")
            if gemini_key and "GEMINI_API_KEY" not in os.environ:
                os.environ["GEMINI_API_KEY"] = gemini_key
            
            gemini_client = genai.Client()
            response = gemini_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7,
                )
            )
            return response.text
        except Exception as gemini_e:
            print(f"Gemini API Error: {gemini_e}")
            return f"It looks like you're struggling with: {misconception_name}. Try reviewing the problem requirements again."
