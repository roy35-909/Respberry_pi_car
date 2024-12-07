from flask import Flask, render_template, Response, jsonify
from flask_socketio import SocketIO, send, emit
import cv2
import logging
from threading import Lock

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

camera = None
current_camera_index = None
camera_lock = Lock()  # Lock for thread-safe camera access
websocket_connected = False
camera_active = True  # Flag to manage camera feed


def initialize_camera(source=0):
    """Initialize the camera safely."""
    global camera, current_camera_index
    try:
        with camera_lock:
            # Release any existing camera
            if camera is not None:
                camera.release()
                logging.debug(f"Released previous camera source {current_camera_index}")
            
            # Attempt to initialize the new camera
            new_camera = cv2.VideoCapture(source)
            if not new_camera.isOpened():
                raise ValueError(f"Camera source {source} is not available.")
            
            # Successfully initialized camera
            camera = new_camera
            current_camera_index = source
            logging.debug(f"Camera initialized with source {source}")
            return True
    except Exception as e:
        logging.error(f"Error initializing camera: {e}")
        return False


def generate_frames():
    """Generate video frames from the camera."""
    global camera, camera_active
    while True:
        with camera_lock:
            if not camera_active:
                logging.debug("Camera feed stopped")
                break
            if camera is None or not camera.isOpened():
                yield b'--frame\r\nContent-Type: text/plain\r\n\r\nCamera not available\r\n\r\n'
                break
            success, frame = camera.read()
            if not success:
                break
            else:
                ret, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@socketio.on('connect')
def handle_connect():
    global websocket_connected, camera_active
    websocket_connected = True
    camera_active = True  # Enable camera feed when WebSocket connects
    logging.debug("[WebSocket] Client connected")


@socketio.on('disconnect')
def handle_disconnect():
    global websocket_connected, camera_active
    websocket_connected = False
    camera_active = False  # Disable camera feed when WebSocket disconnects
    logging.debug("[WebSocket] Client disconnected")


@socketio.on('disconnect_request')
def handle_disconnect_request():
    global camera_active
    camera_active = False  # Stop the camera feed
    emit('disconnect_confirmed')
    logging.debug("[WebSocket] Disconnect request received")


@app.route('/')
def index():
    """Render the main interface."""
    return render_template('index.html')


@app.route('/video')
def video():
    """Stream video from the camera."""
    global camera_active
    if not camera_active:
        logging.debug("Camera feed request denied: Camera inactive")
        return Response(
            b"--frame\r\nContent-Type: text/plain\r\n\r\nCamera inactive\r\n\r\n",
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/switch_camera/<int:source>', methods=['GET'])
def switch_camera(source):
    """Switch the camera source."""
    logging.debug(f"Received request to switch camera to source {source}")
    global camera_active
    camera_active = False  # Temporarily stop the camera feed
    if initialize_camera(source):
        camera_active = True  # Reactivate the camera feed after switching
        logging.debug(f"Successfully switched to camera source {source}")
        return jsonify({"status": "success", "message": f"Switched to camera {source}"})
    else:
        logging.error(f"Failed to switch to camera source {source}")
        return jsonify({"status": "error", "message": f"Failed to switch to camera {source}. Please check the camera source."})


if __name__ == '__main__':
    # Initialize the default camera (laptop camera)
    initialize_camera(0)
    try:
        logging.debug("Starting Flask server with SocketIO...")
        socketio.run(app, host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        logging.error(f"Error starting the server: {e}")
