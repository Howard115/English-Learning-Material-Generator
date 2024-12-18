from pydantic_ai import Agent, RunContext
from pydantic import BaseModel, Field
from typing import List
from enum import Enum
from pathlib import Path
from dataclasses import dataclass
import re

# ---- Models and Config Classes ----
class ContentType(str, Enum):
    VOCABULARY = "vocabulary"
    EXAMPLE = "example"
    EXERCISE = "exercise"
    DISCUSSION = "discussion"

class VocabularyItem(BaseModel):
    word: str = Field(description="The vocabulary word")
    definition: str = Field(description="Definition of the word")

class LearningSegment(BaseModel):
    vocabulary: List[VocabularyItem]
    example_sentences: List[str]
    practice_exercises: List[str]
    discussion_questions: List[str]

class ProcessingConfig(BaseModel):
    english_level: str = Field(default="intermediate")
    max_vocab_per_segment: int = Field(default=5)
    include_examples: bool = Field(default=True)

class AnswerResponse(BaseModel):
    answer: str
    explanation: str
    additional_tips: str = ""

@dataclass
class AnswerConfig:
    answer_style: str = "detailed"
    max_length: int = 300
    vocabulary: dict[str, str] = None
    examples: List[str] = None

# ---- Agent Definitions ----
material_generator = Agent(
    "openai:gpt-4o-mini",
    result_type=LearningSegment,
    deps_type=ProcessingConfig,
)

answer_generator = Agent(
    "openai:gpt-4o-mini",
    result_type=AnswerResponse,
    deps_type=AnswerConfig
)

# ---- System Prompts ----
@material_generator.system_prompt
def get_material_system_prompt(ctx: RunContext[ProcessingConfig]) -> str:
    return f"""You are an expert English language learning material creator.
            Your task is to process text and create structured learning materials with:
            - Vocabulary explanations (max {ctx.deps.max_vocab_per_segment} words per segment)
            - Natural example sentences
            - Practice exercises
            - Discussion questions
            Target English level: {ctx.deps.english_level}
            """

@answer_generator.system_prompt
def get_answer_system_prompt(ctx: RunContext[AnswerConfig]) -> str:
    # Build vocabulary and examples section if available
    context_sections = []
    
    if ctx.deps.vocabulary:
        vocab_section = "Vocabulary:\n" + "\n".join(
            f"- {word}: {definition}"
            for word, definition in ctx.deps.vocabulary.items()
        )
        context_sections.append(vocab_section)
    
    if ctx.deps.examples:
        examples_section = "Example Usage:\n" + "\n".join(
            f"- {example}" for example in ctx.deps.examples
        )
        context_sections.append(examples_section)
    
    context = "\n\n".join(context_sections)
    if context:
        context = f"\nUse the following context in your answers when relevant:\n\n{context}\n"
    
    return f"""You are an intelligent English learning assistant.
    Your task is to act as a computer science student and provide helpful answers to practice exercises and discussion questions.{context}
    For each question/exercise:
    1. Provide a clear and {ctx.deps.answer_style} answer (max {ctx.deps.max_length} chars)
    2. Include a brief explanation of your reasoning
    3. Add helpful tips when relevant
    4. Incorporate relevant vocabulary words and examples when possible
    Keep responses educational and encouraging, and help reinforce the vocabulary learning.
    """

# ---- Helper Functions ----
def process_text(text: str, config: ProcessingConfig) -> LearningSegment:
    """Process a text segment and generate learning materials."""
    result = material_generator.run_sync(text, deps=config)
    return result.data

def extract_questions(md_content: str) -> tuple[List[str], List[str]]:
    """Extract practice exercises and discussion questions from markdown content"""
    exercises = []
    questions = []
    in_exercises = False
    in_questions = False
    
    for line in md_content.split('\n'):
        if line.startswith('## Practice Exercises'):
            in_exercises = True
            in_questions = False
            continue
        elif line.startswith('## Discussion Questions'):
            in_exercises = False
            in_questions = True
            continue
        elif line.startswith('##'):
            in_exercises = False
            in_questions = False
            continue
            
        if line.startswith('- ') and (in_exercises or in_questions):
            item = line[2:].strip()
            if in_exercises:
                exercises.append(item)
            else:
                questions.append(item)
                
    return exercises, questions

def extract_learning_context(md_content: str) -> tuple[dict[str, str], List[str]]:
    """Extract vocabulary and example sentences from markdown content"""
    vocabulary = {}
    examples = []
    
    in_vocab = False
    in_examples = False
    
    for line in md_content.split('\n'):
        if line.startswith('## Vocabulary'):
            in_vocab = True
            in_examples = False
            continue
        elif line.startswith('## Example Sentences'):
            in_vocab = False
            in_examples = True
            continue
        elif line.startswith('##'):
            in_vocab = False
            in_examples = False
            continue
            
        if line.startswith('- ') and in_vocab:
            # Parse vocabulary line: "- **word**: definition."
            line = line[2:].strip()
            word = line[2:line.index('**', 2)]
            definition = line[line.index(':')+1:].strip(' .')
            vocabulary[word] = definition
        elif line.startswith('- ') and in_examples:
            examples.append(line[2:].strip())
                
    return vocabulary, examples

def generate_answer(prompt: str, config: AnswerConfig) -> AnswerResponse:
    """Generate an answer for a single question/exercise"""
    result = answer_generator.run_sync(prompt, deps=config)
    return result.data

def create_colored_content(content: str) -> str:
    """Add color formatting to bold text"""
    pattern = r'\*\*(.*?)\*\*'
    return re.sub(pattern, r'<span style="color: gold">**\1**</span>', content)

# ---- Main Process Functions ----
def generate_learning_material(input_path: Path, output_path: Path = None):
    """Step 1: Generate learning materials"""
    try:
        text = input_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Error: Input file {input_path} not found")
        return None

    config = ProcessingConfig(english_level="intermediate")
    result = process_text(text, config)

    output = f"""# English Learning Materials
## Vocabulary
{chr(10).join(f"- **{item.word}**: {item.definition}" for item in result.vocabulary)}

## Example Sentences
{chr(10).join(f"- {sentence}" for sentence in result.example_sentences)}

## Practice Exercises
{chr(10).join(f"- {exercise}" for exercise in result.practice_exercises)}

## Discussion Questions
{chr(10).join(f"- {question}" for question in result.discussion_questions)}
"""
    
    if output_path:
        output_path.write_text(output, encoding="utf-8")
    return output

def generate_answers(content: str, output_path: Path = None):
    """Step 2: Generate answers"""
    # Extract context and questions
    vocabulary, examples = extract_learning_context(content)
    exercises, questions = extract_questions(content)
    
    # Generate answers with context
    config = AnswerConfig(
        vocabulary=vocabulary,
        examples=examples
    )
    
    exercise_answers = []
    for ex in exercises:
        print(f"\nProcessing exercise: {ex}")
        answer = generate_answer(ex, config)
        exercise_answers.append((ex, answer))
        
    question_answers = []
    for q in questions:
        print(f"\nProcessing question: {q}")
        answer = generate_answer(q, config)
        question_answers.append((q, answer))
        
    output = content + "\n\n# Generated Answers\n"
    
    output += "\n## Practice Exercise Answers\n"
    for ex, ans in exercise_answers:
        output += f"\n### {ex}\n"
        output += f"**Answer:** {ans.answer}\n\n"
        output += f"**Explanation:** {ans.explanation}\n\n"
        if ans.additional_tips:
            output += f"**Tips:** {ans.additional_tips}\n"
            
    output += "\n## Discussion Question Answers\n"
    for q, ans in question_answers:
        output += f"\n### {q}\n"
        output += f"**Answer:** {ans.answer}\n\n"
        output += f"**Explanation:** {ans.explanation}\n\n"
        if ans.additional_tips:
            output += f"**Tips:** {ans.additional_tips}\n"
            
    if output_path:
        output_path.write_text(output, encoding="utf-8")
    return output

def main():
    # Define file paths
    raw_input_path = Path("raw_data.md")
    final_output_path = Path("Exquisite_handout.md")

    # Step 1: Generate learning materials
    print("Generating learning materials...")
    content = generate_learning_material(raw_input_path, None)
    if content is None:
        return

    # Step 2: Generate answers
    print("Generating answers...")
    content_with_answers = generate_answers(content, None)

    # Step 3: Add color formatting
    print("Adding color formatting...")
    colored_content = create_colored_content(content_with_answers)
    final_output_path.write_text(colored_content, encoding="utf-8")
    
    print(f"\nProcess completed! Final output saved to {final_output_path}")

if __name__ == "__main__":
    main()
