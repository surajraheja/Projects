import cv2
import os
import numpy as np
from deepface import DeepFace
import pandas as pd
import matplotlib.pyplot as plt

# Function to recursively count all images in the dataset directory
def count_images_in_directory(directory):
    count = 0
    for root, dirs, files in os.walk(directory):
        count += len([file for file in files if file.lower().endswith(('png', 'jpg', 'jpeg'))])
    return count

# Function to get the person's name from the image path
def get_person_name(image_path):
    return os.path.basename(os.path.dirname(image_path))

# File paths
test_img_folder = r'C:\Users\Lenovo\Desktop\testing data\group pic t'
dataset_path = r'C:\Users\Lenovo\Desktop\training data'

# Find all test images in the test folder
test_images = [os.path.join(test_img_folder, file) for file in os.listdir(test_img_folder) if file.lower().endswith(('png', 'jpg', 'jpeg'))]

# Total number of images compared
total_images_compared = count_images_in_directory(dataset_path)
print(f'Total number of images compared: {total_images_compared}')

# Process each test image
for test_img in test_images:
    print(f'Processing test image: {test_img}')
    
    # Detect and extract faces from the test image
    detected_faces = DeepFace.extract_faces(img_path=test_img, enforce_detection=False)
    
    # Read the test image
    test_image = cv2.imread(test_img)
    test_image_rgb = cv2.cvtColor(test_image, cv2.COLOR_BGR2RGB)

    # Display the test image
    plt.figure(figsize=(15, 10))
    plt.subplot(1, len(detected_faces) + 1, 1)
    plt.imshow(test_image_rgb)
    plt.title('Test Image')
    plt.axis('off')

    match_found = False  # Flag to check if any match is found
    
    # Process each detected face
    for i, face in enumerate(detected_faces):
        face_img = face["face"]
        
        # Convert face image to uint8 format if necessary
        if face_img.dtype != np.uint8:
            face_img = (face_img * 255).astype(np.uint8)
            
        face_img_path = f'face_{i}.jpg'
        cv2.imwrite(face_img_path, face_img)

        # Find the matching images using DeepFace
        results = DeepFace.find(img_path=face_img_path, db_path=dataset_path, model_name='Facenet', enforce_detection=False)

        # If results is a list, get the first DataFrame
        if isinstance(results, list):
            result = results[0]
        else:
            result = results

        # Number of matching images
        number_of_matches = len(result)
        print(f'Number of images matched: {number_of_matches}')

        # Get the path of the most matching image
        if not result.empty:
            most_matching_img_path = result.loc[0, 'identity']
            person_name = get_person_name(most_matching_img_path)
            
            print(f'The detected face matches with: {person_name}')
            
            # Read the most matching image
            matching_image = cv2.imread(most_matching_img_path)
            matching_image_rgb = cv2.cvtColor(matching_image, cv2.COLOR_BGR2RGB)

            # Display the detected face and the most matching image
            plt.figure(figsize=(10, 5))
            plt.subplot(1, 2, 1)
            plt.imshow(cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB))
            plt.title(f'Detected Face {i+1}')
            plt.axis('off')
            
            plt.subplot(1, 2, 2)
            plt.imshow(matching_image_rgb)
            plt.title(f'Most Matching Image\n({person_name})')
            plt.axis('off')
            
            plt.show()
            
            match_found = True  # Set flag to True if a match is found

    if not match_found:
        print("No matching images found.")