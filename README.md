# English Learning Material Generator

This project contains a Python script (@main.py) that generates English learning materials and answers from raw text input. The main script:

1. Takes raw text input and generates structured learning materials including:
   - Vocabulary with definitions
   - Example sentences
   - Practice exercises 
   - Discussion questions

2. Automatically generates answers for the exercises and discussion questions using an AI assistant that:
   - Provides clear, detailed answers
   - Includes explanations and reasoning
   - Adds helpful learning tips
   - Incorporates relevant vocabulary

3. Formats the output with colored highlighting for key terms

The script uses OpenAI's GPT model through a Pydantic-based agent system to generate contextually appropriate learning content and answers.

Key files:
- `main.py`: Core script orchestrating the full generation pipeline
- `raw_data.md`: Input text file
- `Exquisite_handout.md`: Final formatted output with colored highlighting
