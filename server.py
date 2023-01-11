from flask import Flask,render_template,Response
from flask_socketio import SocketIO, send
import cv2
from threading import Thread
app = Flask(__name__)
camera=cv2.VideoCapture(1)
app.config['SECRET'] = 'secret!'
socketio = SocketIO(app,cors_allowed_origins="*")
         
            

#t = Thread(target=get_cam)
#t.start()



def generate_frames():
    
    print("A client Connected For video ")
    while True:
        
        ## read the camera frame
        success,frame=camera.read()
        if not success:
            break
        else:
            ret,buffer=cv2.imencode('.jpg',frame)
            frame=buffer.tobytes()

            yield(b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

# When a Client Connected
@socketio.on('connect')
def on_connect():
    print('A client connected')

#When a Client Disconnected
@socketio.on('disconnect')
def on_disconnect():
    print('A client disconnected')

#Messageing 
@socketio.on('message')
def on_message(message):
    print('Received message: ' + message)
    if message=="R":
        print("Robot Move Right")
    if message=="L":
        print("Robot Move Left")
    if message=="F":
        print("Robot Move Font")
    if message=="B":
        print("Robot move back")
    if message[0]=="!" and message[1]=="S":
        print("Value is setting")
    send(message, broadcast=True)


#default Index.html page shows.
@app.route('/')
def index():
    return render_template('./index.html')



@app.route('/video')
def video():
    return Response(generate_frames(),mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    socketio.run(app,host="0.0.0.0")
