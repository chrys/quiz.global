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
from .utils import *
from .schemas import QuizSchema

import logging

logger = logging.getLogger('custom_logger')

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
        logger.error("Warning: GEMINI_API_KEY environment variable not set.") # Add proper logging
    genai.configure(api_key=api_key)

    # Create the model instance (choose the model you want to use)
    # Common models: 'gemini-pro', 'gemini-1.5-flash', 'gemini-1.5-pro'
    model = genai.GenerativeModel('gemini-2.5-pro-exp-03-25')

except Exception as e:
    # Handle configuration errors more robustly in production
    logger.error(f"Error configuring Gemini API: {e}")
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
        logger.error("Error: Gemini API is not configured.")
        return JsonResponse({'error': 'Gemini API is not configured correctly.'}, status=500)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            description = data.get('description', '').strip()

            if not description:
                logger.error("Error: No description provided.")
                return JsonResponse({'error': 'Please enter a description.'}, status=400)

            # Generate the prompt
            formatted_prompt = generate_quiz_prompt(description)
           
            # Send the query to the Gemini API
            logger.info(f"Sending query to Gemini: {formatted_prompt}")
            try:
                response = model.generate_content(
                    formatted_prompt,
                    generation_config={
                        'temperature': 0.7,
                        'top_p': 1,
                        'top_k': 1,
                    }
                )
            except ConnectionError as e:
                logger.error(f"Connection error: {e}")
                return JsonResponse({'error': 'Failed to connect to Gemini API. Please try again later.'}, status=500)
            except ValueError as e:
                logger.error(f"Value error: {e}")
                return JsonResponse({'error': f'Invalid response from Gemini API: {str(e)}'}, status=500)
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)
            write_response_to_file(response.text, 'response.json')
            if response.parts:
                # Validate the response
                is_valid, error_message = validate_quiz_response(response.text)
                if not is_valid:
                    logger.error(f"Invalid response format: {error_message}")
                    return JsonResponse({'error': f'Invalid response format: {error_message}'}, status=500)
    
                # Create quiz if validation passed
                success, message, quiz_id = create_quiz(response.text)
                if success:
                    logger.info(f"Created quiz with ID: {quiz_id}")
                    return JsonResponse({
                        'success': True,
                        'message': message,
                        'quiz_id': quiz_id,
                        'response': response.text
                    })
                else:
                    logger.error(f"Failed to create quiz: {message}")
                    return JsonResponse({
                        'error': f'Failed to create quiz: {message}'
                    }, status=500)
            else:
                logger.error("Error: Received empty response from Gemini")
                return JsonResponse({'error': 'Received empty response from Gemini'}, status=500)

        except Exception as e:
            logger.error(f"Error: {e}")
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405) 


