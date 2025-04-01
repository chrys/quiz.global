# front/views.py

import google.generativeai as genai
import os
from dotenv import load_dotenv
from django.shortcuts import render
from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt

# Load environment variables from .env file
load_dotenv()

# Configure the Gemini API Key
try:
    api_key = os.getenv("GEMINI_API_KEY")
    print (api_key)
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

@csrf_exempt  # Only for testing, use proper CSRF protection in production
def query_gemini(request):
    """
    Handles GET request to display the form and POST request to query Gemini.
    """
    context = {'query': '', 'response': '', 'error': ''}

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
            
            # Send the query to the Gemini API
            print(f"Sending query to Gemini: {description}")
            response = model.generate_content(description)
            
            if response.parts:
                return JsonResponse({'response': response.text})
            else:
                return JsonResponse({'error': 'Received empty response from Gemini'}, status=500)
                
        except Exception as e:
            print(f"Error: {e}")
            return JsonResponse({'error': str(e)}, status=500)
            
    return JsonResponse({'error': 'Invalid request method'}, status=405)

    # For both GET requests and after processing POST requests, render the template
    return render(request, 'home.html', context)