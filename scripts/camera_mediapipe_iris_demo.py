"""
Simple Camera + Eye Detection Test
Test script to verify webcam and MediaPipe eye tracking work correctly

Usage: python test_camera_tracking.py
Press 'q' to quit
"""

import cv2
import time
import sys

def main():
    print("=" * 50)
    print("Camera + Eye Detection Test")
    print("=" * 50)
    
    # Step 1: Initialize MediaPipe Face Mesh
    print("\n[1/4] Initializing MediaPipe...")
    try:
        # Try to import MediaPipe with the legacy solutions API
        # This works with pip installed mediapipe 0.8-0.10
        import mediapipe.python.solutions as mp_solutions
        
        face_mesh = mp_solutions.face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,  # Enable iris tracking
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        mp_drawing = mp_solutions.drawing_utils
        mp_drawing_styles = mp_solutions.drawing_styles
        
        print("SUCCESS: MediaPipe initialized")
        
    except (ImportError, AttributeError) as e:
        print(f"ERROR: Could not initialize MediaPipe")
        print(f"Details: {e}")
        print("\nMediaPipe needs to be reinstalled with the correct version.")
        print("Run: pip uninstall mediapipe")
        print("Then: pip install mediapipe==0.10.9")
        return
    
    # Step 2: Open webcam
    print("\n[2/4] Opening camera...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("ERROR: Could not open camera")
        print("\nPossible solutions:")
        print("  1. Enable camera in Windows Settings > Privacy > Camera")
        print("  2. Close other apps using the camera (Zoom, Teams, etc.)")
        print("  3. Check if camera LED turns on")
        return
    
    # Set camera properties
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print("SUCCESS: Camera opened")
    print(f"  Resolution: {actual_width}x{actual_height}")
    print(f"  Camera LED should be ON now")
    
    # Step 3: Main detection loop
    print("\n[3/4] Starting detection loop...")
    print("  A window will open showing the camera feed")
    print("  Look at the camera - your face and eyes should be detected")
    print("  Press 'q' in the video window to quit\n")
    
    frame_count = 0
    face_detected_count = 0
    start_time = time.time()
    
    # Iris landmark indices (MediaPipe)
    LEFT_IRIS_INDICES = [468, 469, 470, 471, 472]
    RIGHT_IRIS_INDICES = [473, 474, 475, 476, 477]
    
    try:
        while True:
            # Read frame from camera
            ret, frame = cap.read()
            
            if not ret:
                print("ERROR: Failed to read frame")
                break
            
            frame_count += 1
            
            # Convert BGR to RGB (MediaPipe needs RGB)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Run MediaPipe detection
            results = face_mesh.process(rgb_frame)
            
            # Check if face detected
            if results.multi_face_landmarks:
                face_detected_count += 1
                
                # Get landmarks
                face_landmarks = results.multi_face_landmarks[0]
                landmarks = face_landmarks.landmark
                
                # Calculate iris centers
                left_iris_x = sum(landmarks[i].x for i in LEFT_IRIS_INDICES) / len(LEFT_IRIS_INDICES)
                left_iris_y = sum(landmarks[i].y for i in LEFT_IRIS_INDICES) / len(LEFT_IRIS_INDICES)
                
                right_iris_x = sum(landmarks[i].x for i in RIGHT_IRIS_INDICES) / len(RIGHT_IRIS_INDICES)
                right_iris_y = sum(landmarks[i].y for i in RIGHT_IRIS_INDICES) / len(RIGHT_IRIS_INDICES)
                
                # Print detection info every 30 frames (once per second at 30 FPS)
                if frame_count % 30 == 0:
                    elapsed = time.time() - start_time
                    detection_rate = (face_detected_count / frame_count) * 100
                    print(f"[{elapsed:.1f}s] FACE DETECTED | "
                          f"Left iris: ({left_iris_x:.3f}, {left_iris_y:.3f}) | "
                          f"Right iris: ({right_iris_x:.3f}, {right_iris_y:.3f}) | "
                          f"Rate: {detection_rate:.0f}%")
                
                # Draw all face landmarks
                mp_drawing.draw_landmarks(
                    image=frame,
                    landmark_list=face_landmarks,
                    connections=mp_solutions.face_mesh.FACEMESH_TESSELATION,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_tesselation_style()
                )
                
                # Draw iris landmarks with bright green circles
                h, w = frame.shape[:2]
                for i in LEFT_IRIS_INDICES + RIGHT_IRIS_INDICES:
                    x = int(landmarks[i].x * w)
                    y = int(landmarks[i].y * h)
                    cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)
                
                # Draw iris centers with yellow circles
                left_center = (int(left_iris_x * w), int(left_iris_y * h))
                right_center = (int(right_iris_x * w), int(right_iris_y * h))
                cv2.circle(frame, left_center, 5, (0, 255, 255), 2)
                cv2.circle(frame, right_center, 5, (0, 255, 255), 2)
                
                # Add status text
                cv2.putText(frame, "FACE DETECTED", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            else:
                # No face detected
                if frame_count % 30 == 0:
                    elapsed = time.time() - start_time
                    print(f"[{elapsed:.1f}s] No face detected - look at the camera")
                
                cv2.putText(frame, "NO FACE - LOOK AT CAMERA", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Add frame counter and FPS
            fps = frame_count / (time.time() - start_time) if time.time() - start_time > 0 else 0
            cv2.putText(frame, f"Frame: {frame_count} | FPS: {fps:.1f}", 
                       (10, frame.shape[0] - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Show frame
            cv2.imshow('Camera + Eye Detection Test (Press Q to quit)', frame)
            
            # Check for 'q' key press
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == ord('Q'):
                print("\n'q' pressed - exiting...")
                break
                
    except KeyboardInterrupt:
        print("\n\nInterrupted by user (Ctrl+C)")
    
    # Step 4: Cleanup
    print("\n[4/4] Cleaning up...")
    cap.release()
    cv2.destroyAllWindows()
    face_mesh.close()
    
    # Print summary
    print("\n" + "=" * 50)
    print("Test Summary:")
    print(f"  Total frames processed: {frame_count}")
    print(f"  Faces detected in: {face_detected_count} frames")
    if frame_count > 0:
        detection_rate = (face_detected_count / frame_count) * 100
        print(f"  Detection rate: {detection_rate:.1f}%")
    print(f"  Duration: {time.time() - start_time:.1f}s")
    print("=" * 50)
    
    if face_detected_count > 0:
        print("\nSUCCESS: Camera and eye detection working correctly!")
        print("You can now integrate this into the main keyboard application.")
    else:
        print("\nWARNING: No faces were detected")
        print("  Make sure you were looking at the camera")
        print("  Check lighting conditions")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
