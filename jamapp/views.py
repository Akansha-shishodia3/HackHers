from django.shortcuts import render, redirect
from . models import JobSeeker, Login, Employer, Enquiry, Jobs, AppliedJobs, News, Skill, InterviewResult
from django.contrib import messages
from django.core.paginator import Paginator
import datetime
from django.db.models import Count, Avg
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, FileResponse, HttpResponse, Http404, StreamingHttpResponse
from django.urls import reverse
from django.conf import settings
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.shortcuts import get_object_or_404
import tempfile
import os
import spacy
import pdfplumber
import docx
from spacy.matcher import PhraseMatcher
import google.generativeai as genai
import json
import time
import requests





# Configure the Gemini AI model with your API key
if settings.GOOGLE_API_KEY:
    genai.configure(api_key=settings.GOOGLE_API_KEY)
# Load the spaCy model once when the server starts. This is a heavy object.
nlp = spacy.load("en_core_web_sm")
# Create your views here.
def index(request):
    nw=News.objects.all()
    return render(request, 'index.html', {'nw':nw})
def about(request):
    nw=News.objects.all()
    return render(request, 'about.html', {'nw':nw})
def jobseekerreg(request):
    nw=News.objects.all()
    return render(request, 'jobseekerreg.html', {'nw':nw})
def employerreg(request):
    nw=News.objects.all()
    return render(request, 'employerreg.html', {'nw':nw})
def login(request):
    nw=News.objects.all()
    return render(request, 'login.html', {'nw':nw})
def contact(request):
    nw=News.objects.all()
    return render(request, 'contact.html', {'nw':nw})
def jsreg(request):
    name=request.POST['name']
    gender=request.POST['gender']
    address=request.POST['address']
    contactno=request.POST['contactno']
    emailaddress=request.POST['emailaddress']
    dob=request.POST['dob']
    qualification=request.POST['qualification']
    experience=request.POST['experience']
    keyskills=request.POST['keyskills']
    regdate=datetime.datetime.today()
    password=request.POST['password']
    usertype='jobseeker'
    js=JobSeeker(name=name, gender=gender, address=address, contactno=contactno, emailaddress=emailaddress, dob=dob, qualification=qualification, experience=experience, keyskills=keyskills, regdate=regdate)
    log=Login(userid=emailaddress, password=password, usertype=usertype)
    js.save()
    log.save()
    messages.success(request, 'Registration is done Successful.')
    return redirect('jobseekerreg')
def ereg(request):
    firmname=request.POST['firmname']
    firmwork=request.POST['firmwork']
    firmaddress=request.POST['firmaddress']
    cpname=request.POST['cpname']
    cpcontactno=request.POST['cpcontactno']
    cpemailaddress=request.POST['cpemailaddress']
    aadharno=request.POST['aadharno']
    panno=request.POST['panno']
    gstno=request.POST['gstno']
    regdate=datetime.datetime.today()
    password=request.POST['password']
    usertype='employer'
    e=Employer(firmname=firmname, firmwork=firmwork, firmaddress=firmaddress, cpname=cpname, cpcontactno=cpcontactno, cpemailaddress=cpemailaddress, aadharno=aadharno, panno=panno, gstno=gstno, regdate=regdate)
    log=Login(userid=cpemailaddress, password=password, usertype=usertype)
    e.save()
    log.save()
    messages.success(request, 'Firm Registered Successfully.')
    return redirect('employerreg')

def saveenq(request):
    name=request.POST['name']
    gender=request.POST['gender']
    address=request.POST['address']
    contactno=request.POST['contactno']
    emailaddress=request.POST['emailaddress']
    enquirytext=request.POST['enquirytext']
    posteddate=datetime.datetime.today()
    enq=Enquiry(name=name, gender=gender, address=address, contactno=contactno, emailaddress=emailaddress, enquirytext=enquirytext, posteddate=posteddate)
    enq.save()
    messages.success(request, 'Enquiry is Submitted Successfully.')
    return redirect('contact')

def validate(request):
    userid=request.POST['userid']
    password=request.POST['password']
    usertype=request.POST['usertype']
    try:
        # Check for userid, password, AND usertype for security
        obj=Login.objects.get(userid=userid, password=password, usertype=usertype)
        if usertype=='employer':
            request.session['employer']=userid
            return redirect('emphome')
        elif usertype=='jobseeker':
            request.session['jobseeker']=userid
            return redirect('jobhome')
        elif usertype=='admin':
            request.session['admin']=userid
            return redirect('adminhome')
    except Login.DoesNotExist:
        messages.error(request, 'Invalid credentials or user type!')
    return redirect('login')

def emphome(request):
    obj = Employer.objects.get(cpemailaddress=request.session['employer'])
    firmname = obj.firmname
    return render(request, 'emphome.html', {'obj': obj})

def postjob(request):
    try:
        if request.session['employer']:
            obj = Employer.objects.get(cpemailaddress=request.session['employer'])
            firmname = obj.firmname
            skills_list = Skill.objects.all()
            return render(request, 'postjob.html', {'obj': obj, 'skills_list': skills_list})
    except:
        return render(request, 'login.html')

def manageapp(request):
    # Ensure employer is logged in
    if 'employer' not in request.session:
        return redirect('login')

    try:
        employer_email = request.session['employer']
        employer_obj = Employer.objects.get(cpemailaddress=employer_email)

        # Get the list of all applicants for this employer, ordered by most recent
        applicants_list = AppliedJobs.objects.filter(empemailaddress=employer_email).order_by('-id')

        # Set up the Paginator
        paginator = Paginator(applicants_list, 10)  # Show 10 applicants per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'page_obj': page_obj,
            'obj': employer_obj
        }
        return render(request, 'manageapp.html', context)

    except Employer.DoesNotExist:
        # If employer in session doesn't exist in DB, clear session and redirect to login
        del request.session['employer']
        return redirect('login')


def empchangepassword(request):
    try:
        if request.session['employer']:
            obj = Employer.objects.get(cpemailaddress=request.session['employer'])
            firmname = obj.firmname
            return render(request, 'empchangepassword.html', {'obj':obj})
    except:
        return render(request, 'login.html')

def emplogout(request):
    request.session['employer']=None
    return render (request, 'login.html')

def pjob(request):
    obj=Employer.objects.get(cpemailaddress=request.session['employer'])
    firmname=obj.firmname
    emailaddress=obj.cpemailaddress
    jobtitle=request.POST['jobtitle']
    post=request.POST['post']
    jobdesc=request.POST['jobdesc']
    qualification=request.POST['qualification']
    skill_ids = request.POST.getlist('skills')
    experience=request.POST['experience']
    location=request.POST['location']
    salarypa=request.POST['salarypa']
    posteddate=datetime.datetime.today()
    j=Jobs(firmname=firmname, jobtitle=jobtitle, post=post, jobdesc=jobdesc, qualification=qualification, experience=experience, location=location, salarypa=salarypa, posteddate=posteddate, emailaddress=emailaddress)
    j.save()
    if skill_ids:
        j.skills.set(skill_ids)
    messages.success(request, 'Job is Posted Successfully.')
    return redirect('postjob')

def empchangepwd(request):
    oldpassword=request.POST['oldpassword']
    newpassword=request.POST['newpassword']
    confirmpassword=request.POST['confirmpassword']
    if newpassword!=confirmpassword:
        messages.error(request, 'New Password and Confirm Password are not same!')
        return redirect('empchangepassword')
    userid=request.session['employer']
    usertype='employer'
    try:
        obj=Login.objects.get(userid=userid, password=oldpassword, usertype=usertype)
        obj.password = newpassword
        obj.save()
        messages.success(request, 'Password changed successfully. Please log in again.')
        return redirect('emplogout')
    except Login.DoesNotExist:
        messages.error(request, 'Old Password is not matched!')
        return redirect('empchangepassword')

def jobhome(request):
    obj=JobSeeker.objects.get(emailaddress=request.session['jobseeker'])
    name=obj.name
    return render(request, 'jobhome.html', {'obj': obj})



def applyjob(request):
    try:
        # Get the logged-in jobseeker's email from the session
        jobseeker_email = request.session['jobseeker']
        jobseeker_obj = JobSeeker.objects.get(emailaddress=jobseeker_email)
    except (KeyError, JobSeeker.DoesNotExist):
        # If the user is not logged in or doesn't exist, redirect to the login page
        return render(request, 'login.html', {'msg': 'Please log in to view and apply for jobs.'})

    # Get a set of job IDs the user has already applied for
    applied_job_ids = set(AppliedJobs.objects.filter(
        emailaddress=jobseeker_email
    ).values_list('job_id', flat=True))

    # Get all jobs, ordered by the newest first, and prefetch related skills
    job_list = Jobs.objects.prefetch_related('skills').all().order_by('-id')

    # --- Pagination Logic ---
    paginator = Paginator(job_list, 10)  # Show 10 jobs per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    # --- End Pagination Logic ---

    context = {
        'page_obj': page_obj,  # Pass the page object instead of the full list
        'obj': jobseeker_obj,
        'applied_job_ids': applied_job_ids
    }
    return render(request, 'applyjob.html', context)


def jobchangepassword(request):
    try:
        if request.session['jobseeker']:
            obj = JobSeeker.objects.get(emailaddress=request.session['jobseeker'])
            name = obj.name
            return render(request, 'jobchangepassword.html', {'obj': obj})
    except:
        return render(request, 'login.html')

def joblogout(request):
    request.session['jobseeker']=None
    return render(request, 'login.html')

def jobchangepwd(request):
    oldpassword=request.POST['oldpassword']
    newpassword=request.POST['newpassword']
    confirmpassword=request.POST['confirmpassword']
    if newpassword!=confirmpassword:
        messages.error(request, 'New Password and Confirm Password are not same.')
        return redirect('jobchangepassword')
    userid=request.session['jobseeker']
    try:
        obj=Login.objects.get(userid=userid, password=oldpassword)
        Login.objects.filter(userid=userid).update(password=newpassword)
        messages.success(request, 'Password changed successfully. Please log in again.')
        return redirect('joblogout')
    except Login.DoesNotExist:
        messages.error(request, 'Old Password does not match.')
        return redirect('jobchangepassword')

def my_resume(request):
    if not request.session.get('jobseeker'):
        return redirect('login')

    try:
        jobseeker = JobSeeker.objects.get(emailaddress=request.session['jobseeker'])
    except JobSeeker.DoesNotExist:
        # This case should not happen if the session is valid, but it's good practice
        return redirect('login')

    if request.method == 'POST':
        resume_file = request.FILES.get('resume')
        if not resume_file:
            messages.error(request, 'Please select a file to upload.')
            return redirect('myresume')

        # File extension validation
        ext = os.path.splitext(resume_file.name)[1]
        valid_extensions = ['.pdf', '.docx']
        if not ext.lower() in valid_extensions:
            messages.error(request, 'Unsupported file type. Please upload a .pdf or .docx file.')
            return redirect('myresume')

        # If a resume already exists, delete the old file before saving the new one
        if jobseeker.resume and os.path.isfile(jobseeker.resume.path):
            os.remove(jobseeker.resume.path)

        jobseeker.resume = resume_file
        jobseeker.save()
        messages.success(request, 'Your resume has been uploaded successfully.')
        return redirect('myresume')

    return render(request, 'my_resume.html', {'obj': jobseeker})

def appliedjobs(request, id):
    job=Jobs.objects.get(id=id)
    jobseeker_email = request.session['jobseeker']

    # Check if the user has already applied to prevent duplicates
    already_applied = AppliedJobs.objects.filter(job=job, emailaddress=jobseeker_email).exists()

    if already_applied:
        # If already applied, show a warning message and redirect back to the job list.
        messages.warning(request, 'You have already applied for this job.')
        return redirect('applyjob')

    empemailaddress=job.emailaddress
    jobtitle=job.jobtitle
    post=job.post
    # Note: It's generally better to link models with ForeignKeys than to copy data.
    obj2=JobSeeker.objects.get(emailaddress=jobseeker_email)
    name=obj2.name
    gender=obj2.gender
    address=obj2.address
    contactno=obj2.contactno
    emailaddress=obj2.emailaddress
    dob=obj2.dob
    qualification=obj2.qualification
    experience=obj2.experience
    keyskills=obj2.keyskills
    applieddate=datetime.datetime.today()
    aj=AppliedJobs(job=job, empemailaddress=empemailaddress, jobtitle=jobtitle, post=post, name=name, gender=gender, address=address, contactno=contactno, emailaddress=emailaddress, dob=dob, qualification=qualification, experience=experience, keyskills=keyskills, applieddate=applieddate)
    aj.save()
    # Show a success message and redirect back to the job list.
    messages.success(request, 'You have successfully applied for this job.')
    return redirect('applyjob')

def jsprofile(request, id):
    # Ensure employer is logged in for security
    if 'employer' not in request.session:
        messages.error(request, "You must be logged in to view applicant profiles.")
        return redirect('login')

    try:
        # Get the application object which links the job and the applicant
        application = AppliedJobs.objects.get(id=id)
        
        # Security Check: The employer viewing this profile should be the one who posted the job.
        employer = Employer.objects.get(cpemailaddress=request.session['employer'])
        if application.empemailaddress != employer.cpemailaddress:
            messages.error(request, "You do not have permission to view this profile.")
            return redirect('manageapp')

        # Get the related JobSeeker to access resume and interview results
        job_seeker = JobSeeker.objects.get(emailaddress=application.emailaddress)

        # --- Aggregate Interview Data for this specific job seeker ---
        results_qs = InterviewResult.objects.filter(jobseeker=job_seeker)

        # 1. Stats Cards
        total_interviews = results_qs.count()
        status_counts_dict = results_qs.values('status').annotate(count=Count('id')).order_by()
        status_map = {item['status']: item['count'] for item in status_counts_dict}
        total_passed = status_map.get('Passed', 0)
        total_failed = status_map.get('Failed', 0)

        avg_score_data = results_qs.filter(status__in=['Passed', 'Failed']).aggregate(avg_score=Avg('overall_score'))
        average_score = (avg_score_data['avg_score'] or 0) * 100

        # 2. Chart Data
        type_data = results_qs.values('interview_type').annotate(count=Count('id')).order_by('interview_type')
        type_labels = [item['interview_type'] for item in type_data]
        type_counts = [item['count'] for item in type_data]

        difficulty_data = results_qs.values('difficulty').annotate(count=Count('id')).order_by('difficulty')
        difficulty_labels = [item['difficulty'] for item in difficulty_data]
        difficulty_counts = [item['count'] for item in difficulty_data]

        status_data = results_qs.values('status').annotate(count=Count('id')).order_by('status')
        status_labels = [item['status'] for item in status_data]
        status_counts_list = [item['count'] for item in status_data]

        context = {
            'obj': application, # The AppliedJobs object for basic details
            'job_seeker': job_seeker, # The JobSeeker object for resume
            'total_interviews': total_interviews,
            'total_passed': total_passed,
            'total_failed': total_failed,
            'average_score': average_score,
            'type_labels': json.dumps(type_labels),
            'type_counts': json.dumps(type_counts),
            'difficulty_labels': json.dumps(difficulty_labels),
            'difficulty_counts': json.dumps(difficulty_counts),
            'status_labels': json.dumps(status_labels),
            'status_counts': json.dumps(status_counts_list),
        }
        return render(request, 'jsprofile.html', context)

    except AppliedJobs.DoesNotExist:
        messages.error(request, "The requested application does not exist.")
        return redirect('manageapp')
    except (JobSeeker.DoesNotExist, Employer.DoesNotExist):
        messages.error(request, "The applicant's or your employer profile could not be found.")
        return redirect('manageapp')

@xframe_options_sameorigin
def view_resume(request, id):
    """
    A view to securely serve a resume file for embedding in an iframe.
    This view allows the file to be displayed by bypassing the default X-Frame-Options: DENY header.
    """
    if 'employer' not in request.session:
        return HttpResponse("Unauthorized", status=401)

    try:
        # 1. Get the application object
        application = get_object_or_404(AppliedJobs, id=id)
        
        # 2. Security Check: Verify the logged-in employer has rights to view this
        employer = get_object_or_404(Employer, cpemailaddress=request.session['employer'])
        if application.empemailaddress != employer.cpemailaddress:
            return HttpResponse("Forbidden", status=403)

        # 3. Get the related JobSeeker and their resume
        job_seeker = get_object_or_404(JobSeeker, emailaddress=application.emailaddress)

        if not job_seeker.resume or not hasattr(job_seeker.resume, 'path'):
            raise Http404("Resume file not found.")
        
        # 4. Check if the file exists on the filesystem
        if not os.path.exists(job_seeker.resume.path):
            raise Http404("Resume file is missing from storage.")

        # 5. Serve the file. FileResponse guesses the Content-Type.
        return FileResponse(open(job_seeker.resume.path, 'rb'))

    except Http404 as e:
        return HttpResponse(str(e), status=404)
    except (Employer.DoesNotExist, JobSeeker.DoesNotExist):
        # This is essentially a permissions failure if the employer/jobseeker doesn't exist
        return HttpResponse("Forbidden", status=403)
    except Exception as e:
        # Log the error for debugging
        print(f"Error in view_resume: {e}")
        return HttpResponse("An internal error occurred.", status=500)

def adminhome(request):
    nw=News.objects.all()
    return render(request, 'adminhome.html', {'nw':nw})

def enquiries(request):
    try:
        if request.session['admin']:
            enq=Enquiry.objects.all()
            return render(request, 'enquiries.html', {'enq':enq})
    except:
        return render(request, 'login.html')

def jobseekers(request):
    try:
        if request.session['admin']:
            js=JobSeeker.objects.all()
            return render(request, 'jobseekers.html', {'js':js})
    except:
        return render(request, 'login.html')

def employers(request):
    try:
        if request.session['admin']:
            emp=Employer.objects.all()
            return render(request, 'employers.html', {'emp':emp})
    except:
        return render(request, 'login.html')

def adminlogout(request):
    request.session['admin']=None
    return render(request, 'login.html')

def addnews(request):
    newstext=request.POST['newstext']
    newsdate=datetime.datetime.today()
    nw=News(newstext=newstext, newsdate=newsdate)
    nw.save()
    return redirect('adminhome')

def deletenews(request, id):
    obj=News.objects.get(id=id)
    obj.delete()
    return redirect('adminhome')

def addSkills(request):
    try:
        if not request.session.get('employer'):
            return redirect('login')
        
        obj = Employer.objects.get(cpemailaddress=request.session['employer'])

        if request.method=='POST':
            skill_name = request.POST.get('skill_name', '').strip()
            if skill_name:
                # Use get_or_create for a more robust, case-insensitive check
                skill, created = Skill.objects.get_or_create(
                    name__iexact=skill_name, defaults={'name': skill_name}
                )
                if created:
                    messages.success(request, f"Skill '{skill.name}' added successfully.")
                else:
                    messages.warning(request, f"Skill '{skill.name}' already exists.")
            else:
                messages.error(request, 'Skill name cannot be empty.')
            return redirect('addskills')
        else:
           return render(request, 'postskills.html', {'obj': obj})
    except:
        return redirect('login')
    
def appliedjobsview(request):
    # Retrieve all applied jobs for the current user, ordered by the most recent first.
    # Ordering is important for consistent pagination.
    applied_jobs_list = AppliedJobs.objects.filter(
        emailaddress=request.session['jobseeker']
    ).select_related('job').prefetch_related('job__skills').order_by('-id')

    # Set up the Paginator with 10 items per page.
    paginator = Paginator(applied_jobs_list, 10)
    
    # Get the page number from the URL's 'page' query parameter (e.g., /applied-jobs/?page=2).
    page_number = request.GET.get('page')
    
    # Get the Page object for the requested page number.
    # .get_page() handles invalid or empty page numbers gracefully.
    page_obj = paginator.get_page(page_number)
    obj=JobSeeker.objects.get(emailaddress=request.session['jobseeker'])
    name=obj.name
    
    # Render the template, passing the 'page_obj' to the context.
    return render(request, 'appliedjobsview.html', {'page_obj': page_obj, 'obj': obj})
def extract_text_from_resume(file_path):
    """Extracts text from a .pdf or .docx file."""
    text = ""
    try:
        if file_path.endswith('.pdf'):
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        elif file_path.endswith('.docx'):
            doc = docx.Document(file_path)
            for para in doc.paragraphs:
                text += para.text + "\n"
    except Exception as e:
        print(f"Error reading file {file_path}: {e}") # For logging/debugging
    return text

def extract_skills_from_text(text):
    """Extracts skills from text using a predefined list from the Skill model."""
    # Get all skills from the database and create patterns for the matcher
    all_skills = [skill.name.lower() for skill in Skill.objects.all()]
    matcher = PhraseMatcher(nlp.vocab, attr='LOWER')
    patterns = [nlp.make_doc(skill) for skill in all_skills]
    matcher.add("SKILL_MATCHER", patterns)
    
    doc = nlp(text)
    matches = matcher(doc)
    
    # Extract the unique matched skills
    found_skills = {doc[start:end].text.lower() for match_id, start, end in matches}
    return found_skills

def skill_suggestions(request):
    try:
        if not request.session.get('jobseeker'):
            return redirect('login')
 
        jobseeker = JobSeeker.objects.get(emailaddress=request.session['jobseeker'])
        jobs = Jobs.objects.prefetch_related('skills').all()
        context = {'obj': jobseeker, 'jobs': jobs, 'analysis_complete': False}
 
        if request.method == 'POST':
            job_id = request.POST.get('job_id')
            if not job_id:
                messages.error(request, "Please select a job to get suggestions.")
                return render(request, 'skill_suggestions.html', context)
 
            if not jobseeker.resume or not hasattr(jobseeker.resume, 'path'):
                messages.error(request, "Please upload your resume on the 'My Resume' page to get suggestions.")
                return render(request, 'skill_suggestions.html', context)
 
            selected_job = Jobs.objects.get(id=job_id)
            
            resume_text = extract_text_from_resume(jobseeker.resume.path)
            user_skills = extract_skills_from_text(resume_text)
            
            # Get job's required skills
            required_skills = set(s.name.lower() for s in selected_job.skills.all())
 
            matching_skills = user_skills.intersection(required_skills)
            missing_skills = required_skills.difference(user_skills)
 
            context.update({
                'selected_job': selected_job,
                'user_skills': user_skills,
                'required_skills': required_skills,
                'matching_skills': matching_skills,
                'missing_skills': missing_skills,
                'analysis_complete': True,
                'selected_job_id': int(job_id)
            })
 
        return render(request, 'skill_suggestions.html', context)
    except JobSeeker.DoesNotExist:
        messages.error(request, "Could not find your profile. Please log in again.")
        return redirect('login')
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {e}")
        return redirect('jobhome')

def generate_questions_from_ai(skills_list, num_questions, difficulty):
    """
    Generates interview questions using the Gemini AI model.
    """
    if not settings.GOOGLE_API_KEY:
        print("GOOGLE_API_KEY not found in settings.")
        return None

    response_text = ""
    try:
        # Using a specific generation config can help get structured output.
        generation_config = {
            "response_mime_type": "application/json",
        }
        model = genai.GenerativeModel(
            'gemini-1.5-flash-latest',
            generation_config=generation_config
        )
        skill_names = ", ".join(skills_list)

        # Refined prompt for better JSON output
        prompt = f"""
        Generate a JSON object. The object must have a single key "questions".
        The value of "questions" should be a list of {num_questions} interview questions for a candidate with '{difficulty}' level expertise in the following skills: {skill_names}.
        Each item in the list must be an object with two keys: "question" (string) and "ideal_answer" (string).
        """

        response = model.generate_content(prompt)
        response_text = response.text
        
        # The API with response_mime_type should return just the JSON text.
        questions_data = json.loads(response_text)
        return questions_data.get('questions', [])

    except json.JSONDecodeError as e:
        # This block will catch errors if the response is not valid JSON.
        print(f"AI response was not valid JSON: {e}")
        print(f"--- Raw AI Response --- \n{response_text}\n-----------------------")
        return None
    except Exception as e:
        # This will catch other errors, like API authentication, network issues, etc.
        print(f"An unexpected error occurred during AI generation: {e}")
        return None

def transcribe_audio_with_gemini(audio_file):
    """
    Transcribes an audio file using the Gemini AI model.
    """
    if not settings.GOOGLE_API_KEY:
        print("GOOGLE_API_KEY not found in settings.")
        return "Error: AI API key not configured."

    temp_path = None
    uploaded_file_name = None  # To ensure deletion in the finally block
    try:
        # Create a temporary file to save the uploaded audio, as Gemini needs a file path.
        # This handles both InMemoryUploadedFile and TemporaryUploadedFile.
        with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as temp_f:
            for chunk in audio_file.chunks():
                temp_f.write(chunk)
            temp_path = temp_f.name

        # Now, upload the file from the temporary path to the Gemini API.
        uploaded_file = genai.upload_file(
            path=temp_path,
            display_name="user_audio_answer",
            mime_type="audio/webm"
        )
        uploaded_file_name = uploaded_file.name

        # Wait for the file to be processed and become ACTIVE. This is the key fix.
        timeout = 120  # 2-minute timeout to prevent infinite loops
        start_time = time.time()
        while uploaded_file.state.name == "PROCESSING":
            if time.time() - start_time > timeout:
                raise Exception("File processing timed out on Google's servers.")
            time.sleep(5)  # Poll the status every 5 seconds
            uploaded_file = genai.get_file(name=uploaded_file.name)

        if uploaded_file.state.name != "ACTIVE":
            # If the file processing failed, provide a more specific and helpful error.
            if uploaded_file.state.name == "FAILED":
                raise Exception(
                    "File processing failed on Google's servers. This might be due to an "
                    "unsupported audio format or a corrupted file. Please try recording again."
                )
            # For any other non-active state.
            raise Exception(f"Uploaded file is not in an ACTIVE state and usage is not allowed. Current state: {uploaded_file.state.name}")

        # Create a model instance and prompt for transcription
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        prompt = "Transcribe the following audio. Provide only the text from the audio, without any extra commentary or formatting."

        response = model.generate_content([prompt, uploaded_file])

        return response.text.strip()
    except Exception as e:
        print(f"An unexpected error occurred during AI transcription: {e}")
        return f"Error: Could not transcribe audio. Details: {e}"
    finally:
        # Ensure the temporary file on the local server is deleted
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        # Ensure the file on Gemini's servers is deleted
        if uploaded_file_name:
            genai.delete_file(name=uploaded_file_name)

def transcribe_audio(request):
    if not request.session.get('jobseeker'):
        return JsonResponse({'status': 'error', 'transcript': 'Authentication required.'}, status=403)

    if request.method == 'POST' and request.FILES.get('audio_data'):
        audio_file = request.FILES['audio_data']
        transcribed_text = transcribe_audio_with_gemini(audio_file)

        if "Error:" in transcribed_text:
             return JsonResponse({'status': 'error', 'transcript': transcribed_text}, status=500)

        return JsonResponse({'status': 'ok', 'transcript': transcribed_text})
    
    return JsonResponse({'status': 'error', 'transcript': 'Invalid request. Expected a POST request with an audio file.'}, status=400)


def mock_interview_options(request):
    """
    Renders the page that gives users the option to start a mock interview based on a job or on specific skills.
    """
    jobseeker = JobSeeker.objects.get(emailaddress=request.session['jobseeker'])
    return render(request, 'mock_interview_options.html', {'obj': jobseeker})

def interview_dashboard(request):
    try:
        if not request.session.get('employer'):
            return redirect('login')

        employer = Employer.objects.get(cpemailaddress=request.session['employer'])

        # --- Data Aggregation for Charts ---
        # Note: This dashboard shows platform-wide analytics. For employer-specific data,
        # the InterviewResult model would need a direct link to the Employer or Job.

        # 1. Get count of interviews by type
        type_data = InterviewResult.objects.values('interview_type').annotate(count=Count('id')).order_by('interview_type')
        type_labels = [item['interview_type'] for item in type_data]
        type_counts = [item['count'] for item in type_data]

        # 2. Get count of interviews by difficulty
        difficulty_data = InterviewResult.objects.values('difficulty').annotate(count=Count('id')).order_by('difficulty')
        difficulty_labels = [item['difficulty'] for item in difficulty_data]
        difficulty_counts = [item['count'] for item in difficulty_data]

        # 3. Get total number of interviews
        total_interviews = InterviewResult.objects.count()

        # --- NEW AGGREGATIONS ---

        # 4. Get count of interviews by status (Passed, Failed, etc.)
        status_data = InterviewResult.objects.values('status').annotate(count=Count('id')).order_by('status')
        status_labels = [item['status'] for item in status_data]
        status_counts_list = [item['count'] for item in status_data]
        
        # Create a dictionary for easy access to counts for stat cards
        status_counts_dict = {item['status']: item['count'] for item in status_data}
        total_passed = status_counts_dict.get('Passed', 0)
        total_failed = status_counts_dict.get('Failed', 0)

        # 5. Get average score for completed interviews
        from django.db.models import Avg
        average_score_data = InterviewResult.objects.filter(status__in=['Passed', 'Failed']).aggregate(avg_score=Avg('overall_score'))
        # Multiply by 100 to get a percentage, handle case where there are no scores
        average_score = (average_score_data['avg_score'] or 0) * 100

        context = {
            'obj': employer,
            'total_interviews': total_interviews,
            'total_passed': total_passed,
            'total_failed': total_failed,
            'average_score': average_score,
            'type_labels': json.dumps(type_labels),
            'type_counts': json.dumps(type_counts),
            'difficulty_labels': json.dumps(difficulty_labels),
            'difficulty_counts': json.dumps(difficulty_counts),
            'status_labels': json.dumps(status_labels),
            'status_counts': json.dumps(status_counts_list),
        }
        return render(request, 'interview_dashboard.html', context)

    except Employer.DoesNotExist:
        messages.error(request, "Employer profile not found. Please log in again.")
        return redirect('login')
    except Exception as e:
        messages.error(request, f"An error occurred while loading the dashboard: {e}")
        return redirect('emphome')

# Employer.objects.get(cpemailaddress=request.session['employer'])

def mock_interview_job(request):
    """
    Handles the mock interview based on a job.
    GET: Shows a list of jobs to select from.
    POST: Proceeds to the interview for the selected job.
    """
    jobseeker = JobSeeker.objects.get(emailaddress=request.session['jobseeker'])
    
    if request.method == 'POST':
        job_id = request.POST.get('job_id')
        num_questions = request.POST.get('num_questions')
        difficulty = request.POST.get('difficulty')

        if not all([job_id, num_questions, difficulty]):
            messages.error(request, "Please fill out all fields.")
            return redirect('mock_interview_job')

        try:
            selected_job = Jobs.objects.prefetch_related('skills').get(id=job_id)
        except Jobs.DoesNotExist:
            messages.error(request, "The selected job does not exist.")
            return redirect('mock_interview_job')

        # Get skills from the job
        skill_names_list = [s.name for s in selected_job.skills.all()]
        if not skill_names_list:
            messages.error(request, "The selected job has no skills listed. Cannot generate interview questions.")
            return redirect('mock_interview_job')

        # --- AI Integration ---
        questions = generate_questions_from_ai(skill_names_list, num_questions, difficulty)

        if questions is None or not questions:
            messages.error(request, "Sorry, we couldn't generate interview questions at this time. Please try again later.")
            return redirect('mock_interview_job')

        # Store the generated questions and other info in the session
        request.session['interview_data'] = {
            'questions': questions,
            'type': 'Job',
            'details': f"{selected_job.jobtitle} at {selected_job.firmname}",
            'difficulty': difficulty,
            'current_question_index': 0,
            'answers': []
        }
        # Redirect to the first question of the interview
        return redirect('interview_session', question_number=1)

    jobs = Jobs.objects.all()
    context = {'jobs': jobs, 'obj': jobseeker}
    return render(request, 'mock_interview_by_job.html', context)


def mock_interview_skills(request):
    """
    Handles the mock interview based on skills.
    GET: Shows a list of skills to select from.
    POST: (Placeholder) Proceeds to the interview for the selected skills.
    """
    jobseeker = JobSeeker.objects.get(emailaddress=request.session['jobseeker'])

    if request.method == 'POST':
        skill_ids = request.POST.getlist('skills')
        num_questions = request.POST.get('num_questions')
        difficulty = request.POST.get('difficulty')

        if not all([skill_ids, num_questions, difficulty]):
            messages.error(request, "Please fill out all fields and select at least one skill.")
            return redirect('mock_interview_skills')

        selected_skills = Skill.objects.filter(id__in=skill_ids)
        skill_names_list = [s.name for s in selected_skills]

        # --- AI Integration ---
        questions = generate_questions_from_ai(skill_names_list, num_questions, difficulty)

        if questions is None or not questions:
            messages.error(request, "Sorry, we couldn't generate interview questions at this time. Please try again later.")
            return redirect('mock_interview_skills')

        # Store the generated questions and other info in the session
        request.session['interview_data'] = {
            'questions': questions,
            'type': 'Skills',
            'details': ", ".join(skill_names_list),
            'difficulty': difficulty,
            'current_question_index': 0,
            'answers': []
        }
        # Redirect to the first question of the interview
        return redirect('interview_session', question_number=1)

    skills = Skill.objects.all().order_by('name')
    context = {'skills': skills, 'obj': jobseeker}
    return render(request, 'mock_interview_by_skill.html', context)


def interview_session(request, question_number):
    # --- AJAX-aware pre-checks ---
    if not request.session.get('jobseeker'):
        if request.method == 'POST':
            return JsonResponse({'status': 'error', 'message': 'Authentication error. Your session may have expired. Please log in again.'}, status=401)
        messages.error(request, "You must be logged in to start an interview.")
        return redirect('login')
        
    interview_data = request.session.get('interview_data')

    if not interview_data:
        if request.method == 'POST':
            return JsonResponse({'status': 'error', 'message': 'Interview session not found. It may have expired or been completed.'}, status=400)
        messages.error(request, "Interview session not found. Please start a new one.")
        return redirect('mock_interview_options')

    questions = interview_data.get('questions', [])
    total_questions = len(questions)

    # --- Progress and Security Checks ---
    current_index = interview_data.get('current_question_index', 0)
    requested_index = question_number - 1

    # Security check: If user tries to access a question out of order.
    if requested_index != current_index:
        if request.method == 'POST':
            # This can happen with double-clicks or race conditions.
            return JsonResponse({'status': 'error', 'message': 'Question mismatch. The interview state is out of sync. Please refresh the page.'}, status=409) # 409 Conflict
        messages.warning(request, "Please answer the questions in order.")
        return redirect('interview_session', question_number=current_index + 1)

    # Security check: If the interview is already over or index is invalid.
    if not 0 <= current_index < total_questions:
        if request.method == 'POST':
             # This case should be handled by the 'finished' status, but as a fallback:
            return JsonResponse({'status': 'error', 'message': 'This interview has already been completed.'}, status=400)
        messages.success(request, "Interview completed! You can view your results in your history.")
        if 'interview_data' in request.session:
            del request.session['interview_data']
        return redirect('interview_history')

    # --- Main Logic ---
    current_question = questions[current_index]

    # --- Timer Management ---
    time_map = {'Easy': 90, 'Moderate': 120, 'Hard': 180}
    duration = time_map.get(interview_data.get('difficulty', 'Moderate'), 120)

    # If the user is submitting an answer for the current question
    if request.method == 'POST':
        user_answer = request.POST.get('user_answer', '')
 
        # Store the answer. Check if it's already been added to prevent duplicates on refresh.
        if len(interview_data.get('answers', [])) == current_index:
            interview_data.setdefault('answers', []).append({
                'question': current_question.get('question'),
                'ideal_answer': current_question.get('ideal_answer'),
                'user_answer': user_answer
            })
 
        # Move to the next question
        interview_data['current_question_index'] = current_index + 1
        request.session.modified = True
 
        next_question_index = current_index + 1
 
        if next_question_index >= total_questions:
            # This was the last question. Save the results and then finish.
            try:
                jobseeker = JobSeeker.objects.get(emailaddress=request.session['jobseeker'])
                
                # Create and save the InterviewResult object
                interview_result = InterviewResult.objects.create(
                    jobseeker=jobseeker,
                    interview_type=interview_data.get('type', 'N/A'),
                    interview_details=interview_data.get('details', 'N/A'),
                    difficulty=interview_data.get('difficulty', 'N/A'),
                    results=interview_data.get('answers', [])
                )

                # NEW: Trigger the automatic analysis of the answers
                interview_result.analyze_answers()

                # Clean up the session
                del request.session['interview_data']
                request.session.modified = True

                # Generate the URL for the results page
                result_url = reverse('interview_result_detail', args=[interview_result.id])

                return JsonResponse({
                    'status': 'finished',
                    'message': 'Interview completed! View your results.',
                    'result_url': result_url
                })
            except Exception as e:
                print(f"Error saving interview result: {e}")
                return JsonResponse({'status': 'error', 'message': 'Could not save your interview results.'}, status=500)
        else:
            # Prepare data for the next question
            next_question = questions[next_question_index]
            next_question['start_time'] = time.time()
            request.session.modified = True
            
            # Generate the URL for the next question to ensure the form POSTs to the correct endpoint
            next_url = reverse('interview_session', args=[next_question_index + 1])

            return JsonResponse({
                'status': 'next_question',
                'question': next_question.get('question'),
                'current_question_number': next_question_index + 1,
                'is_last_question': (next_question_index + 1) == total_questions,
                'duration': duration,
                'start_time': next_question['start_time'],
                'next_url': next_url
            })
 
    # --- GET Request Logic ---
    # Set start time if it's not already set for this question
    if 'start_time' not in current_question:
        current_question['start_time'] = time.time()
        request.session.modified = True

    start_time = current_question['start_time']

    context = {
        'obj': JobSeeker.objects.get(emailaddress=request.session['jobseeker']),
        'interview_info': interview_data,
        'question': current_question,
        'current_question_number': question_number,
        'total_questions': total_questions,
        'is_last_question': question_number == total_questions,
        'duration': duration,
        'start_time': start_time
    }
    return render(request, 'interview_session.html', context)

def terminate_interview(request):
    """
    Handles the forceful termination of an interview session.
    """
    if request.method == 'POST':
        # Check if an interview is in progress before trying to delete
        if 'interview_data' in request.session:
            # Optional: You could save the partial results here before deleting
            del request.session['interview_data']
        
        reason = request.POST.get('reason', 'The interview was terminated prematurely.')
        messages.warning(request, reason)
    
    # Redirect to a safe page, like the jobseeker dashboard
    return redirect('jobhome')


def interview_history(request):
    """
    Displays a list of all past mock interviews for the logged-in user.
    """
    try:
        jobseeker = JobSeeker.objects.get(emailaddress=request.session['jobseeker'])
        # Get all results for the user, ordered by most recent first
        results_list = InterviewResult.objects.filter(jobseeker=jobseeker).order_by('-date_taken')

        # Pagination
        paginator = Paginator(results_list, 10) # 10 results per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'obj': jobseeker,
            'page_obj': page_obj
        }
        return render(request, 'interview_history.html', context)
    except JobSeeker.DoesNotExist:
        messages.error(request, "Please log in to view your history.")
        return redirect('login')


def interview_result_detail(request, result_id):
    """
    Displays the detailed results of a single mock interview.
    """
    try:
        jobseeker = JobSeeker.objects.get(emailaddress=request.session['jobseeker'])
        result = InterviewResult.objects.get(id=result_id, jobseeker=jobseeker)

        # If the result hasn't been analyzed yet, analyze it now on-demand.
        # This will process any old interviews that were taken before the analysis feature was added.
        if result.status == 'Pending':
            result.analyze_answers()
            # The 'result' object is now updated with the score and new status.
        
        context = {
            'obj': jobseeker,
            'result': result
        }
        return render(request, 'interview_result_detail.html', context)
    except JobSeeker.DoesNotExist:
        messages.error(request, "Please log in to view your results.")
        return redirect('login')
    except InterviewResult.DoesNotExist:
        messages.error(request, "The requested interview result was not found or does not belong to you.")
        return redirect('interview_history') # Redirect to the list of interviews

def stream_response_generator(user_message):
    """A generator function that streams the response from the chatbot API."""
    try:
        api_url = "https://api.euron.one/api/v1/euri/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.CHATBOT_API_KEY}"
        }
        payload = {
            "messages": [{"role": "user", "content": user_message}],
            "model": "gemini-2.5-pro",
            "temperature": 0.1,
            "stream": True  # Enable streaming
        }

        # Use a session for better connection management
        with requests.post(api_url, headers=headers, json=payload, stream=True) as response:
            response.raise_for_status()  # Raise an exception for bad status codes

            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith('data: '):
                        json_str = decoded_line[6:]
                        if json_str.strip() == '[DONE]':
                            break
                        try:
                            data = json.loads(json_str)
                            if 'choices' in data and data['choices']:
                                delta = data['choices'][0].get('delta', {})
                                content = delta.get('content')
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        yield f"Error: API request failed. {e}"
    except Exception as e:
        print(f"An unexpected error occurred in stream_response_generator: {e}")
        yield f"Error: An unexpected error occurred. {e}"

def career_advice(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            user_message = body.get('message')

            if not user_message:
                return JsonResponse({'error': 'No message provided.'}, status=400)

            return StreamingHttpResponse(stream_response_generator(user_message), content_type='text/event-stream')
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500) # Catches invalid request body JSON

    # For a GET request, just render the chat page
    obj=JobSeeker.objects.get(emailaddress=request.session['jobseeker'])
    name=obj.name
    return render(request, 'career_advice.html', {'obj': obj})
