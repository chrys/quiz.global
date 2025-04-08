from django.test import TestCase, Client
from django.urls import reverse
from .utils import validate_quiz_response, generate_quiz_prompt
import json

class UtilsTestCase(TestCase):
    def test_generate_quiz_prompt(self):
        description = "Python programming"
        prompt = generate_quiz_prompt(description)
        self.assertIn("Python programming", prompt)
        self.assertIn("Generate the response as a JSON array", prompt)

    def test_validate_quiz_response_valid(self):
        valid_response = '[{"id": "q_topic_001", "topic": "Python", "difficulty": "Easy", "type": "MCQ", "question_text": "What is Python?", "options": [{"option_id": "a", "text": "A snake"}, {"option_id": "b", "text": "A programming language"}, {"option_id": "c", "text": "A car"}, {"option_id": "d", "text": "A fruit"}], "correct_answer_id": "b", "explanation": "Python is a programming language."}]'
        is_valid, error_message = validate_quiz_response(valid_response)
        self.assertTrue(is_valid)
        self.assertEqual(error_message, "")

    def test_validate_quiz_response_invalid(self):
        invalid_response = '[{"id": "q_topic_001", "topic": "Python"}]'  # Missing required fields
        is_valid, error_message = validate_quiz_response(invalid_response)
        self.assertFalse(is_valid)
        self.assertIn("Schema validation failed", error_message)
        
class QueryGeminiViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('query_gemini')  # Ensure this matches the name in your `urls.py`

    def test_query_gemini_no_description(self):
        response = self.client.post(self.url, json.dumps({}), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'error': 'Please enter a description.'})

    def test_query_gemini_invalid_method(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.json(), {'error': 'Invalid request method'})

    def test_query_gemini_valid_request(self):
        # Mock the model's `generate_content` method
        from unittest.mock import patch
        with patch('front.views.model.generate_content') as mock_generate_content:
            mock_generate_content.return_value.parts = True
            mock_generate_content.return_value.text = '[{"id": "q_topic_001", "topic": "Python", "difficulty": "Easy", "type": "MCQ", "question_text": "What is Python?", "options": [{"option_id": "a", "text": "A snake"}, {"option_id": "b", "text": "A programming language"}, {"option_id": "c", "text": "A car"}, {"option_id": "d", "text": "A fruit"}], "correct_answer_id": "b", "explanation": "Python is a programming language."}]'

            response = self.client.post(self.url, json.dumps({"description": "Python programming"}), content_type="application/json")
            self.assertEqual(response.status_code, 200)
            self.assertIn("response", response.json())