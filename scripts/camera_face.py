"""
Camera + Face Detection Test (Using OpenCV Haar Cascade)
Simple test to verify camera and basic face detection work

This version uses OpenCV's built-in face detection instead of MediaPipe
Once this works, we can upgrade to MediaPipe for iris tracking

Usage: python test_camera_face.py
Press 'q' to quit
"""

import cv2
import time

def main():
    print("=" * 60)
    print("Camera + Face Detection Test (OpenCV)")
    print("=" * 60)
    
    # Step 1: Load face detection model (Haar Cascade - built into OpenCV)
    print("\n[1/4] Loading face detection model...")
    try:
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        print("SUCCESS: Face detection model loaded")
    except Exception as e:
        print(f"ERROR: Could not load face detection model: {e}")
        return
    
    # Step 2: Open camera
    print("\n[2/4] Opening camera...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("ERROR: Could not open camera!")
        print("\nGo to: Windows Settings > Privacy > Camera")
        print("Enable: 'Let desktop apps access your camera'")
        return
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    print("SUCCESS: Camera opened")
    print("  Camera LED should be ON")
    
    # Step 3: Detection loop
    print("\n[3/4] Starting face detection...")
    print("  Look at the camera")
    print("  Press 'q' to quit\n")
    
    frame_count = 0
    face_detected_count = 0
    eyes_detected_count = 0
    start_time = time.time()
    
    while True:
        ret, frame = cap.read()
        
        if not ret:
            print("ERROR: Cannot read frame - check camera permissions")
            break
        
        frame_count += 1
        
        # Convert to grayscale for detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        if len(faces) > 0:
            face_detected_count += 1
            
            # Draw rectangle around face
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                
                # Detect eyes within face region
                roi_gray = gray[y:y+h, x:x+w]
                roi_color = frame[y:y+h, x:x+w]
                eyes = eye_cascade.detectMultiScale(roi_gray)
                
                if len(eyes) > 0:
                    eyes_detected_count += 1
                    
                    # Draw circles around eyes
                    for (ex, ey, ew, eh) in eyes:
                        eye_center = (x + ex + ew//2, y + ey + eh//2)
                        cv2.circle(frame, eye_center, 20, (0, 255, 255), 2)
            
            # Status text
            cv2.putText(frame, f"FACE DETECTED | Eyes: {len(eyes)}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            # Print every 30 frames
            if frame_count % 30 == 0:
                elapsed = time.time() - start_time
                face_rate = (face_detected_count / frame_count) * 100
                eye_rate = (eyes_detected_count / frame_count) * 100
                print(f"[{elapsed:.1f}s] Face: {face_rate:.0f}% | Eyes: {eye_rate:.0f}% | "
                      f"Current eyes detected: {len(eyes)}")
        else:
            # No face
            cv2.putText(frame, "NO FACE - LOOK AT CAMERA", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            if frame_count % 30 == 0:
                print(f"[{time.time() - start_time:.1f}s] No face detected")
        
        # Frame info
        fps = frame_count / (time.time() - start_time) if time.time() - start_time > 0 else 0
        cv2.putText(frame, f"Frame: {frame_count} | FPS: {fps:.1f}", 
                   (10, frame.shape[0] - 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Show frame
        cv2.imshow('Face + Eye Detection Test (Press Q to quit)', frame)
        
        # Check for quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("\nQuitting...")
            break
    
    # Step 4: Cleanup
    print("\n[4/4] Cleaning up...")
    cap.release()
    cv2.destroyAllWindows()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print(f"  Frames processed: {frame_count}")
    print(f"  Face detected: {face_detected_count} frames ({(face_detected_count/frame_count*100) if frame_count > 0 else 0:.1f}%)")
    print(f"  Eyes detected: {eyes_detected_count} frames ({(eyes_detected_count/frame_count*100) if frame_count > 0 else 0:.1f}%)")
    print(f"  Duration: {time.time() - start_time:.1f}s")
    print("=" * 60)
    
    if face_detected_count > 0:
        print("\nSUCCESS: Face detection is working!")
        print("Next step: We can integrate this into the keyboard")
    else:
        print("\nNo faces detected - try different lighting")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
