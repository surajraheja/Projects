import os
import cv2
import numpy as np
from deepface import DeepFace
import matplotlib.pyplot as plt
import psycopg2
from psycopg2 import sql
import random
from datetime import datetime, time, timedelta
import re

# Function to recursively count all images in the dataset directory
def count_images_in_directory(directory):
    count = 0
    for root, dirs, files in os.walk(directory):
        count += len([file for file in files if file.lower().endswith(('png', 'jpg', 'jpeg'))])
    return count

# Database connection function
def connect_to_db():
    return psycopg2.connect(
        dbname="Automated Reporting System",
        user="postgres",
        password="Nancy@2017",
        host="localhost",
        port="5432"
    )

# Attendance record insertion function
def insert_attendance(conn, date, student_id, subject_id, image_path):
    try:
        with conn.cursor() as cur:
            query = sql.SQL("""
                INSERT INTO attendance (date, student_id, subject_id, image)
                VALUES (%s, %s, %s, %s)
            """)
            cur.execute(query, (date, student_id, subject_id, image_path))
        conn.commit()
        print(f"Inserted attendance for student {student_id} in subject {subject_id} on {date}")
    except (Exception, psycopg2.Error) as error:
        conn.rollback()
        print("Error inserting attendance:", error)

# Time slot generation function
def get_subject_by_time(class_time):
    subjects = {
        (time(9, 0), time(10, 0)): "Maths",
        (time(10, 0), time(11, 0)): "Artificial Intelligence",
        (time(11, 0), time(12, 0)): "Machine Learning",
        (time(12, 0), time(13, 0)): "Cloud Computing",
        (time(14, 0), time(15, 0)): "DBMS",
        (time(15, 0), time(16, 0)): "AWS",
        (time(16, 0), time(17, 0)): "DSA",
        (time(17, 0), time(18, 0)): "WEB D",
    }
    
    for (start_time, end_time), subject in subjects.items():
        if start_time <= class_time < end_time:
            return subject
    
    return None  # Return None if no matching time slot is found

# Faculty retrieval or insertion function
def retrieve_or_insert_faculty(conn, faculty_name):
    faculty_ids = {
        "Ram": 12340,
        "Sita": 23450,
        "Narayan": 34560,
        "Suresh": 45670,
        "Geeta": 56780,
        "Mahesh": 67890,
        "Shiv": 78900,
        "Krishna": 89010
    }

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM Faculty WHERE name = %s", (faculty_name,))
            faculty_row = cur.fetchone()
            if faculty_row:
                return faculty_row[0]
            else:
                faculty_id = faculty_ids.get(faculty_name, random.randint(10, 999))
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

# Faculty names assignment
faculty_names = {
    "Maths": "Ram",
    "Artificial Intelligence": "Sita",
    "Machine Learning": "Narayan",
    "Cloud Computing": "Suresh",
    "DBMS": "Geeta",
    "AWS": "Mahesh",
    "DSA": "Shiv",
    "WEB D": "Krishna",
}

# Subject retrieval or insertion function
def retrieve_or_insert_subject(conn, class_time, available_time_slots, subject_name):
    subject_ids = {
        "Maths": 1122330,
        "Artificial Intelligence": 2233440,
        "Machine Learning": 3344550,
        "Cloud Computing": 4455660,
        "DBMS": 5566770,
        "AWS": 6677880,
        "DSA": 7788990,
        "WEB D": 8899110
    }

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, from_time, to_time, faculty_id FROM Subject WHERE name = %s", (subject_name,))
            subject_row = cur.fetchone()
            if subject_row:
                return subject_row[0], (subject_row[1], subject_row[2]), subject_row[3]
            else:
                # Find the appropriate time slot
                chosen_slot = None
                for slot in available_time_slots:
                    if slot[0] <= class_time < slot[1]:
                        chosen_slot = slot
                        break

                if not chosen_slot:
                    print(f"No available time slot for {class_time}")
                    return None, None, None

                faculty_name = faculty_names.get(subject_name, f"Prof. {subject_name}")
                faculty_id = retrieve_or_insert_faculty(conn, faculty_name)
                if not faculty_id:
                    return None, None, None

                subject_id = subject_ids.get(subject_name, random.randint(1000, 9999))
                query = sql.SQL("""
                    INSERT INTO Subject (id, name, from_time, to_time, faculty_id)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """)
                cur.execute(query, (subject_id, subject_name, chosen_slot[0], chosen_slot[1], faculty_id))
                subject_id = cur.fetchone()[0]
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
                cv2.putText(img, recognized_name, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36,255,12), 2)
        
        return img, recognized_persons
    except Exception as e:
        print(f"Error recognizing faces: {e}")
        return None, []

# Generate available time slots function
def generate_time_slots():
    start_time = time(9, 0)
    end_time = time(18, 0)
    time_slots = []
    
    current_time = start_time
    while current_time < end_time:
        slot_end_time = (datetime.combine(datetime.today(), current_time) + timedelta(hours=1)).time()
        time_slots.append((current_time, slot_end_time))
        current_time = slot_end_time
    
    return time_slots

# Timestamp extraction function
def extract_timestamp(image_path):
    filename = os.path.basename(image_path)
    # Extract timestamp part using regex
    match = re.search(r'\d{14}', filename)
    if match:
        timestamp_str = match.group(0)
        # Assuming the format 'YYYYMMDDHHMMSS'
        timestamp = datetime.strptime(timestamp_str, '%Y%m%d%H%M%S')
        return timestamp
    else:
        raise ValueError(f"Timestamp not found in filename: {filename}")

# Main script logic
def main():
    # Connect to the database
    conn = connect_to_db()
    
    dataset_directory = "C:/Users/Lenovo/Desktop/training data"
    if not os.path.exists(dataset_directory):
        print(f"Dataset directory '{dataset_directory}' does not exist.")
        return

    num_images = count_images_in_directory(dataset_directory)
    print("Number of images in the dataset:", num_images)
    
    # Define your training directory path for DeepFace
    training_dir = dataset_directory
    
    image_directory = "C:/Users/Lenovo/Desktop/testing data"
    output_directory = "C:/Users/Lenovo/Desktop/testing data"   
    
    if not os.path.exists(image_directory):
        print(f"Image directory '{image_directory}' does not exist.")
        return
    
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    
    available_time_slots = generate_time_slots()
    
    # Process each image in the test directory
    for image_name in os.listdir(image_directory):
        image_path = os.path.join(image_directory, image_name)
        if image_path.lower().endswith(('png', 'jpg', 'jpeg')):
            timestamp = extract_timestamp(image_path)
            class_time = timestamp.time()
            subject_name = get_subject_by_time(class_time)
            if not subject_name:
                print(f"No subject found for image {image_name} at time {class_time}")
                continue
            
            subject_id, chosen_slot, faculty_id = retrieve_or_insert_subject(conn, class_time, available_time_slots, subject_name)
            if not subject_id:
                print(f"Could not retrieve or insert subject for image {image_name}")
                continue
            
            result_img, recognized_persons = recognize_faces(image_path, training_dir)
            if result_img is not None:
                output_image_path = os.path.join(output_directory, f"{os.path.splitext(image_name)[0]}_result.jpg")
                plt.imsave(output_image_path, result_img)
            
            for person_name in recognized_persons:
                student_id = insert_or_retrieve_student(conn, person_name)
                if student_id:
                    insert_attendance(conn, timestamp.date(), student_id, subject_id, output_image_path)
    
    conn.close()

if __name__ == "__main__":
    main()
