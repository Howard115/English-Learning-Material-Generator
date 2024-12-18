from pydantic_ai import Agent, RunContext
from pydantic import BaseModel, Field
from typing import List
from enum import Enum
from pathlib import Path


class ContentType(str, Enum):
    VOCABULARY = "vocabulary"
    EXAMPLE = "example"
    EXERCISE = "exercise"
    DISCUSSION = "discussion"


class VocabularyItem(BaseModel):
    word: str = Field(description="The vocabulary word")
    definition: str = Field(description="Definition of the word")


class LearningSegment(BaseModel):
    vocabulary: List[VocabularyItem] = Field(
        description="List of vocabulary items with definitions"
    )
    example_sentences: List[str] = Field(
        description="Example sentences using the vocabulary"
    )
    practice_exercises: List[str] = Field(
        description="Practice exercises for the content"
    )
    discussion_questions: List[str] = Field(
        description="Discussion questions about the topic"
    )


class ProcessingConfig(BaseModel):
    english_level: str = Field(default="intermediate")
    max_vocab_per_segment: int = Field(default=5)
    include_examples: bool = Field(default=True)


# Create the learning material generation agent
material_generator = Agent(
    "openai:gpt-4o-mini",
    result_type=LearningSegment,
    deps_type=ProcessingConfig,
)


@material_generator.system_prompt
def get_system_prompt(ctx: RunContext[ProcessingConfig]) -> str:
    return f"""You are an expert English language learning material creator.

            Your task is to process text and create structured learning materials with:
            - Vocabulary explanations (max {ctx.deps.max_vocab_per_segment} words per segment)
            - Natural example sentences
            - Practice exercises
            - Discussion questions

            Target English level: {ctx.deps.english_level}
            """


def process_text(text: str, config: ProcessingConfig) -> LearningSegment:
    """Process a text segment and generate learning materials."""
    result = material_generator.run_sync(text, deps=config)
    print(result.cost)
    return result.data


def main():
    # Read input file
    input_path = Path("raw_data.md")
    output_path = Path("Learning_material.md")

    try:
        text = input_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Error: Input file {input_path} not found")
        return

    # Process the text
    config = ProcessingConfig(english_level="intermediate")
    result = process_text(text, config)

    # Generate output markdown
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

    # Write output file
    output_path.write_text(output, encoding="utf-8")
    print()


if __name__ == "__main__":
    main()
