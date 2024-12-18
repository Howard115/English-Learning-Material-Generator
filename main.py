from pathlib import Path
from typing import List, Tuple, Dict
from enum import Enum
from dataclasses import dataclass
import re

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

# ---- Constants ----
DEFAULT_ENGLISH_LEVEL = "intermediate"
DEFAULT_MAX_VOCAB = 5
DEFAULT_ANSWER_LENGTH = 300

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

# ---- Agent Setup ----
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

# ---- Content Extraction Functions ----
def extract_section_items(content: str, section_header: str) -> List[str]:
    """Extract items from a specific markdown section."""
    items = []
    in_section = False
    
    for line in content.split('\n'):
        if line.startswith(f'## {section_header}'):
            in_section = True
            continue
        elif line.startswith('##'):
            in_section = False
            continue
            
        if in_section and line.startswith('- '):
            items.append(line[2:].strip())
                
    return items

def extract_questions(md_content: str) -> Tuple[List[str], List[str]]:
    """Extract practice exercises and discussion questions from markdown content"""
    exercises = extract_section_items(md_content, 'Practice Exercises')
    questions = extract_section_items(md_content, 'Discussion Questions')
    return exercises, questions

def extract_learning_context(md_content: str) -> Tuple[Dict[str, str], List[str]]:
    """Extract vocabulary and example sentences from markdown content"""
    vocabulary = {}
    examples = extract_section_items(md_content, 'Example Sentences')
    
    # Parse vocabulary section
    in_vocab = False
    for line in md_content.split('\n'):
        if line.startswith('## Vocabulary'):
            in_vocab = True
            continue
        elif line.startswith('##'):
            in_vocab = False
            continue
            
        if in_vocab and line.startswith('- '):
            line = line[2:].strip()
            word = line[2:line.index('**', 2)]
            definition = line[line.index(':')+1:].strip(' .')
            vocabulary[word] = definition
                
    return vocabulary, examples

# ---- Content Generation Functions ----
def generate_learning_material(input_path: Path) -> str:
    """Generate learning materials from input text"""
    try:
        text = input_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Error: Input file {input_path} not found")
        return None

    config = ProcessingConfig(english_level=DEFAULT_ENGLISH_LEVEL)
    result = material_generator.run_sync(text, deps=config)
    return format_learning_material(result.data)

def format_learning_material(segment: LearningSegment) -> str:
    """Format learning segment into markdown"""
    sections = [
        ("Vocabulary", [f"- **{item.word}**: {item.definition}" for item in segment.vocabulary]),
        ("Example Sentences", [f"- {sentence}" for sentence in segment.example_sentences]),
        ("Practice Exercises", [f"- {exercise}" for exercise in segment.practice_exercises]),
        ("Discussion Questions", [f"- {question}" for question in segment.discussion_questions])
    ]
    
    output = ["# English Learning Materials"]
    for title, items in sections:
        output.extend([f"## {title}", chr(10).join(items), ""])
    
    return "\n".join(output)

def generate_answers(content: str) -> str:
    """Generate answers for exercises and questions"""
    vocabulary, examples = extract_learning_context(content)
    exercises, questions = extract_questions(content)
    
    config = AnswerConfig(vocabulary=vocabulary, examples=examples)
    
    # Generate answers
    output = [content, "", "# Generated Answers"]
    
    for section_title, items in [
        ("Practice Exercise Answers", exercises),
        ("Discussion Question Answers", questions)
    ]:
        output.append(f"\n## {section_title}")
        for item in items:
            answer = generate_answer(item, config)
            output.extend([
                f"\n### {item}",
                f"**Answer:** {answer.answer}\n",
                f"**Explanation:** {answer.explanation}\n",
                f"**Tips:** {answer.additional_tips}" if answer.additional_tips else ""
            ])
    
    return "\n".join(output)

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

def generate_answer(prompt: str, config: AnswerConfig) -> AnswerResponse:
    """Generate an answer for a single question/exercise"""
    result = answer_generator.run_sync(prompt, deps=config)
    return result.data

def create_colored_content(content: str) -> str:
    """Add color formatting to bold text"""
    pattern = r'\*\*(.*?)\*\*'
    return re.sub(pattern, r'<span style="color: gold">**\1**</span>', content)

# ---- Main Process Functions ----
def main():
    input_path = Path("raw.md")
    output_path = Path("Exquisite_handout.md")

    print("Generating learning materials...")
    content = generate_learning_material(input_path)
    if not content:
        return

    print("Generating answers...")
    content_with_answers = generate_answers(content)

    print("Adding color formatting...")
    colored_content = create_colored_content(content_with_answers)
    output_path.write_text(colored_content, encoding="utf-8")
    
    print(f"\nProcess completed! Final output saved to {output_path}")

if __name__ == "__main__":
    main()
