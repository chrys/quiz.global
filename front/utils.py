import json
from jsonschema import validate, ValidationError

def validate_quiz_response(response_text):
    schema = {
        "type": "array",
        "items": {
            "type": "object",
            "required": ["id", "topic", "difficulty", "type", "question_text", "options", "correct_answer_id", "explanation"],
            "properties": {
                "id": {"type": "string", "pattern": "^q_topic_[0-9]{3}$"},
                "topic": {"type": "string"},
                "difficulty": {"type": "string", "enum": ["Easy", "Medium", "Hard"]},
                "type": {"type": "string", "enum": ["MCQ"]},
                "question_text": {"type": "string"},
                "options": {
                    "type": "array",
                    "minItems": 4,
                    "maxItems": 4,
                    "items": {
                        "type": "object",
                        "required": ["option_id", "text"],
                        "properties": {
                            "option_id": {"type": "string", "enum": ["a", "b", "c", "d"]},
                            "text": {"type": "string"}
                        }
                    }
                },
                "correct_answer_id": {"type": "string", "enum": ["a", "b", "c", "d"]},
                "explanation": {"type": "string"}
            }
        }
    }

    try:
        quiz_data = json.loads(response_text)
        validate(instance=quiz_data, schema=schema)
        return True, ""
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON format: {str(e)}"
    except ValidationError as e:
        return False, f"Schema validation failed: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error during validation: {str(e)}"


def generate_quiz_prompt(description):
    return f"""Create a quiz based on this description: {description}
    Generate the response as a JSON array of question objects with this structure:
    [
        {{
            "id": "q_topic_001",
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
    Ensure the response is valid JSON and matches this format exactly."""