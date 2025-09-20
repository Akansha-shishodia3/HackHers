from django.db import models
from sentence_transformers import SentenceTransformer, util

# --- Caching the model ---
# This dictionary will act as a simple cache. Loading the model is resource-intensive,
# so we only want to do it once.
_model_cache = {}

def get_sentence_transformer_model(model_name='all-MiniLM-L6-v2'):
    """Loads the model or retrieves it from the cache."""
    if model_name not in _model_cache:
        _model_cache[model_name] = SentenceTransformer(model_name)
    return _model_cache[model_name]

# Create your models here.
class JobSeeker(models.Model):
    name=models.CharField(max_length=50)
    gender=models.CharField(max_length=6)
    address=models.TextField()
    contactno=models.CharField(max_length=15)
    emailaddress=models.EmailField(max_length=50, primary_key=True)
    dob=models.CharField(max_length=20)
    qualification=models.CharField(max_length=100)
    experience=models.CharField(max_length=20)
    keyskills=models.TextField()
    regdate=models.CharField(max_length=20)
    resume = models.FileField(upload_to='resumes/', null=True, blank=True)

class Skill(models.Model):
    """Model to store job skills."""
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Login(models.Model):
    userid=models.CharField(max_length=50, primary_key=True)
    password=models.CharField(max_length=20)
    usertype=models.CharField(max_length=50)

class Employer(models.Model):
    firmname=models.CharField(max_length=100)
    firmwork=models.TextField()
    firmaddress=models.TextField()
    cpname=models.CharField(max_length=50)
    cpcontactno=models.CharField(max_length=15)
    cpemailaddress=models.EmailField(max_length=50, primary_key=True)
    aadharno=models.CharField(max_length=12)
    panno=models.CharField(max_length=10)
    gstno=models.CharField(max_length=15)
    regdate=models.CharField(max_length=20)

class Enquiry(models.Model):
    name=models.CharField(max_length=50)
    gender=models.CharField(max_length=6)
    address=models.TextField()
    contactno=models.CharField(max_length=15)
    emailaddress=models.EmailField(max_length=50)
    enquirytext=models.TextField()
    posteddate=models.CharField(max_length=20)

class Jobs(models.Model):
    firmname=models.CharField(max_length=100)
    jobtitle=models.CharField(max_length=100)
    post=models.CharField(max_length=50)
    jobdesc=models.TextField()
    qualification=models.CharField(max_length=100)
    skills = models.ManyToManyField(Skill, help_text="Select at least 3 skills." , blank=True,null=True)
    experience=models.CharField(max_length=20)
    location=models.CharField(max_length=100)
    salarypa=models.IntegerField()
    posteddate=models.CharField(max_length=30)
    emailaddress=models.EmailField(max_length=50)

class AppliedJobs(models.Model):
    job = models.ForeignKey(Jobs, on_delete=models.CASCADE,null=True,blank=True)
    empemailaddress=models.EmailField(max_length=50)
    jobtitle=models.CharField(max_length=100)
    post=models.CharField(max_length=50)
    name=models.CharField(max_length=50)
    gender=models.CharField(max_length=6)
    address=models.TextField()
    contactno=models.CharField(max_length=15)
    emailaddress=models.EmailField(max_length=50)
    dob=models.CharField(max_length=20)
    qualification=models.CharField(max_length=100)
    experience=models.CharField(max_length=20)
    keyskills=models.TextField()
    applieddate=models.CharField(max_length=30)


class News(models.Model):
    newstext=models.TextField()
    newsdate=models.CharField(max_length=30)

class InterviewResult(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending Analysis'),
        ('Passed', 'Passed'),
        ('Failed', 'Failed'),
        ('Incomplete', 'Incomplete'),
    ]

    jobseeker = models.ForeignKey(JobSeeker, on_delete=models.CASCADE, related_name='interview_results')
    interview_type = models.CharField(max_length=50)
    interview_details = models.TextField()
    difficulty = models.CharField(max_length=50)
    date_taken = models.DateTimeField(auto_now_add=True)
    results = models.JSONField()
    # New fields to store the analysis outcome
    overall_score = models.FloatField(null=True, blank=True, help_text="Overall score from 0.0 to 1.0")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')

    def __str__(self):
        # This requires the jobseeker to have a 'name' attribute.
        return f"Interview for {self.jobseeker.name} on {self.date_taken.strftime('%Y-%m-%d')}"

    def analyze_answers(self, pass_threshold=0.5):
        """
        Analyzes answers using sentence embeddings, updates each question with a
        score, and sets the overall score and status for the interview.
        """
        model = get_sentence_transformer_model()

        total_score = 0
        processed_results = []
        
        if not self.results:
            self.overall_score = 0
            self.status = 'Incomplete'
            self.save()
            return

        for result in self.results:
            user_answer = result.get('user_answer', '')
            ideal_answer = result.get('ideal_answer', '')

            # Generate embeddings for both answers
            embedding1 = model.encode(user_answer, convert_to_tensor=True)
            embedding2 = model.encode(ideal_answer, convert_to_tensor=True)

            # Compute cosine similarity score
            score = util.pytorch_cos_sim(embedding1, embedding2).item()
            
            result['score'] = max(0, round(score, 4)) # Ensure score is non-negative and round it
            processed_results.append(result)
            total_score += result['score']

        self.results = processed_results
        self.overall_score = total_score / len(self.results)
        self.status = 'Passed' if self.overall_score >= pass_threshold else 'Failed'
        self.save(update_fields=['results', 'overall_score', 'status'])
