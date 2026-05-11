from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.utils import timezone
import json, PyPDF2, os
from .models import Member, CustomSession

from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate

from dotenv import load_dotenv
load_dotenv()

# Create your views here.
def login(request):
    if request.method == 'POST':
        body = json.loads(request.body)
        email = body.get('email')
        password = body.get('password')

        if not email or not password:
            return JsonResponse({'error': 'Please fill in all fields.', 'code': 400})
        
        try:
            user = Member.objects.get(email=email, password=password)

            # Delete any existing session for the user
            CustomSession.objects.filter(user=user).delete()

            # Create a new session
            customsession = CustomSession.objects.create(
                user=user,
                usertype='loggedin',
                userdata={
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'gender': user.gender,
                    'username': user.username,
                    'email': user.email,
                    'phone_number': user.phone_number,
                },
                created_at=timezone.now(),
            )
    
            # Store data in session
            request.session['jwttoken'] = str(customsession.jwttoken)
            request.session['usertype'] = str(customsession.usertype)
            request.session['userdata'] = customsession.userdata

            return JsonResponse({'status': 'success' ,'msg': 'Login successful'}, status=200)

        except Member.DoesNotExist:
            return JsonResponse({'error': "Invalid email or password", 'code': 400})
        
        except Exception as e:
            return JsonResponse({'error': 'An unexpected error occurred.'}, status=500)

    return render(request, 'pages/login.html')

def signup(request):
    if request.method == 'POST':
        body = json.loads(request.body)

        first_name = body.get('first_name')
        last_name = body.get('last_name')
        gender = body.get('gender')
        username = body.get('username')
        email = body.get('email')
        password = body.get('password')
        confirm_password = body.get('confirm_password')
        phone_number = body.get('phone_number')

        if password != confirm_password:
            return JsonResponse({'error': 'Passwords do not match.', 'code': 400})
        
        if not first_name or not last_name or not gender or not username or not email or not password or not phone_number:
            return JsonResponse({'error': 'Please fill in all fields.', 'code': 400})
        
        if Member.objects.filter(email=email).exists() or Member.objects.filter(username=username).exists():
            return JsonResponse({'error': 'Email or username already exists.', 'code': 400})
        
        try:
            member = Member.objects.create(
                first_name=first_name,
                last_name=last_name,
                gender=gender,
                username=username,
                email=email,
                password=password,
                phone_number=phone_number
            )

            return JsonResponse({'status': 'success' ,'msg': 'Signup successful'}, status=200)

        except Exception as e:
            return JsonResponse({'error': 'An unexpected error occurred.'}, status=500)
        
    return render(request, 'pages/signup.html')
        
def logout(request):
    try:
        if 'jwttoken' in request.session:
            jwttoken = request.session['jwttoken']
            CustomSession.objects.filter(jwttoken=jwttoken).delete()

        request.session.flush()
        return redirect('login')
    
    except Exception as e:
        return JsonResponse({'error': 'An unexpected error occurred.'}, status=500)

def home(request):
    jwttoken = request.session.get('jwttoken')

    if request.session.get('usertype') == "loggedin" and jwttoken:
        
        try:
            customsession = CustomSession.objects.get(jwttoken=jwttoken)
            return render(request, 'pages/home.html', {'usertype': request.session.get('usertype'), 'userdata': request.session.get('userdata')})
        
        except CustomSession.DoesNotExist:
            request.session.flush()
            return redirect('login')
    else:
        return redirect('login')

# helping functions
def extract_text_from_pdf(pdf_file):
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            page_text = page.extract_text()
            if page_text:
                text += page_text
        if not text.strip():
            return "No readable text found in this PDF. It might be a scanned or image-based PDF."
        return text
    except Exception as e:
        return f"Error extracting text from PDF: {str(e)}"

# rest api
# Lazy loader for LLM
def get_llm():
    groq_api_key = os.environ.get('GROQ_API_KEY')
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY environment variable is not set.")
    return ChatGroq(groq_api_key=groq_api_key, model_name="Gemma2-9b-It")

def chat(request):
    groq_chat_prompt = ChatPromptTemplate.from_template(
        """
        Chat as a helpful assistant with the user message as input and you reply as output.
        <context>
        {context}
        </context>
        <message>
        {message}
        </message>
        """
    )
    if request.method == 'POST':
        message = request.POST.get('user_input')
        uploaded_file = request.FILES.get('file')

        if uploaded_file:
            extracted_text = extract_text_from_pdf(uploaded_file)
            
            if extracted_text:
                word_count = len(extracted_text.split())
                if word_count > 2000:
                    return JsonResponse({'error': 'Text in pdf exceeds the maximum allowed word count of 2000. Please shorten the text and try again.', 'code': 400})
                else:
                    llm = get_llm()
                    bot_reply = llm.invoke(groq_chat_prompt.format(context=extracted_text, message=message))
                    bot_reply_content = bot_reply.content.replace('*', ' ')

                    return JsonResponse({'status': 'success', 'msg': bot_reply_content}, status=200)
            else:
                return JsonResponse({'error': 'No readable text found in this PDF.', 'code': 400})
        else:
            return JsonResponse({'error': 'No file uploaded.', 'code': 400})

def readpdf(request): # readpdf and summarize
    groq_summarize_prompt = ChatPromptTemplate.from_template(
        """
        Summarize the following text. Make the summary concise and clear.
        <context>
        {context}
        </context>
        """
    )
    if request.method == 'POST':
        uploaded_file = request.FILES.get('file')

        if uploaded_file:
            extracted_text = extract_text_from_pdf(uploaded_file)
            
            if extracted_text:
                word_count = len(extracted_text.split())
                if word_count > 2000:
                    return JsonResponse({'error': 'Text in pdf exceeds the maximum allowed word count of 2000. Please shorten the text and try again.', 'code': 400})
                else:
                    llm = get_llm()
                    summary = llm.invoke(groq_summarize_prompt.format(context=extracted_text))
                    summary_content = summary.content.replace('*', ' ')
                    
                    return JsonResponse({'status': 'success', 'msg': summary_content}, status=200)
            else:
                return JsonResponse({'error': 'No readable text found in this PDF.', 'code': 400})
        else:
            return JsonResponse({'error': 'No file uploaded.', 'code': 400})
        
def generateQA(request): # generateQA
    groq_qa_prompt = ChatPromptTemplate.from_template(
        """
        Generate 5-10 questions and answers based on the following text. dont ask for more questions
        <context>
        {context}
        </context>
        format:
            Question: <question>
            Answer: 
            <answer>
        """
    )
    if request.method == 'POST':
        uploaded_file = request.FILES.get('file')

        if uploaded_file:
            extracted_text = extract_text_from_pdf(uploaded_file)
            
            if extracted_text:
                word_count = len(extracted_text.split())
                if word_count > 2000:
                    return JsonResponse({'error': 'Text in pdf exceeds the maximum allowed word count of 2000. Please shorten the text and try again.', 'code': 400})
                else:
                    llm = get_llm()
                    qa = llm.invoke(groq_qa_prompt.format(context=extracted_text))
                    qa_content = qa.content.replace('*', ' ')
                    
                    return JsonResponse({'status': 'success', 'msg': qa_content}, status=200)
            else:
                return JsonResponse({'error': 'No readable text found in this PDF.', 'code': 400})
        else:
            return JsonResponse({'error': 'No file uploaded.', 'code': 400})
