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
        
        # Strip whitespace
        cleaned_response = response_text.strip()
        
        # Remove markdown code blocks and markers
        if cleaned_response.startswith('```'):
            cleaned_response = cleaned_response.split('\n', 1)[1] if '\n' in cleaned_response else cleaned_response[3:]
        if cleaned_response.endswith('```'):
            cleaned_response = cleaned_response.rsplit('\n', 1)[0] if '\n' in cleaned_response else cleaned_response[:-3]
        
        # Remove any remaining markdown markers
        cleaned_response = cleaned_response.replace('```json', '').replace('```', '').strip()
        
        # Find JSON array boundaries - more robust extraction
        start_idx = cleaned_response.find('[')
        end_idx = cleaned_response.rfind(']')
        
        if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
            logger.error(f"Could not find valid JSON array in response")
            return False, "Response does not contain a valid JSON array", ""
        
        # Extract only the JSON array
        cleaned_response = cleaned_response[start_idx:end_idx+1]
        
        # Parse JSON
        quiz_data = json.loads(cleaned_response)
        
        # Write the JSON string to file for debugging
        write_response_to_file(cleaned_response, 'response.json')
        
        logger.info(f"Validating quiz data with {len(quiz_data)} questions")
        # Validate the JSON structure against the schema
        validate(instance=quiz_data, schema=my_schema)
        return True, "", cleaned_response
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return False, f"Invalid JSON format: {str(e)}", ""
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        return False, f"Schema validation failed: {str(e)}", ""
    except Exception as e:
        logger.error(f"Unexpected error during validation: {e}")
        return False, f"Unexpected error during validation: {str(e)}", ""


def generate_quiz_prompt(description):
    
    return f"""You are a quiz generator. Create exactly 5 questions based on: {description}

CRITICAL: Return ONLY valid JSON array. No markdown, no code blocks, no explanations.

[
    {{
        "id": "q_subject_001",
        "topic": "Topic",
        "difficulty": "Easy",
        "type": "MCQ",
        "question_text": "Question?",
        "options": [
            {{"option_id": "a", "text": "Option A"}},
            {{"option_id": "b", "text": "Option B"}},
            {{"option_id": "c", "text": "Option C"}},
            {{"option_id": "d", "text": "Option D"}}
        ],
        "correct_answer_id": "a",
        "explanation": "Why correct"
    }}
]

RULES:
- id: q_<subject>_<3digits> (e.g. q_biology_001)
- difficulty: Easy, Medium, or Hard only
- options: exactly 4
- correct_answer_id: a, b, c, or d
- Generate exactly 5 questions
- START with [ and END with ]
- NO OTHER TEXT"""
    
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