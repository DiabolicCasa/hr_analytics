from flask import Flask, render_template, request, redirect, url_for,jsonify
from pymongo import MongoClient
from datetime import datetime, timedelta
import json
import calendar

from bson.objectid import ObjectId
from werkzeug.utils import secure_filename
import PyPDF2
import docx
from pyresparser import ResumeParser
import os

app = Flask(__name__)


# Set up MongoDB connection 
client = MongoClient('mongodb://localhost:27017/') 
db = client['HR'] 
jobs_collection = db['jobs']
interviews = db['interviews']
applications_collection = db['applicants']


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/applicants')
def applicants():
    applicants_list = list(applications_collection.find()) 
    vacancies = list(jobs_collection.find({'open': True}))
    vacancy_dict = {vacancy['_id']: vacancy['title'] for vacancy in vacancies}

    return render_template('applicants.html',vacancies=vacancies,applicants_list=applicants_list,vacancy_dict=vacancy_dict)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

import warnings
warnings.filterwarnings("ignore", category=UserWarning)

@app.route('/parse_resume', methods=['POST'])
def parse_resume():
    if 'resume' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['resume']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Parse the resume using pyresparser
        data = ResumeParser(filepath).get_extracted_data()
        
        parsed_data = {
            'name': data.get('name', ''),
            'email': data.get('email', ''),
            'mobile_number': data.get('mobile_number', ''),
            'skills': data.get('skills', []),
            'college_name': data.get('college_name', []),
            'degree': data.get('degree', []),
            'designation': data.get('designation', []),
            'company_names': data.get('company_names', []),
            'total_experience': data.get('total_experience', 0),
            'no_of_pages': data.get('no_of_pages', 0)
        }
        
        # Clean up the uploaded file
        os.remove(filepath)
        
        return jsonify(parsed_data)

from bson import ObjectId

@app.route('/add_applicant', methods=['POST'])
def add_applicant():
    # Get form data
    name = request.form.get('name')
    email = request.form.get('email')
    mobile = request.form.get('mobile')
    skills = request.form.get('skills').split(',')
    experience = request.form.get('experience')
    job_id = request.form.get('job_id')

    # Create applicant document
    applicant = {
        'name': name,
        'email': email,
        'mobile': mobile,
        'skills': skills,
        'experience': experience,
        'date' : datetime.now(),
        'job_id': ObjectId(job_id)  # Convert string to ObjectId
    }

    # Insert into database
    result = applications_collection.insert_one(applicant)

    if result.inserted_id:
        return jsonify({'success': True, 'message': 'Applicant added successfully'}), 200
    else:
        return jsonify({'success': False, 'message': 'Failed to add applicant'}), 500
    

@app.route('/add_job', methods=['POST'])
def add_job():
    rubrics = json.loads(request.form['rubricsArray'])
    job = {
        'title': request.form['title'],
        'company': request.form['company'],
        'location': request.form['location'],
        'rubrics': rubrics,
        'open' : True
    }
    jobs_collection.insert_one(job)
    return redirect(url_for('jobs'))

@app.route('/edit_job/<job_id>', methods=['POST'])
def edit_job(job_id):
    rubrics = json.loads(request.form['rubricsArray'])
    jobs_collection.update_one(
        {'_id': ObjectId(job_id)},
        {'$set': {
            'title': request.form['title'],
            'company': request.form['company'],
            'location': request.form['location'],
            'rubrics': rubrics
        }}
    )
    return redirect(url_for('jobs'))

@app.route('/close_job/<job_id>')
def close_job(job_id):
    job = jobs_collection.find_one({'_id': ObjectId(job_id)})
    
    if job:
        current_status = job.get('open', False)
        new_status = not current_status
        
        jobs_collection.update_one(
            {'_id': ObjectId(job_id)},
            {'$set': {
                'open': new_status
            }}
        )
        print(f"Job {job_id} status changed to {'open' if new_status else 'closed'}")
    
    return redirect(url_for('jobs'))


@app.route('/delete_job/<job_id>')
def delete_job(job_id):
    # Your delete logic here
    jobs_collection.delete_one({'_id': ObjectId(job_id)})
    return redirect(url_for('jobs'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/jobs')
def jobs():
    open_jobs = list(jobs_collection.find({'open': True}))
    closed_jobs = list(jobs_collection.find({'open': False}))
    return render_template('jobs.html', open_jobs=open_jobs, closed_jobs=closed_jobs)

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/calendar')
def calendar_view():
    year = int(request.args.get('year', datetime.now().year))
    month = int(request.args.get('month', datetime.now().month))
    
    # Create a calendar for the specified month
    cal = calendar.monthcalendar(year, month)
    
    # Get all interviews for the month
    start_date = datetime(year, month, 1)
    end_date = start_date + timedelta(days=31)
    end_date = end_date.replace(day=1)  # First day of next month
    
    scheduled_interviews = list(interviews.find({
        'date': {'$gte': start_date, '$lt': end_date}
    }))
    
    return render_template('calendar.html', year=year, month=month, calendar=cal, 
                           interviews=scheduled_interviews, 
                           month_name=calendar.month_name[month],
                           today=datetime.now())

@app.route('/schedule', methods=['POST'])
def schedule_interview():
    date = request.form['date']
    time = request.form['time']
    name = request.form['name']
    
    interview_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    
    interviews.insert_one({
        'date': interview_datetime,
        'name': name
    })
    
    return redirect(url_for('calendar_view'))

@app.route('/get_interviews', methods=['GET'])
def get_interviews():
    date = request.args.get('date')
    date_obj = datetime.strptime(date, "%Y-%m-%d")
    
    day_interviews = list(interviews.find({
        'date': {
            '$gte': date_obj,
            '$lt': date_obj + timedelta(days=1)
        }
    }))
    
    return jsonify([{
        'id': str(interview['_id']),
        'time': interview['date'].strftime('%H:%M'),
        'name': interview['name']
    } for interview in day_interviews])

@app.route('/delete_interview/<interview_id>', methods=['DELETE'])
def delete_interview(interview_id):
    result = interviews.delete_one({'_id': ObjectId(interview_id)})
    if result.deleted_count > 0:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False}), 404


if __name__ == '__main__':
    app.run(debug=True)