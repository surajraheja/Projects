import os
import cv2
import numpy as np
from deepface import DeepFace
import matplotlib.pyplot as plt
import psycopg2
from psycopg2 import sql
import random
from datetime import datetime, time, timedelta

# Database connection function
def connect_to_db():
    return psycopg2.connect(
        dbname="Automated Reporting System",
        user="postgres",
        password="Nancy@2017",
        host="localhost",
        port="5432"
    )

# Function to read the image file as binary data
def read_image_as_binary(image_path):
    with open(image_path, 'rb') as file:
        binary_data = file.read()
    return binary_data

# Attendance record insertion function
def insert_attendance(conn, date, student_id, subject_id, image_path):
    try:
        with conn.cursor() as cur:
            query = sql.SQL("""
                INSERT INTO attendance (date, student_id, subject_id, image)
                VALUES (%s, %s, %s, %s)
            """)
            binary_image = read_image_as_binary(image_path)
            cur.execute(query, (date, student_id, subject_id, psycopg2.Binary(binary_image)))
        conn.commit()
        print(f"Inserted attendance for student {student_id} in subject {subject_id} on {date}")
    except (Exception, psycopg2.Error) as error:
        conn.rollback()
        print("Error inserting attendance:", error)

# Time slot generation function
def generate_time_slots():
    base_time = datetime.combine(datetime.today(), time(9, 0))
    end_time = datetime.combine(datetime.today(), time(22, 0))
    duration = timedelta(hours=1)
    break_start = datetime.combine(datetime.today(), time(13, 0))
    break_end = datetime.combine(datetime.today(), time(14, 0))
    time_slots = []

    current_time = base_time
    while current_time + duration <= end_time:
        next_time = current_time + duration
        if (current_time < break_start or current_time >= break_end) and \
           (next_time <= break_start or next_time > break_end):
            time_slots.append((current_time.time(), next_time.time()))
        current_time = next_time

    return time_slots

# Faculty retrieval or insertion function
def retrieve_or_insert_faculty(conn, faculty_name):
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM Faculty WHERE name = %s", (faculty_name,))
            faculty_row = cur.fetchone()
            if faculty_row:
                return faculty_row[0]
            else:
                faculty_id = random.randint(10, 999)
                faculty_email = f"{faculty_name.lower().replace(' ', '_')}@university.edu"
                query = sql.SQL("""
                    INSERT INTO Faculty (id, name, email)
                    VALUES (%s, %s, %s)
                """)
                cur.execute(query, (faculty_id, faculty_name, faculty_email))
                conn.commit()
                print(f"Inserted new faculty: {faculty_name} with id {faculty_id}")
                return faculty_id
    except (Exception, psycopg2.Error) as error:
        conn.rollback()
        print("Error with faculty data:", error)
        return None

# Subject retrieval or insertion function
def retrieve_or_insert_subject(conn, subject_name, available_time_slots):
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, from_time, to_time, faculty_id FROM Subject WHERE name = %s", (subject_name,))
            subject_row = cur.fetchone()
            if subject_row:
                return subject_row[0], (subject_row[1], subject_row[2]), subject_row[3]
            else:
                subject_id = random.randint(1000, 9999)
                
                if not available_time_slots:
                    print(f"No available time slots for {subject_name}")
                    return None, None, None

                # Choose the first available time slot
                chosen_slot = available_time_slots.pop(0)

                faculty_name = f"Prof. {subject_name.title()}"
                faculty_id = retrieve_or_insert_faculty(conn, faculty_name)
                if not faculty_id:
                    return None, None, None

                query = sql.SQL("""
                    INSERT INTO Subject (id, name, from_time, to_time, faculty_id)
                    VALUES (%s, %s, %s, %s, %s)
                """)
                cur.execute(query, (subject_id, subject_name, chosen_slot[0], chosen_slot[1], faculty_id))
                conn.commit()
                print(f"Inserted {subject_name} with time slot {chosen_slot[0]} - {chosen_slot[1]}")
                return subject_id, chosen_slot, faculty_id
    except (Exception, psycopg2.Error) as error:
        conn.rollback()
        print("Error with subject data:", error)
        return None, None, None

# Student retrieval or insertion function
def insert_or_retrieve_student(conn, student_name):
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM Student WHERE name = %s", (student_name,))
            student_row = cur.fetchone()
            if student_row:
                return student_row[0]
            else:
                student_id = random.randint(10000, 99999)
                query = sql.SQL("""
                    INSERT INTO Student (id, name, email)
                    VALUES (%s, %s, %s)
                """)
                cur.execute(query, (student_id, student_name, f"{student_name.lower().replace(' ', '_')}@student.edu"))
                conn.commit()
                print(f"Inserted new student: {student_name} with id {student_id}")
                return student_id
    except (Exception, psycopg2.Error) as error:
        conn.rollback()
        print("Error with student data:", error)
        return None

# Face recognition function
def recognize_faces(image_path, training_dir, model_name="VGG-Face", distance_metric="cosine"):
    try:
        faces = DeepFace.extract_faces(img_path=image_path, enforce_detection=False)
        img = cv2.imread(image_path)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        recognized_persons = []
        
        for face in faces:
            facial_area = face['facial_area']
            x, y, w, h = facial_area['x'], facial_area['y'], facial_area['w'], facial_area['h']
            face_img = img[y:y+h, x:x+w]
            
            result = DeepFace.find(img_path=face_img, db_path=training_dir, model_name=model_name,
                                   distance_metric=distance_metric, enforce_detection=False)
            
            if result and len(result[0]) > 0:
                recognized_path = result[0]['identity'][0]
                recognized_name = os.path.basename(os.path.dirname(recognized_path))
                recognized_persons.append(recognized_name)
                cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(img, recognized_name, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            else:
                cv2.rectangle(img, (x, y), (x+w, y+h), (0, 0, 255), 2)
                cv2.putText(img, "Unknown", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
        
        return img, recognized_persons
    except Exception as e:
        print(f"Error in face recognition: {str(e)}")
        return None, []

# Main execution
if __name__ == "__main__":
    training_dir = r'C:\Users\Lenovo\Desktop\training data'
    test_image_path = r'C:\Users\Lenovo\Desktop\testing data\Maths_20240628.jpeg'

    # Extract information from filename
    image_name = os.path.basename(test_image_path)
    subject_name, date_str = image_name.rsplit('_', 1)
    date_str = date_str.split('.')[0]  # Remove the file extension
    date = datetime.strptime(date_str, "%Y%m%d").date()

    print(f"Subject: {subject_name}, Date: {date}")

    # Recognize faces
    result_img, recognized_persons = recognize_faces(test_image_path, training_dir)

    if result_img is not None:
        # Display result
        plt.figure(figsize=(12, 8))
        plt.imshow(result_img)
        plt.axis('off')
        plt.title(f"Recognized Faces - {subject_name} {date}")
        plt.show()

        print(f"Students {', '.join(recognized_persons)} attended {subject_name} class on {date}")

        # Database operations
        try:
            conn = connect_to_db()
            
            # Generate all possible time slots
            all_time_slots = generate_time_slots()
            
            # Retrieve existing subjects and remove their time slots from available slots
            with conn.cursor() as cur:
                cur.execute("SELECT from_time, to_time FROM Subject")
                existing_slots = cur.fetchall()
                for slot in existing_slots:
                    if slot in all_time_slots:
                        all_time_slots.remove(slot)
            
            subject_id, time_slot, faculty_id = retrieve_or_insert_subject(conn, subject_name, all_time_slots)
            
            if subject_id:
                for student_name in recognized_persons:
                    student_id = insert_or_retrieve_student(conn, student_name)
                    if student_id:
                        insert_attendance(conn, date, student_id, subject_id, test_image_path)
            else:
                print(f"Could not insert or retrieve subject {subject_name}")
        except (Exception, psycopg2.Error) as error:
            print("Database error:", error)
        finally:
            if conn:
                conn.close()
                print("Database connection closed.")
    else:
        print("Face recognition failed.")