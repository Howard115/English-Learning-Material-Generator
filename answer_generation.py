from pathlib import Path
from pydantic import BaseModel
from typing import List
from dataclasses import dataclass
from pydantic_ai import Agent, RunContext

# Define the response model
class AnswerResponse(BaseModel):
    answer: str
    explanation: str
    additional_tips: str = ""

# Define dependencies
@dataclass
class AnswerConfig:
    answer_style: str = "detailed"
    max_length: int = 300
    vocabulary: dict[str, str] = None
    examples: List[str] = None

# Create the answer generator agent
answer_generator = Agent(
    "openai:gpt-4o-mini",
    result_type=AnswerResponse, 
    deps_type=AnswerConfig
)

@answer_generator.system_prompt
def get_system_prompt(ctx: RunContext[AnswerConfig]) -> str:
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
    
    Your task is to stand in the perspective of a computer science student and provide helpful answers to practice exercises and discussion questions.{context}
    
    For each question/exercise:
    1. Provide a clear and {ctx.deps.answer_style} answer (max {ctx.deps.max_length} chars)
    2. Include a brief explanation of your reasoning
    3. Add helpful tips when relevant
    4. Incorporate relevant vocabulary words and examples when possible
    
    Keep responses educational and encouraging, and help reinforce the vocabulary learning.
    """

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

def main():
    # Read learning material
    input_path = Path("Learning_material.md")
    output_path = Path("Reference_answer.md")
    
    try:
        content = input_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Error: Input file {input_path} not found")
        return
        
    # Extract context and questions
    vocabulary, examples = extract_learning_context(content)
    exercises, questions = extract_questions(content)
    
    # Generate answers
    config = AnswerConfig(
        vocabulary=vocabulary,
        examples=examples
    )
    
    # Process exercises
    print("\nGenerating answers for practice exercises...")
    exercise_answers = []
    for ex in exercises:
        print(f"\nProcessing exercise: {ex}")
        answer = generate_answer(ex, config)
        exercise_answers.append((ex, answer))
        
    # Process discussion questions    
    print("\nGenerating answers for discussion questions...")
    question_answers = []
    for q in questions:
        print(f"\nProcessing question: {q}")
        answer = generate_answer(q, config)
        question_answers.append((q, answer))
        
    # Generate output markdown
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
            
    # Write output file
    output_path.write_text(output, encoding="utf-8")
    print(f"\nAnswers generated and saved to {output_path}")

if __name__ == "__main__":
    main()
