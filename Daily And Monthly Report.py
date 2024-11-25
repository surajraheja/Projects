import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import psycopg2
import os
from datetime import datetime
import schedule
import time

# SMTP configuration details
SMTP_HOST = 'smtp.office365.com'
SMTP_PORT = 587
SMTP_EMAIL = 'support@aptpath.in'
SMTP_PASSWORD = 'btpdcnfkgjyzdndh'  # Ensure this is stored securely

# Function to connect to the PostgreSQL database
def connect_to_db():
    return psycopg2.connect(
        dbname="Automated Reporting System",
        user="postgres",
        password="Nancy@2017",
        host="localhost",
        port="5432"
    )

# Function to generate daily attendance report as a CSV file
def generate_daily_report(conn):
    query = """
    SELECT DISTINCT sub.name AS subject_name, 
           STRING_AGG(s.name, ', ' ORDER BY s.name) AS present_students,
           array_agg(DISTINCT a.image) AS student_images
    FROM attendance a
    JOIN student s ON a.student_id = s.id
    JOIN subject sub ON a.subject_id = sub.id
    GROUP BY sub.name
    ORDER BY sub.name
    """
    df = pd.read_sql(query, conn)
    
    daily_file_path = "daily_attendance_report.csv"
    df[['subject_name', 'present_students']].to_csv(daily_file_path, index=False)
    return daily_file_path, df

# Function to generate monthly attendance report as a CSV file
def generate_monthly_report(conn):
    query = """
    WITH attendance_data AS (
        SELECT s.name AS student_name, 
               sub.name AS subject_name, 
               COUNT(DISTINCT a.date) AS present_count
        FROM student s
        CROSS JOIN subject sub
        LEFT JOIN attendance a ON s.id = a.student_id AND sub.id = a.subject_id
        GROUP BY s.name, sub.name
    ),
    total_classes AS (
        SELECT sub.name AS subject_name, 
               COUNT(DISTINCT a.date) AS total_classes
        FROM subject sub
        LEFT JOIN attendance a ON sub.id = a.subject_id
        GROUP BY sub.name
    )
    SELECT ad.student_name AS "Student Name",
           ad.subject_name AS "Subject",
           tc.total_classes AS "Total Classes",
           ad.present_count AS "Present",
           tc.total_classes - ad.present_count AS "Absent",
           CAST((ad.present_count::float / NULLIF(tc.total_classes, 0) * 100) AS DECIMAL(5,2)) AS "Attendance %"
    FROM attendance_data ad
    JOIN total_classes tc ON ad.subject_name = tc.subject_name
    ORDER BY ad.student_name, ad.subject_name
    """
    df = pd.read_sql(query, conn)
    monthly_file_path = "monthly_attendance_report.csv"
    df.to_csv(monthly_file_path, index=False)
    return monthly_file_path

# Function to get professor emails
def get_professor_emails(conn):
    query = """
    SELECT name, email
    FROM faculty
    """
    df = pd.read_sql(query, conn)
    return dict(zip(df.name, df.email))

# Modified function to send email with the report and images
def send_email(subject, body, to_email, cc_email, attachment_paths, image_paths, subject_image_map):
    msg = MIMEMultipart()
    msg['From'] = SMTP_EMAIL
    msg['To'] = to_email
    msg['Cc'] = cc_email
    msg['Subject'] = subject
    
    # Convert body to HTML format
    body = "<html><body><p>" + body.replace('\n', '<br>') + "</p></body></html>"
    msg.attach(MIMEText(body, 'html'))

    # Attach CSV reports
    for attachment_path in attachment_paths:
        attachment = MIMEBase('application', 'octet-stream')
        with open(attachment_path, 'rb') as file:
            attachment.set_payload(file.read())
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition', f'attachment; filename={os.path.basename(attachment_path)}')
        msg.attach(attachment)

    # Attach student images with renamed filenames
    for image_path in image_paths:
        try:
            with open(image_path.strip(), 'rb') as file:  # Strip any extra spaces in the filename
                image_attachment = MIMEBase('application', 'octet-stream')
                image_attachment.set_payload(file.read())
            encoders.encode_base64(image_attachment)
            
            original_filename = os.path.basename(image_path)
            file_extension = os.path.splitext(original_filename)[1]
            
            subject_name = subject_image_map.get(image_path, "Unknown_Subject")
            
            new_filename = f"{subject_name}_student{file_extension}"
            
            image_attachment.add_header('Content-Disposition', f'attachment; filename={new_filename}')
            msg.attach(image_attachment)
        except FileNotFoundError as e:
            print(f"Error attaching image {image_path}: {e}")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        recipients = [to_email]
        if cc_email:
            recipients.append(cc_email)
        server.sendmail(SMTP_EMAIL, recipients, msg.as_string())
    
    print(f"Email sent successfully to {to_email} with CC to {cc_email}")

# Function to generate and send reports
def generate_and_send_reports():
    conn = connect_to_db()

    # Generate daily attendance report
    daily_report_path, daily_data = generate_daily_report(conn)

    # Generate monthly attendance report
    monthly_report_path = generate_monthly_report(conn)

    # Get professor emails
    professor_emails = get_professor_emails(conn)

    print("Professor emails:", professor_emails)
    print("Subjects in attendance data:", daily_data['subject_name'].tolist())

    # Create a mapping of image paths to subject names
    subject_image_map = {}
    all_image_paths = []

    # Create email body for all subjects
    body = "Daily Attendance Report for All Subjects:\n\n"

    # Iterate through each subject
    for _, row in daily_data.iterrows():
        subject_name = row['subject_name']
        present_students = row['present_students']

        body += f"{subject_name}:\n"
        body += f"Students attended: {present_students}\n\n"

        for image_path in row['student_images']:
            subject_image_map[image_path] = subject_name
            all_image_paths.append(image_path)

    # Send a single email with all subjects' information
    send_email(
        subject="Daily Attendance Report - All Subjects",
        body=body,
        to_email='rahejasuraj69@gmail.com',  # Your email address
        cc_email=', '.join(professor_emails.values()),  # CC all professors
        attachment_paths=[daily_report_path, monthly_report_path],
        image_paths=all_image_paths,
        subject_image_map=subject_image_map
    )

    conn.close()

# Run the report generation immediately
generate_and_send_reports()

# Schedule the job to run daily at a specific time (e.g., 11:59 PM)
schedule.every().day.at("11:59").do(generate_and_send_reports)

# Run the scheduled jobs
while True:
    schedule.run_pending()
    time.sleep(60)  # Wait for 60 seconds before checking again
