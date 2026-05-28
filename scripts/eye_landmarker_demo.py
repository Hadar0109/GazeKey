"""
Eye Tracking Test - MediaPipe Face Landmarker (EYES AND IRIS ONLY)

This script demonstrates precise eye and iris tracking using MediaPipe.
- Uses MediaPipe Face Landmarker (new API)
- Focuses ONLY on eye and iris landmarks
- Does NOT draw face, mouth, nose, or other landmarks
- Clean debug visualization for eye tracking

Eye landmark indices:
- Left eye: 33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246
- Right eye: 362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398
- Left iris: 468, 469, 470, 471, 472
- Right iris: 473, 474, 475, 476, 477

Usage: python test_eye_tracking.py
Press 'q' to quit
"""

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
import time

# Eye landmark indices
LEFT_EYE = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
RIGHT_EYE = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
LEFT_IRIS = [468, 469, 470, 471, 472]
RIGHT_IRIS = [473, 474, 475, 476, 477]

def main():
    print("=" * 70)
    print("Eye Tracking Test - MediaPipe Face Landmarker")
    print("=" * 70)
    
    # Step 1: Initialize Face Landmarker
    print("\n[1/4] Loading MediaPipe Face Landmarker model...")
    model_path = "models/face_landmarker.task"
    
    try:
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        landmarker = vision.FaceLandmarker.create_from_options(options)
        print("SUCCESS: Face Landmarker loaded")
        print(f"  Model: {model_path}")
        print("  Mode: VIDEO (optimized for real-time)")
    except Exception as e:
        print(f"ERROR: Could not load model: {e}")
        print(f"\nMake sure model file exists at: {model_path}")
        return
    
    # Step 2: Open camera
    print("\n[2/4] Opening camera...")
    try:
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("ERROR: Could not open camera!")
            landmarker.close()
            return
        
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        print("SUCCESS: Camera opened")
        print(f"  Resolution: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
    except Exception as e:
        print(f"ERROR opening camera: {e}")
        landmarker.close()
        return
    
    # Step 3: Eye tracking loop
    print("\n[3/4] Starting eye tracking...")
    print("  Focus: EYES AND IRIS ONLY")
    print("  Look at the camera")
    print("  Press 'q' to quit\n")
    
    frame_count = 0
    eyes_detected_count = 0
    iris_detected_count = 0
    start_time = time.time()
    
    while True:
        try:
            ret, frame = cap.read()
            
            if not ret:
                print("ERROR: Cannot read frame")
                break
            
            frame_count += 1
            frame_timestamp_ms = int((time.time() - start_time) * 1000)
        
            # Convert to MediaPipe Image
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            
            # Detect face landmarks
            detection_result = landmarker.detect_for_video(mp_image, frame_timestamp_ms)
        except Exception as e:
            print(f"ERROR in detection loop: {e}")
            import traceback
            traceback.print_exc()
            break
        
        h, w, _ = frame.shape
        
        if detection_result.face_landmarks:
            face_landmarks = detection_result.face_landmarks[0]
            
            eyes_detected = False
            iris_detected = False
            
            # Draw LEFT EYE contour
            left_eye_points = []
            for idx in LEFT_EYE:
                landmark = face_landmarks[idx]
                x = int(landmark.x * w)
                y = int(landmark.y * h)
                left_eye_points.append((x, y))
                cv2.circle(frame, (x, y), 1, (0, 255, 0), -1)  # Green
            
            if len(left_eye_points) > 0:
                left_eye_points = np.array(left_eye_points, dtype=np.int32)
                cv2.polylines(frame, [left_eye_points], True, (0, 255, 0), 1)
                eyes_detected = True
            
            # Draw RIGHT EYE contour
            right_eye_points = []
            for idx in RIGHT_EYE:
                landmark = face_landmarks[idx]
                x = int(landmark.x * w)
                y = int(landmark.y * h)
                right_eye_points.append((x, y))
                cv2.circle(frame, (x, y), 1, (0, 255, 0), -1)  # Green
            
            if len(right_eye_points) > 0:
                right_eye_points = np.array(right_eye_points, dtype=np.int32)
                cv2.polylines(frame, [right_eye_points], True, (0, 255, 0), 1)
            
            # Draw LEFT IRIS
            left_iris_points = []
            for idx in LEFT_IRIS:
                landmark = face_landmarks[idx]
                x = int(landmark.x * w)
                y = int(landmark.y * h)
                left_iris_points.append((x, y))
                cv2.circle(frame, (x, y), 2, (0, 255, 255), -1)  # Yellow
            
            if len(left_iris_points) >= 5:
                left_iris_center = np.mean(left_iris_points, axis=0).astype(int)
                cv2.circle(frame, tuple(left_iris_center), 3, (0, 0, 255), -1)  # Red center
                iris_detected = True
            
            # Draw RIGHT IRIS
            right_iris_points = []
            for idx in RIGHT_IRIS:
                landmark = face_landmarks[idx]
                x = int(landmark.x * w)
                y = int(landmark.y * h)
                right_iris_points.append((x, y))
                cv2.circle(frame, (x, y), 2, (0, 255, 255), -1)  # Yellow
            
            if len(right_iris_points) >= 5:
                right_iris_center = np.mean(right_iris_points, axis=0).astype(int)
                cv2.circle(frame, tuple(right_iris_center), 3, (0, 0, 255), -1)  # Red center
            
            # Update counters
            if eyes_detected:
                eyes_detected_count += 1
            if iris_detected:
                iris_detected_count += 1
            
            # Status text
            status = f"EYES TRACKED | Iris: {'YES' if iris_detected else 'NO'}"
            cv2.putText(frame, status, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Print every 30 frames
            if frame_count % 30 == 0:
                elapsed = time.time() - start_time
                eye_rate = (eyes_detected_count / frame_count) * 100
                iris_rate = (iris_detected_count / frame_count) * 100
                print(f"[{elapsed:.1f}s] Eyes: {eye_rate:.0f}% | Iris: {iris_rate:.0f}% | "
                      f"Landmarks drawn: {len(LEFT_EYE) + len(RIGHT_EYE) + len(LEFT_IRIS) + len(RIGHT_IRIS)}")
        else:
            # No face detected
            cv2.putText(frame, "NO FACE - LOOK AT CAMERA", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            if frame_count % 30 == 0:
                print(f"[{time.time() - start_time:.1f}s] No face detected")
        
        # Frame info
        fps = frame_count / (time.time() - start_time) if time.time() - start_time > 0 else 0
        cv2.putText(frame, f"Frame: {frame_count} | FPS: {fps:.1f}", 
                   (10, frame.shape[0] - 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Legend
        cv2.putText(frame, "Green: Eye contour | Yellow: Iris | Red: Iris center", 
                   (10, frame.shape[0] - 40), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        # Show frame
        cv2.imshow('Eye Tracking (Press Q to quit)', frame)
        
        # Check for quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("\nQuitting...")
            break
    
    # Step 4: Cleanup
    print("\n[4/4] Cleaning up...")
    landmarker.close()
    cap.release()
    cv2.destroyAllWindows()
    
    # Summary
    print("\n" + "=" * 70)
    print("Test Summary:")
    print(f"  Frames processed: {frame_count}")
    print(f"  Eyes detected: {eyes_detected_count} frames ({(eyes_detected_count/frame_count*100) if frame_count > 0 else 0:.1f}%)")
    print(f"  Iris detected: {iris_detected_count} frames ({(iris_detected_count/frame_count*100) if frame_count > 0 else 0:.1f}%)")
    print(f"  Duration: {time.time() - start_time:.1f}s")
    print(f"  Average FPS: {frame_count / (time.time() - start_time):.1f}")
    print("=" * 70)
    
    if iris_detected_count > 0:
        print("\nSUCCESS: Eye and iris tracking is working!")
        print("Next step: Integrate into GazeKey keyboard")
    else:
        print("\nNo iris detected - check lighting and face position")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
