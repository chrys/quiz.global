import json
from jsonschema import validate, ValidationError
import logging

from .models import Quiz, Question, AnswerOption


from .schemas import QuizSchema

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
        my_schema = QuizSchema.model_json_schema()
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
    1. The 'id' field MUST follow the pattern 'q_topic_XXX' where XXX is a 3-digit number (001-999)
    2. The topic part in the ID can include underscores (e.g., 'q_animal_fan_001' is valid)
    3. Example valid IDs: 'q_topic_001', 'q_topic_002', 'q_animal_fan_010', 'q_science_quiz_999'
    4. Return ONLY the JSON array with no additional text or formatting."""
    
def create_quiz(quiz_data: str) -> tuple[bool, str, int]:
    """
    Creates a quiz in the database based on the validated JSON data.
    Uses bulk operations for better performance.
    
    Args:
        quiz_data (str): JSON string containing validated quiz data
        
    Returns:
        tuple: (success: bool, message: str, quiz_id: int)
            - success: True if quiz was created successfully
            - message: Success/error message
            - quiz_id: ID of the created quiz or None if failed
    """
    try:
        # Parse the JSON data
        questions_data = json.loads(quiz_data)
        
        if not questions_data:
            logger.error("Empty quiz data received")
            return False, "Empty quiz data", None
            
        # Extract topic from first question for the quiz title
        first_question = questions_data[0]
        topic = first_question.get('topic', 'General Knowledge')
        
        # Create the Quiz instance (can't bulk create as we need the ID)
        quiz = Quiz.objects.create(
            title=f"Quiz about {topic}",
            description=f"A quiz containing {len(questions_data)} questions about {topic}"
        )
        logger.info(f"Created quiz with ID {quiz.quiz_id}")

        # Prepare questions for bulk creation
        questions_to_create = []
        for q_data in questions_data:
            question = Question(
                quiz=quiz,
                question_text=q_data['question_text'],
                question_type=q_data['type'],
                order_in_quiz=int(q_data['id'].split('_')[-1])
            )
            questions_to_create.append(question)
        
        # Bulk create questions
        questions = Question.objects.bulk_create(questions_to_create)
        logger.info(f"Bulk created {len(questions)} questions")
        
        # Prepare options for bulk creation
        options_to_create = []
        for question, q_data in zip(questions, questions_data):
            for opt in q_data['options']:
                option = AnswerOption(
                    question=question,
                    option_text=opt['text'],
                    is_correct=(opt['option_id'] == q_data['correct_answer_id'])
                )
                options_to_create.append(option)
        
        # Bulk create options
        options = AnswerOption.objects.bulk_create(options_to_create)
        logger.info(f"Bulk created {len(options)} answer options")
        
        logger.info(f"Successfully created quiz {quiz.quiz_id} with {len(questions)} questions")
        return True, "Quiz created successfully", quiz.quiz_id
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON data: {e}")
        return False, f"Invalid JSON data: {str(e)}", None
    except Exception as e:
        logger.error(f"Error creating quiz: {str(e)}")
        return False, f"Failed to create quiz: {str(e)}", None