import os
from website import create_app, socketio

app = create_app()

if __name__ == '__main__':
    socketio.run(app, 
                 host="0.0.0.0", 
                 port=os.getenv('PORT'), 
                 debug=True,
                 allow_unsafe_werkzeug=True)