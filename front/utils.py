import json
from jsonschema import validate, ValidationError
import logging

from .models import Quiz, Question, AnswerOption


from .schemas import Quiz

logger = logging.getLogger('custom_logger')


def write_response_to_file(response_text, file_path):
    """
    Writes the response text to a file.
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(response_text)
        logger.info(f"Response successfully written to {file_path}")
    except Exception as e:
        logger.error(f"Error writing response to file: {e}")


def validate_quiz_response(response_text):
    try:
        my_schema = Quiz.model_json_schema()
        # Strip Markdown code block syntax if present
        cleaned_response = response_text.strip()
        if cleaned_response.startswith('```'):
            # Remove opening ```json or ``` line
            cleaned_response = cleaned_response.split('\n', 1)[1]
        if cleaned_response.endswith('```'):
            # Remove closing ``` line
            cleaned_response = cleaned_response.rsplit('\n', 1)[0]
        
        cleaned_response = cleaned_response.strip()
        quiz_data = json.loads(cleaned_response)
        
        # Write the original JSON string to file for debugging
        write_response_to_file(cleaned_response, 'response.json')
        
        logger.info(f"Validating quiz data: {quiz_data}")
        # Validate the JSON structure against the schema
        validate(instance=quiz_data, schema=my_schema)
        return True, ""
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return False, f"Invalid JSON format: {str(e)}"
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        return False, f"Schema validation failed: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error during validation: {e}")
        return False, f"Unexpected error during validation: {str(e)}"


def generate_quiz_prompt(description):
    
    return f"""Create a quiz based on this description: {description}
    IMPORTANT: Return ONLY the raw JSON array without any Markdown formatting or code blocks.
    DO NOT include ```json or ``` markers.
    Generate a complete and valid JSON array of question objects with this structure:
    [
        {{
            "id": "q_topic_001", # IMPORTANT: ID must follow pattern 'q_topic_XXX' where XXX is a 3-digit number
            "topic": "Topic Name",
            "difficulty": "Easy/Medium/Hard",
            "type": "MCQ",
            "question_text": "Question text here?",
            "options": [
                {{"option_id": "a", "text": "First option"}},
                {{"option_id": "b", "text": "Second option"}},
                {{"option_id": "c", "text": "Third option"}},
                {{"option_id": "d", "text": "Fourth option"}}
            ],
            "correct_answer_id": "a",
            "explanation": "Explanation of the correct answer"
        }}
    ]
    IMPORTANT RULES:
    1. The 'id' field MUST follow the exact pattern 'q_topic_XXX' where XXX is a 3-digit number (001-999)
    2. Do not use any other format for the ID field
    3. Example valid IDs: 'q_topic_001', 'q_topic_002', 'q_topic_010', 'q_topic_999'
    4. Return ONLY the JSON array with no additional text or formatting."""
    

def create_quiz(description: str) -> tuple[bool, str, int]:
    """
    Creates a quiz in the database based on the validated response from Gemini API.
    
    Args:
        description (str): The description/topic for the quiz
        
    Returns:
        tuple: (success: bool, message: str, quiz_id: int)
            - success: True if quiz was created successfully
            - message: Success/error message
            - quiz_id: ID of the created quiz or None if failed
    """
    try:
        # Create the Quiz instance
        quiz = Quiz.objects.create(
            title=f"Quiz about {description}",
            description=description
        )
        
        # Create Questions and Options
        for q_data in quiz_data:
            # Create Question
            question = Question.objects.create(
                quiz=quiz,
                question_text=q_data['question_text'],
                question_type=q_data['type'],
                order_in_quiz=int(q_data['id'].split('_')[-1])  # Extract number from q_topic_XXX
            )
            
            # Create Answer Options
            for opt in q_data['options']:
                AnswerOption.objects.create(
                    question=question,
                    option_text=opt['text'],
                    is_correct=(opt['option_id'] == q_data['correct_answer_id'])
                )
        
        logger.info(f"Successfully created quiz {quiz.quiz_id} with {len(quiz_data)} questions")
        return True, "Quiz created successfully", quiz.quiz_id
        
    except Exception as e:
        logger.error(f"Error creating quiz: {str(e)}")
        return False, f"Failed to create quiz: {str(e)}", None