from fastapi.middleware.cors import CORSMiddleware

def core(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Abhi ke liye sabko allow kar rahe hain (Development mode)
        allow_credentials=True,
        allow_methods=["*"],  # GET, POST, DELETE sab allow karega
        allow_headers=["*"],  # Token aur JSON headers allow karega
    )