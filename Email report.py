import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import psycopg2
import os

# SMTP configuration details
SMTP_HOST = 'smtp.office365.com'
SMTP_PORT = 587
SMTP_EMAIL = 'support@aptpath.in'
SMTP_PASSWORD = 'btpdcnfkgjyzdndh'  # Ensure this is stored securely

# Function to connect to the PostgreSQL database
def connect_to_db():
    try:
        conn = psycopg2.connect(
            dbname="Automated Reporting System",
            user="postgres",
            password="Nancy@2017",
            host="localhost",
            port="5432"
        )
        print("Connected to the database")
        return conn
    except psycopg2.OperationalError as e:
        print(f"Unable to connect to the database: {e}")
        raise  # Re-raise the exception to terminate execution

# Function to generate attendance report as a CSV file and retrieve images for all faculties
def generate_attendance_report(conn, report_type='daily'):
    date_condition = "CURRENT_DATE" if report_type == 'daily' else "DATE_TRUNC('month', CURRENT_DATE)"
    query = f"""
        SELECT s.name AS student_name, sub.name AS subject_name, f.name AS faculty_name, f.email AS faculty_email, a.date, a.image
        FROM Attendance a
        JOIN Student s ON a.student_id = s.id
        JOIN Subject sub ON a.subject_id = sub.id
        JOIN Faculty f ON sub.faculty_id = f.id
        WHERE a.date = {date_condition}
    """
    try:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
    except psycopg2.Error as e:
        print(f"Error executing query: {e}")
        raise  # Re-raise the exception to terminate execution

    df = pd.DataFrame(rows, columns=columns)
    file_path = f"attendance_report_{report_type}.csv"
    df.drop(columns=['image']).to_csv(file_path, index=False)  # Exclude image column from CSV

    # Save only one image per subject
    image_files = []
    saved_subjects = set()
    for index, row in df.iterrows():
        subject_name = row['subject_name']
        if subject_name not in saved_subjects:
            image_data = row['image']
            if image_data:
                image_filename = f"attendance_image_{subject_name}_{report_type}.jpg"
                with open(image_filename, 'wb') as img_file:
                    img_file.write(image_data)
                image_files.append(image_filename)
                saved_subjects.add(subject_name)

    return file_path, image_files

# Function to send email with the report and images
def send_email(subject, body, to_email, attachment_path, image_paths):
    msg = MIMEMultipart()
    msg['From'] = SMTP_EMAIL
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    # Attach CSV report
    attachment = MIMEBase('application', 'octet-stream')
    with open(attachment_path, 'rb') as file:
        attachment.set_payload(file.read())
    encoders.encode_base64(attachment)
    attachment.add_header('Content-Disposition', f'attachment; filename={os.path.basename(attachment_path)}')
    msg.attach(attachment)

    # Attach images
    for image_path in image_paths:
        if os.path.exists(image_path):  # Check if the file exists
            image_attachment = MIMEBase('application', 'octet-stream')
            with open(image_path, 'rb') as img_file:
                image_attachment.set_payload(img_file.read())
            encoders.encode_base64(image_attachment)
            image_attachment.add_header('Content-Disposition', f'attachment; filename={os.path.basename(image_path)}')
            msg.attach(image_attachment)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.send_message(msg)
    
    print(f"Email sent successfully to {to_email}")

# Main function to generate and send reports
def main():
    try:
        conn = connect_to_db()

        # Generate attendance reports
        daily_report_path, daily_image_paths = generate_attendance_report(conn, report_type='daily')
        monthly_report_path, _ = generate_attendance_report(conn, report_type='monthly')

        # Set the faculty email to your email address
        faculty_emails = ['rahejasuraj69@gmail.com']  # Change this to include other faculty emails if needed

        # Send daily report with images to the specified email
        for faculty_email in faculty_emails:
            send_email(
                subject="Daily Attendance Report",
                body="Please find attached the daily attendance report and related images.",
                to_email=faculty_email,
                attachment_path=daily_report_path,
                image_paths=daily_image_paths
            )
            # Clean up image files
            for image_path in daily_image_paths:
                if os.path.exists(image_path):
                    os.remove(image_path)

        # Send monthly report without images to the specified email
        for faculty_email in faculty_emails:
            send_email(
                subject="Monthly Attendance Report",
                body="Please find attached the monthly attendance report.",
                to_email=faculty_email,
                attachment_path=monthly_report_path,
                image_paths=[]  # No images for the monthly report
            )

        conn.close()
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
