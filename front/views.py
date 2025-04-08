# front/views.py

import google.generativeai as genai
import os
from dotenv import load_dotenv
from django.shortcuts import render
from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt
import json
from jsonschema import validate, ValidationError
from .utils import validate_quiz_response, generate_quiz_prompt


# Load environment variables from .env file
load_dotenv()

# Configure the Gemini API Key
try:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        # Handle the case where the API key is not found
        # Maybe log an error or raise a configuration error
        # For now, we'll rely on genai.configure to potentially raise an error later
        # Or you can prevent startup: raise ValueError("GEMINI_API_KEY not found in environment variables")
        print("Warning: GEMINI_API_KEY environment variable not set.") # Add proper logging
    genai.configure(api_key=api_key)

    # Create the model instance (choose the model you want to use)
    # Common models: 'gemini-pro', 'gemini-1.5-flash', 'gemini-1.5-pro'
    model = genai.GenerativeModel('gemini-2.5-pro-exp-03-25')

except Exception as e:
    # Handle configuration errors more robustly in production
    print(f"Error configuring Gemini API: {e}")
    # You might want to prevent the app from running fully if config fails
    model = None # Set model to None if configuration fails

def home(request):
    """
    Simple view to render the initial query form.
    """
    return render(request, 'home.html') # Reuse the query template



@csrf_exempt
def query_gemini(request):
    if not model:
        return JsonResponse({'error': 'Gemini API is not configured correctly.'}, status=500)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            description = data.get('description', '').strip()

            if not description:
                return JsonResponse({'error': 'Please enter a description.'}, status=400)

            # Generate the prompt
            formatted_prompt = generate_quiz_prompt(description)

            # Send the query to the Gemini API
            print(f"Sending query to Gemini: {formatted_prompt}")
            try:
                response = model.generate_content(formatted_prompt)
            except ConnectionError as e:
                return JsonResponse({'error': 'Failed to connect to Gemini API. Please try again later.'}, status=500)
            except ValueError as e:
                return JsonResponse({'error': f'Invalid response from Gemini API: {str(e)}'}, status=500)
            except Exception as e:
                return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)

            if response.parts:
                # Validate the response
                is_valid, error_message = validate_quiz_response(response.text)
                if is_valid:
                    return JsonResponse({'response': response.text})
                else:
                    return JsonResponse({'error': f'Invalid response format: {error_message}'}, status=500)
            else:
                return JsonResponse({'error': 'Received empty response from Gemini'}, status=500)

        except Exception as e:
            print(f"Error: {e}")
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405) 


@csrf_exempt  # Only for testing, use proper CSRF protection in production
def query_gemini(request):
    """
    Handles GET request to display the form and POST request to query Gemini.
    """
    context = {'query': '', 'response': '', 'error': ''}
    # Define the prompt template
    QUIZ_PROMPT_TEMPLATE = """Create a quiz based on this description: {description}
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
    if not model:
        context['error'] = "Gemini API is not configured correctly. Please check server logs."
        print("Error: Gemini API is not configured.")
        return render(request, 'home.html', context, status=500)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            description = data.get('description', '').strip()
            
            if not description:
                return JsonResponse({'error': 'Please enter a description.'}, status=400)
            
            if not model:
                return JsonResponse({'error': 'Gemini API is not configured correctly.'}, status=500)
            
             # Format the prompt with the user's description
            formatted_prompt = QUIZ_PROMPT_TEMPLATE.format(description=description)
            
            # Send the query to the Gemini API
            print(f"Sending query to Gemini: {formatted_prompt }")
            try:
                response = model.generate_content(formatted_prompt)
            except ConnectionError as e:
                return JsonResponse({'error': 'Failed to connect to Gemini API. Please try again later.'}, status=500)
            except ValueError as e:
                return JsonResponse({'error': f'Invalid response from Gemini API: {str(e)}'}, status=500)
            except Exception as e:
                return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)
            
            if response.parts:
                # Validate the response
                is_valid, error_message = validate_quiz_response(response.text)
                if is_valid:
                    return JsonResponse({'response': response.text})
                else:
                    return JsonResponse({'error': f'Invalid response format: {error_message}'}, status=500)
            else:
                return JsonResponse({'error': 'Received empty response from Gemini'}, status=500)
            
          
        except Exception as e:
            print(f"Error: {e}")
            return JsonResponse({'error': str(e)}, status=500)
            
    return JsonResponse({'error': 'Invalid request method'}, status=405)

    # For both GET requests and after processing POST requests, render the template
    return render(request, 'home.html', context)