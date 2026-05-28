"""
SUPER SIMPLE Camera Test
Just opens the camera and shows the video feed - no face detection yet

Usage: python test_camera_simple.py
Press 'q' to quit
"""

import cv2
import time

def main():
    print("=" * 50)
    print("Simple Camera Test")
    print("=" * 50)
    
    # Open webcam
    print("\nOpening camera...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("ERROR: Could not open camera!")
        print("\nTo fix this:")
        print("  1. Go to Windows Settings")
        print("  2. Search for 'Camera privacy settings'")
        print("  3. Turn ON 'Let apps access your camera'")
        print("  4. Turn ON 'Let desktop apps access your camera'")
        print("  5. Restart this script")
        input("\nPress Enter to exit...")
        return
    
    print("SUCCESS: Camera is open!")
    print("  Your camera LED should be ON")
    print("  A window will open showing the camera feed")
    print("  Press 'q' to quit\n")
    
    frame_count = 0
    start_time = time.time()
    
    while True:
        # Read frame
        ret, frame = cap.read()
        
        if not ret:
            print("ERROR: Cannot read from camera")
            break
        
        frame_count += 1
        
        # Add some text to show it's working
        cv2.putText(frame, "Camera is working!", (50, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        elapsed = time.time() - start_time
        fps = frame_count / elapsed if elapsed > 0 else 0
        cv2.putText(frame, f"Frame: {frame_count} | FPS: {fps:.1f}", 
                   (10, frame.shape[0] - 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Show frame
        cv2.imshow('Camera Test - Press Q to quit', frame)
        
        # Print status every 2 seconds
        if frame_count % 60 == 0:
            print(f"[{elapsed:.1f}s] Camera working - {frame_count} frames captured | FPS: {fps:.1f}")
        
        # Check for 'q' key
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("\nQuitting...")
            break
    
    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    
    print("\n" + "=" * 50)
    print(f"Test complete! Captured {frame_count} frames in {elapsed:.1f} seconds")
    print("=" * 50)
    
    if frame_count > 60:
        print("\nSUCCESS: Camera is working correctly!")
    else:
        print("\nTest was too short to verify properly")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted")
    except Exception as e:
        print(f"\nERROR: {e}")
