import google.generativeai as genai

# Paste your actual API key here again
genai.configure(api_key="My_API_Key")

print("Available Models:")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)