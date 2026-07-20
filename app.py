# pyre-ignore-all-errors[21]
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, send_from_directory
# pyre-ignore[21]
from flask_sqlalchemy import SQLAlchemy
# pyre-ignore[21]
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime

import os
import re
import json
import logging
from groq import Groq
from dotenv import load_dotenv
# razorpay 1.4.1 depends on pkg_resources; never let a payment-SDK import
# failure crash the whole app at cold start
try:
    import razorpay
except ImportError:
    razorpay = None

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key_change_me')

UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Database Configuration
# Priority: DATABASE_URL -> POSTGRES_URL -> Local SQLite
database_url = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')
if database_url:
    # SQL-Alchemy requires 'postgresql://' instead of 'postgres://' for some versions
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
else:
    # Use an absolute path for the SQLite database
    # On Vercel, /tmp is the only writable directory
    if os.environ.get('VERCEL') == '1' or os.environ.get('VERCEL_ENV'):
        db_path = "/tmp/database.db"
    else:
        # For local development, use a local instance folder
        basedir = os.path.abspath(os.path.dirname(__file__))
        db_path = os.path.join(basedir, 'instance', 'database.db')
        # Create instance folder if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    database_url = f'sqlite:///{db_path}'

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
def _safe_next(target):
    """Only allow same-site relative redirect targets."""
    return bool(target) and target.startswith('/') and not target.startswith('//')

# Login Required Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login', next=request.full_path))
        return f(*args, **kwargs)
    return decorated_function

# Admin Required Decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        user = db.session.get(User, session['user_id'])
        if not user or not user.is_admin:
            flash('Admin access required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    bio = db.Column(db.Text, nullable=True)
    github_link = db.Column(db.String(255), nullable=True)
    linkedin_link = db.Column(db.String(255), nullable=True)
    profile_image_url = db.Column(db.String(255), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # pyre-ignore[28]
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    action = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('activities', lazy=True))

    # pyre-ignore[28]
    def __init__(self, **kwargs):
        super(ActivityLog, self).__init__(**kwargs)

class ContactSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # pyre-ignore[28]
    def __init__(self, **kwargs):
        super(ContactSubmission, self).__init__(**kwargs)



class ProjectRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    product_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # pyre-ignore[28]
    def __init__(self, **kwargs):
        super(ProjectRequest, self).__init__(**kwargs)

class StackLabsRegistration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    year_of_study = db.Column(db.String(50), nullable=False)
    college = db.Column(db.String(200), nullable=False)
    batch = db.Column(db.String(50), nullable=False)
    fee = db.Column(db.Integer, nullable=False)
    transaction_id = db.Column(db.String(100), nullable=True)
    payment_status = db.Column(db.String(20), default='pending')
    is_approved = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # pyre-ignore[28]
    def __init__(self, **kwargs):
        super(StackLabsRegistration, self).__init__(**kwargs)

class StackLabsProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    day = db.Column(db.Integer, nullable=False)
    task_id = db.Column(db.String(50), nullable=False)
    data = db.Column(db.Text, nullable=True) # JSON string
    completed = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('stacklabs_progress', lazy=True))

    # pyre-ignore[28]
    def __init__(self, **kwargs):
        super(StackLabsProgress, self).__init__(**kwargs)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    icon = db.Column(db.String(100), nullable=False)
    link = db.Column(db.String(255), nullable=False)
    program_type = db.Column(db.String(50), nullable=False) # 'stackup' or 'stacklabs'

    def __init__(self, **kwargs):
        super(Course, self).__init__(**kwargs)

initialized = False

def initialize_database():
    global initialized
    if initialized:
        return
        
    try:
        with app.app_context():
            # Ensure all tables exist
            db.create_all()
            
            # Manual Schema Migration: Add missing columns if they don't exist
            # This is specifically for existing production databases (Postgres)
            try:
                from sqlalchemy import text
                
                # List of columns that might be missing from older versions
                # Format: (table_name, column_name, type_sql)
                migrations = [
                    ('stack_labs_registration', 'is_approved', 'BOOLEAN DEFAULT FALSE'),
                    ('stack_labs_registration', 'transaction_id', 'VARCHAR(100)'),
                    ('stack_labs_registration', 'payment_status', "VARCHAR(20) DEFAULT 'pending'"),
                    ('stack_labs_registration', 'timestamp', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
                    ('stack_labs_progress', 'data', 'TEXT'), # JSON field
                    ('user', 'is_admin', 'BOOLEAN DEFAULT FALSE')
                ]
                
                for table, col, type_sql in migrations:
                    try:
                        # Attempt to add column. Postgres will throw an error if it already exists
                        # We use 'ALTER TABLE ... ADD COLUMN IF NOT EXISTS' for modern PG, 
                        # but check-first is safer across dialects.
                        db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {type_sql}"))
                        db.session.commit()
                        logger.info(f"Added column {col} to {table}")
                    except Exception:
                        db.session.rollback()
                        # Column already exists? 
                        pass
            except Exception as e:
                logger.error(f"Migration error: {e}")
                
            logger.info("Database tables verified/created.")
            
            # Create initial admin if no users exist
            if not User.query.first():
                admin = User(
                    name="Admin",
                    email="admin@stackeducation.com",
                    password_hash=generate_password_hash("admin123"),
                    is_admin=True
                )
                db.session.add(admin)
                db.session.commit()
                logger.info("Created default admin user")
            
            # Seed initial Courses
            if not Course.query.first():
                seed_courses = [
                    Course(title="Cyber Security", description="Master ethical hacking, network defense, and cryptography.", icon="security", link="#", program_type="stackup"),
                    Course(title="Blockchain", description="Build decentralized applications and smart contracts.", icon="currency_bitcoin", link="#", program_type="stackup"),
                    Course(title="ATC", description="Advanced Technology Curriculum for futuristic development.", icon="flight_takeoff", link="#", program_type="stackup"),
                    Course(title="Full Stack 101", description="Build comprehensive web applications from frontend to backend.", icon="developer_mode", link="#", program_type="stacklabs"),
                    Course(title="Cyber Security 101", description="Gain practical experience in securing infrastructure and applications.", icon="shield", link="#", program_type="stacklabs")
                ]
                for sc in seed_courses:
                    db.session.add(sc)
                db.session.commit()
                logger.info("Seed data for Courses added.")
            
            initialized = True
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        initialized = True 

@app.before_request
def ensure_db_is_initialized():
    try:
        initialize_database()
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        # Continue without database for basic functionality

@app.route('/.well-known/appspecific/com.chrome.devtools.json')
def chrome_devtools():
    return jsonify({})

@app.route('/robots.txt')
def robots():
    return send_from_directory('static', 'robots.txt')

@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory('static', 'sitemap.xml')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'favicon.ico')

@app.route('/apple-touch-icon.png')
@app.route('/apple-touch-icon-precomposed.png')
def apple_touch_icon():
    return send_from_directory('static', 'apple-touch-icon.png')

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Stack Education API is running'})

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering index page: {e}")
        return "Stack Education - Loading...", 500

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        if User.query.filter_by(email=email).first():
            return render_template('signup.html',
                                   error='An account with this email already exists. Try logging in instead.')

        new_user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password)
        )

        db.session.add(new_user)
        db.session.commit()
        
        # Log activity
        log = ActivityLog(user_id=new_user.id, action="Created an account")
        db.session.add(log)
        db.session.commit()

        # Log the new user straight in so they continue where they started
        session['user_id'] = new_user.id
        session['user_name'] = new_user.name

        flash('Account created successfully! Welcome to stackeducation.', 'success')
        next_page = request.args.get('next')
        if _safe_next(next_page):
            return redirect(next_page)
        return redirect(url_for('index'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = User.query.filter_by(email=email).first()

        if not user:
            return render_template('login.html',
                                   error='No account found with this email. Please sign up first.')
        if not check_password_hash(user.password_hash, password):
            return render_template('login.html',
                                   error='Incorrect password. Please try again.')

        session['user_id'] = user.id
        session['user_name'] = user.name
        
        # Log activity
        log = ActivityLog(user_id=user.id, action="Logged in")
        db.session.add(log)
        db.session.commit()
        
        # Support redirecting back to intended page (same-site paths only)
        next_page = request.args.get('next')
        if _safe_next(next_page):
            return redirect(next_page)
            
        # Redirect admin to admin panel, users to the resume builder
        if user.is_admin:
            return redirect(url_for('admin'))
        else:
            return redirect(url_for('stackbuild_resume'))

    return render_template('login.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        
        # Store as an inquiry so admin can see and respond
        submission = ContactSubmission(
            name="Password Reset Request",
            email=email,
            message="User requested a password reset. Please email them manually to verify."
        )
        db.session.add(submission)
        db.session.commit()
        
        flash('We will check into it and mail you as soon as possible.', 'success')
        return redirect(url_for('login'))
    return render_template('forgot_password.html')



@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    return redirect(url_for('index'))



@app.route('/stackup')
def stackup():
    courses = Course.query.filter_by(program_type='stackup').all()
    return render_template('stackup.html', courses=courses)

@app.route('/stacklabs')
def stacklabs():
    programs = Course.query.filter_by(program_type='stacklabs').all()
    return render_template('stacklabs.html', programs=programs)

@app.route('/new-notification')
def new_notification():
    return render_template('new_notification.html')



@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Server Error: {error}")
    return "Internal Server Error. Please contact admin.", 500

@app.route('/stackbuild')
def stackbuild():
    return render_template('stack.build/index.html')

@app.route('/stackbuild/clients')
def stackbuild_clients():
    return render_template('stack.build/clients.html')

@app.route('/pixelcraft')
def pixelcraft():
    return render_template('pixelcraft.html')

@app.route('/stackbuild/resume')
@login_required
def stackbuild_resume():
    """StackBuild Resume Builder — payment gated; admins get free access."""
    admin_password = os.environ.get('RESUME_UNLOCK_PASSWORD')
    if admin_password and request.args.get('password') == admin_password:
        session['resume_unlocked'] = True
    user = db.session.get(User, session['user_id'])
    is_admin = bool(user and user.is_admin) or session.get('is_admin', False)
    unlocked = is_admin or session.get('resume_unlocked', False)
    return render_template('stack.build/resume.html', unlocked=unlocked)

@app.route('/api/resume/admin-unlock', methods=['POST'])
@login_required
def resume_admin_unlock():
    """Server-side admin unlock for the resume builder (password from env)."""
    data = request.json or {}
    admin_password = os.environ.get('RESUME_UNLOCK_PASSWORD')
    if admin_password and data.get('password') == admin_password:
        session['resume_unlocked'] = True
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Incorrect admin password.'}), 401

RESUME_TAILOR_SYSTEM_PROMPT = """You are an elite ATS (Applicant Tracking System) resume writer. You rewrite a candidate's existing resume so it is perfectly tailored to a specific job description and scores as highly as possible in ATS keyword screening, while staying 100% truthful to the candidate's real background.

RULES:
1. Extract the most important hard skills, tools, technologies, certifications, and soft skills from the JOB DESCRIPTION. Use the JD's EXACT wording for these keywords (ATS match on exact phrases).
2. Weave those keywords naturally into the summary, skills groups, and experience/project bullet points — only where the candidate's real background supports them. NEVER invent employers, job titles, degrees, dates, or experience the candidate does not have.
3. Rewrite every bullet point to start with a strong action verb, include measurable impact (numbers, %, scale) where the source resume provides them, and stay under 2 lines. Use past tense for past roles and present tense for the current role. Never use first-person pronouns.
4. The professional summary must be 3-4 sentences, mirror the job title and top JD requirements, and read naturally.
5. Set the "title" field to the exact job title from the JD when the candidate's background reasonably supports it.
6. Organize skills into clear groups (e.g. Languages, Frameworks, Tools, Cloud) with JD keywords listed first inside each group.
7. Where the JD uses an acronym, include both the acronym and its expansion once (e.g. "CI/CD (Continuous Integration/Continuous Delivery)") so both forms match in ATS scans.
8. Order experience bullets by relevance to the JD - most relevant achievements first.
9. Use standard section headings only (ATS-safe): Summary, Skills, Work Experience, Projects, Education, Certifications, Achievements.
10. Keep everything plain text - no tables, symbols, graphics, or unusual formatting.
11. ONE-PAGE RULE (critical): the final resume MUST fit a single A4 page at 10.5pt. Budget strictly: summary max 3 sentences (~45 words); at most 5 skill groups with max 8 items each; 3-4 bullets for the most recent or most JD-relevant role and only 2 for older roles; at most 2 projects with max 2 bullets each; one line per education entry. If the source resume has more content than fits, keep only what is most relevant to this exact JD and drop the rest - never exceed the budget.
12. Quality bar: every bullet must follow "strong action verb + what was done + tools/JD keywords + quantified outcome". Ban filler phrases like "responsible for", "worked on", "team player", "hardworking".
13. For certifications: extract any certifications mentioned in the source resume. If none are present, return an empty array.
14. For achievements: extract any notable awards, recognitions, or accomplishments from the source resume. If none are present, return an empty array.

OUTPUT: Respond with ONLY a valid JSON object, no markdown fences, no commentary, in exactly this schema:
{
  "resume": {
    "name": "", "title": "", "email": "", "location": "",
    "phone_display": "", "phone_e164": "",
    "linkedin_url": "", "github_url": "", "website_url": "",
    "summary": "",
    "skills": [{"group": "", "items": [""]}],
    "experience": [{"company": "", "role": "", "start": "", "end": "", "location": "", "bullets": [""]}],
    "projects": [{"name": "", "tech": "", "url": "", "date": "", "bullets": [""]}],
    "education": [{"institution": "", "degree": "", "start": "", "end": "", "gpa": "", "location": ""}],
    "certifications": [{"name": "", "issuer": "", "date": "", "credential_id": "", "url": ""}],
    "achievements": [{"title": "", "description": ""}]
  },
  "keywords": ["the JD keywords you incorporated"],
  "missing_keywords": ["important JD keywords still absent because the candidate has no evidence for them - be honest"],
  "ats_score": 0,
  "ats_tips": ["3-5 short, specific suggestions the candidate should act on manually (e.g. certifications worth adding, gaps to address)"]
}
"ats_score" is an integer 0-100: the percentage of the JD's important keywords now present in the resume.
Copy contact details (name, email, phone, links) from the candidate's resume as-is; leave a field as an empty string if the source resume does not contain it."""

RESUME_REOPTIMIZE_SYSTEM_PROMPT = """You are an elite ATS resume optimizer. The candidate has already written and edited their resume themselves. Your job is ONLY to polish it for ATS keyword matching against a job description - you must NOT change their information.

STRICT PRESERVATION RULES:
1. Keep every job, project, education entry, certification, achievement, company name, role title, date, metric and factual claim EXACTLY as provided. Never add, remove or merge entries. Never invent anything.
2. You may rephrase the summary and bullet wording ONLY to: (a) insert the JD's exact keywords where the existing content already supports them, (b) strengthen action verbs, (c) fix grammar and tense (past tense for past roles, present for current), (d) remove filler phrases. The meaning and facts of each line must stay identical.
3. You may reorder bullets within a role and items within a skill group by relevance to the JD - nothing else moves.
4. You may add a JD keyword to the skills section ONLY if it is clearly evidenced elsewhere in the resume.
5. Keep it one A4 page: never lengthen the content; keep bullet counts the same or lower.
6. Where the JD uses an acronym the resume already merits, include both forms once (e.g. "CI/CD (Continuous Integration/Continuous Delivery)").

OUTPUT: Respond with ONLY a valid JSON object, no markdown fences, no commentary, in exactly this schema:
{
  "resume": { same schema and same entries as the input resume, with polished wording. Schema: name, title, email, location, phone_display, phone_e164, linkedin_url, github_url, website_url, summary, skills, experience, projects, education, certifications, achievements },
  "keywords": ["JD keywords now present in the resume"],
  "missing_keywords": ["important JD keywords still absent because the candidate has no evidence for them - be honest"],
  "ats_score": 0,
  "ats_tips": ["3-5 short, specific, actionable suggestions"]
}
"ats_score" is an integer 0-100: the percentage of the JD's important keywords now present in the resume."""

RESUME_KEYWORD_SUGGEST_PROMPT = """You are an expert ATS (Applicant Tracking System) keyword analyst. Your job is to analyze a candidate's existing resume against a specific job description and provide keyword matching insights — WITHOUT rewriting or modifying the phrasing or meaning of the resume in any way.

RULES:
1. Do NOT rewrite or rephrase any wording to tailor it to the job description. The candidate's original text, phrasing, roles, experience, bullet points, skills, certifications, and achievements must be preserved exactly as written.
2. If given a plain text resume, parse and convert it into the structured JSON schema below, mapping the text into the correct fields with NO rewriting.
3. Extract the most important hard skills, tools, technologies, certifications, and soft skills from the JOB DESCRIPTION.
4. Identify which of those JD keywords are already present in the candidate's resume (matched keywords).
5. Identify which important JD keywords are missing from the resume (missing keywords). Only list genuinely important ones for ATS — not every possible keyword.
6. Calculate an ATS score (0-100) representing the percentage of the JD's important keywords already found in the resume.
7. Provide 3-5 specific, actionable tips for the candidate to manually improve their ATS score (e.g., "Add 'machine learning' to your Skills section", "Mention 'Agile methodology' in your experience bullets").

OUTPUT: Respond with ONLY a valid JSON object, no markdown fences, no commentary:
{
  "resume": {
    "name": "", "title": "", "email": "", "location": "",
    "phone_display": "", "phone_e164": "",
    "linkedin_url": "", "github_url": "", "website_url": "",
    "summary": "",
    "skills": [{"group": "", "items": [""]}],
    "experience": [{"company": "", "role": "", "start": "", "end": "", "location": "", "bullets": [""]}],
    "projects": [{"name": "", "tech": "", "url": "", "date": "", "bullets": [""]}],
    "education": [{"institution": "", "degree": "", "start": "", "end": "", "gpa": "", "location": ""}],
    "certifications": [{"name": "", "issuer": "", "date": "", "credential_id": "", "url": ""}],
    "achievements": [{"title": "", "description": ""}]
  },
  "keywords": ["JD keywords already present in the resume"],
  "missing_keywords": ["important JD keywords missing from the resume"],
  "ats_score": 0,
  "ats_tips": ["3-5 specific, actionable suggestions for the candidate to manually add keywords"]
}
"ats_score" is an integer 0-100. If given a JSON resume object as input, return it EXACTLY unchanged in the "resume" field."""

@app.route('/api/resume/ai-tailor', methods=['POST'])
@login_required
def resume_ai_tailor():
    """AI-tailor the user's resume to a job description (Groq)."""
    user = db.session.get(User, session['user_id'])
    is_admin = bool(user and user.is_admin) or session.get('is_admin', False)
    if not (is_admin or session.get('resume_unlocked', False)):
        return jsonify({'status': 'error', 'message': 'Please unlock the Resume Builder first.'}), 403

    data = request.json or {}
    mode = data.get('mode', 'tailor')
    job_description = (data.get('job_description') or '').strip()[:8000]
    target_tmpl = (data.get('target_template') or '').strip()[:50]

    if mode == 'suggest_only':
        # Keyword analysis only — never rewrites the resume
        resume_json_in = data.get('resume_json')
        old_resume = (data.get('old_resume') or '').strip()[:12000]

        if not job_description:
            return jsonify({'status': 'error', 'message': 'Please provide the job description.'}), 400

        system_prompt = RESUME_KEYWORD_SUGGEST_PROMPT

        if isinstance(resume_json_in, dict):
            user_prompt = (
                "CANDIDATE'S RESUME JSON (return this EXACTLY as-is in the 'resume' field — completely unmodified):\n" +
                json.dumps(resume_json_in)[:14000] +
                "\n\nTARGET JOB DESCRIPTION:\n" + job_description
            )
        elif old_resume:
            user_prompt = (
                "CANDIDATE'S RESUME (text format — parse this exactly as-is into the 'resume' JSON schema, preserving all candidates phrasing and details unmodified):\n" +
                old_resume +
                "\n\nTARGET JOB DESCRIPTION:\n" + job_description
            )
        else:
            return jsonify({'status': 'error', 'message': 'Please provide your resume and the job description.'}), 400

    elif mode == 'reoptimize':
        resume_json_in = data.get('resume_json')
        if not isinstance(resume_json_in, dict) or not job_description:
            return jsonify({'status': 'error', 'message': 'Please provide the job description (your resume data is taken from the builder).'}), 400

        system_prompt = RESUME_REOPTIMIZE_SYSTEM_PROMPT
        if target_tmpl:
            system_prompt += f"\n\nTEMPLATE DESIGN TARGET: Tailor the layout and content length to look best in the '{target_tmpl}' template style."

        user_prompt = (
            "CANDIDATE'S CURRENT RESUME (JSON, preserve all entries and facts):\n" +
            json.dumps(resume_json_in)[:14000] +
            "\n\nTARGET JOB DESCRIPTION:\n" + job_description
        )
    else:
        # Default: full AI tailor (rewrite)
        old_resume = (data.get('old_resume') or '').strip()[:12000]
        if not old_resume or not job_description:
            return jsonify({'status': 'error', 'message': 'Please provide both your current resume and the job description.'}), 400

        system_prompt = RESUME_TAILOR_SYSTEM_PROMPT
        if target_tmpl:
            system_prompt += f"\n\nTEMPLATE DESIGN TARGET: Tailor the layout and content length to look best in the '{target_tmpl}' template style."

        user_prompt = (
            "CANDIDATE'S CURRENT RESUME:\n" + old_resume +
            "\n\nTARGET JOB DESCRIPTION:\n" + job_description
        )

    api_key = os.environ.get('GROQ_API_KEY')
    if not api_key:
        return jsonify({'status': 'error', 'message': 'AI service is currently unavailable.'}), 500

    try:
        client = Groq(api_key=api_key)
        raw = None
        last_err = None
        for model in ("qwen/qwen3-32b", "llama-3.3-70b-versatile", "llama-3.1-8b-instant"):
            try:
                completion = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.4,
                    max_tokens=4000,
                )
                raw = completion.choices[0].message.content
                break
            except Exception as model_err:
                last_err = model_err
                continue
        if raw is None:
            raise last_err or RuntimeError("No model available")

        # Reasoning models (qwen3) may emit <think> blocks - strip them
        raw = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL)

        # Extract the JSON object even if the model added stray text
        start, end = raw.find('{'), raw.rfind('}')
        if start == -1 or end == -1:
            raise ValueError("Model returned no JSON")
        parsed = json.loads(raw[start:end + 1])

        resume_json = parsed.get('resume') or {}
        # Shape guards so the editor never receives broken data
        for key in ('skills', 'experience', 'projects', 'education', 'languages'):
            if not isinstance(resume_json.get(key), list):
                resume_json[key] = []
        if not isinstance(resume_json.get('headings'), dict):
            resume_json['headings'] = {
                'summary': 'Summary', 'skills': 'Skills',
                'experience': 'Work Experience', 'projects': 'Projects',
                'education': 'Education', 'languages': 'Languages'
            }

        keywords = parsed.get('keywords') if isinstance(parsed.get('keywords'), list) else []
        missing = parsed.get('missing_keywords') if isinstance(parsed.get('missing_keywords'), list) else []
        ats_tips = parsed.get('ats_tips') if isinstance(parsed.get('ats_tips'), list) else []
        try:
            ats_score = max(0, min(100, int(parsed.get('ats_score'))))
        except (TypeError, ValueError):
            ats_score = None
        return jsonify({'status': 'success', 'resume': resume_json,
                        'keywords': keywords, 'missing_keywords': missing,
                        'ats_score': ats_score, 'ats_tips': ats_tips})
    except Exception as e:
        logger.error(f"AI tailor error: {e}")
        return jsonify({'status': 'error', 'message': 'AI tailoring failed. Please try again in a moment.'}), 500





@app.route('/api/resume/create-order', methods=['POST'])
def resume_create_order():
    """Create a Razorpay order for the resume builder."""
    razorpay_key_id = os.environ.get('RAZORPAY_KEY_ID')
    razorpay_key_secret = os.environ.get('RAZORPAY_KEY_SECRET')
    
    if razorpay is None or not razorpay_key_id or not razorpay_key_secret:
        return jsonify({'status': 'error', 'message': 'Razorpay credentials not configured.'}), 500

    try:
        client = razorpay.Client(auth=(razorpay_key_id, razorpay_key_secret))

        # 9900 paise = ₹99
        amount = 9900
        currency = "INR"
        receipt = "resume_unlock"
        
        order = client.order.create({
            "amount": amount,
            "currency": currency,
            "receipt": receipt
        })
        
        return jsonify({
            'status': 'success',
            'order_id': order['id'],
            'amount': amount,
            'currency': currency,
            'key_id': razorpay_key_id
        })
    except Exception as e:
        logger.error(f"Error creating Razorpay order: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to create payment order.'}), 500


@app.route('/api/resume/verify-payment', methods=['POST'])
def resume_verify_payment():
    """Verify a Razorpay payment signature to unlock the resume builder."""
    data = request.json or {}
    
    razorpay_payment_id = data.get('razorpay_payment_id', '')
    razorpay_order_id = data.get('razorpay_order_id', '')
    razorpay_signature = data.get('razorpay_signature', '')
    
    if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature]):
        return jsonify({'status': 'error', 'message': 'Missing payment verification details.'}), 400
    
    razorpay_key_id = os.environ.get('RAZORPAY_KEY_ID')
    razorpay_key_secret = os.environ.get('RAZORPAY_KEY_SECRET')
    
    if razorpay is None or not razorpay_key_id or not razorpay_key_secret:
        return jsonify({'status': 'error', 'message': 'Razorpay credentials not configured.'}), 500

    try:
        client = razorpay.Client(auth=(razorpay_key_id, razorpay_key_secret))

        # Verify the signature
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }
        
        # This will raise a SignatureVerificationError if verification fails
        client.utility.verify_payment_signature(params_dict)
        
        # Signature is valid, unlock the resume builder
        session['resume_unlocked'] = True
        logger.info(f"Resume unlocked via payment: {razorpay_payment_id}")
        return jsonify({'status': 'success', 'message': 'Payment verified. Resume builder unlocked!'})
        
    except razorpay.errors.SignatureVerificationError:
        logger.warning(f"Invalid payment signature for order {razorpay_order_id}")
        return jsonify({'status': 'error', 'message': 'Invalid payment signature.'}), 400
    except Exception as e:
        logger.error(f"Razorpay verification error: {e}")
        return jsonify({'status': 'error', 'message': 'Verification service error. Please try again.'}), 500

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        # Handle login
        if 'admin_password' in request.form:
            if request.form.get('admin_password') == 'admin123':
                session['is_admin'] = True
                flash('Logged in successfully.', 'success')
            else:
                flash('Incorrect password.', 'error')
            return redirect(url_for('admin'))
            
        # Handle logout
        if request.form.get('action') == 'logout':
            session.pop('is_admin', None)
            flash('Logged out.', 'success')
            return redirect(url_for('admin'))

        # Check authentication for CRUD actions
        if not session.get('is_admin'):
            flash('Please log in first.', 'error')
            return redirect(url_for('admin'))

        action = request.form.get('action')
        
        # Handle file upload if present
        def get_banner_url():
            icon_url = request.form.get('icon', '')
            if 'banner_file' in request.files:
                file = request.files['banner_file']
                if file.filename != '':
                    filename = secure_filename(file.filename)
                    # Add timestamp to make filename unique
                    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    return f"/static/uploads/{filename}"
            return icon_url

        if action == 'add':
            new_course = Course(
                title=request.form.get('title'),
                description=request.form.get('description'),
                icon=get_banner_url(),
                link=request.form.get('link'),
                program_type=request.form.get('program_type')
            )
            db.session.add(new_course)
            db.session.commit()
            flash('Item added successfully.', 'success')
        elif action == 'edit':
            course_id = request.form.get('course_id')
            course = db.session.get(Course, course_id)
            if course:
                course.title = request.form.get('title')
                course.description = request.form.get('description')
                
                # Only update icon if a new one was provided (either text or file)
                new_banner = get_banner_url()
                if new_banner or 'banner_file' in request.files:
                    course.icon = new_banner
                    
                course.link = request.form.get('link')
                course.program_type = request.form.get('program_type')
                db.session.commit()
                flash('Item updated successfully.', 'success')
        elif action == 'delete':
            course_id = request.form.get('course_id')
            course = db.session.get(Course, course_id)
            if course:
                db.session.delete(course)
                db.session.commit()
                flash('Item deleted successfully.', 'success')
        return redirect(url_for('admin'))
        
    if not session.get('is_admin'):
        return render_template('admin_login.html')
        
    courses = Course.query.all()
    return render_template('admin_dashboard.html', courses=courses)






@app.route('/api/test', methods=['GET'])
def test_api():
    return jsonify({'status': 'success', 'message': 'API is working!'})


@app.route('/api/contact', methods=['POST'])
def contact():
    data = request.json
    try:
        new_contact = ContactSubmission(
            name=data.get('name'), 
            email=data.get('email'), 
            message=data.get('message')
        )
        db.session.add(new_contact)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Message sent successfully!'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500



@app.route('/api/build', methods=['POST'])
def build_request():
    data = request.json
    try:
        project = ProjectRequest(
            company_name=data['company_name'],
            email=data['email'],
            product_type=data['product_type'],
            description=data['description']
        )
        db.session.add(project)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Request submitted successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/stacklabs-register', methods=['POST'])
def stacklabs_register():
    data = request.json
    try:
        registration = StackLabsRegistration(
            name=data['name'],
            email=data['email'],
            phone=data['phone'],
            year_of_study=data['year_of_study'],
            college=data['college'],
            batch=data['batch'],
            fee=data['fee']
        )
        db.session.add(registration)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Registration submitted successfully', 'registration_id': registration.id})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/stacklabs-payment', methods=['POST'])
def stacklabs_payment():
    data = request.json
    try:
        registration = db.session.get(StackLabsRegistration, data['registration_id'])
        if registration:
            registration.transaction_id = data['transaction_id']
            registration.payment_status = 'paid'
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Payment confirmed successfully'})
        else:
            return jsonify({'status': 'error', 'message': 'Registration not found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500




# Chatbot Integration
def load_website_context():
    try:
        with open('website_context.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading website context: {e}")
        return []

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message')
    
    if not user_message:
        return jsonify({'status': 'error', 'message': 'No message provided'}), 400
        
    api_key = os.environ.get('GROQ_API_KEY')
    if not api_key:
        return jsonify({
            'status': 'error', 
            'message': 'Chatbot is currently unavailable. (API Key missing)'
        }), 500
        
    try:
        client = Groq(api_key=api_key)
        context = load_website_context()
        
        # URL Mapping for navigation
        url_map = {
            'index.html': '/',
            'stackup.html': '/stackup',
            'stacklabs.html': '/stacklabs',
            'stackbuild.html': '/stackbuild',
            'stackbuild/index.html': '/stackbuild',
            'clients.html': '/stackbuild/clients',
            'signup.html': '/signup',
            'login.html': '/login',
            'admin_dashboard.html': '/admin',
            'new_notification.html': '/new-notification'
        }
        
        # Format context for the prompt
        context_str = "\n\n".join([f"Page: {c['file']} (URL: {url_map.get(c['file'], '#')})\nContent: {c['content']}" for c in context])
        
        system_prompt = f"""
You are Stack AI. Your goal is to help users with information about Stack Education, Master industry skills, StackLabs (Internships), and StackBuild (Products).

Use the following website context to answer user questions. 
If the information is not in the context, politely say you don't know and suggest they contact the team.
Keep your answers concise, professional, and helpful.

NAVIGATION:
If a user asks about a specific program or page, provide the relevant URL from the context. 
Always format links like this: [Page Name](URL)
For example: "You can find our courses on the [StackUp](/stackup) page."

CONTEXT:
{context_str}
"""

        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=500,
        )
        
        response_text = completion.choices[0].message.content
        return jsonify({'status': 'success', 'response': response_text})
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({'status': 'error', 'message': f'Failed to process your request: {str(e)}'}), 500

# For Vercel, the 'app' object is automatically detected. 
# Database initialization is handled by the @app.before_request hook.

if __name__ == '__main__':
    print("Starting Flask app on port 5001...")
    print("Admin Dashboard available at http://127.0.0.1:5001/admin")
    app.run(debug=True, port=5001)
