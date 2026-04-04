from fastapi.middleware.cors import CORSMiddleware

def setup_cors(app):
    origins = [
        "https://cerebrum-frontend.onrender.com",
        "https://cerebrum.ai",  # if you have custom domain
        "http://localhost:3000",
        "http://localhost:5173",
    ]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"]
    )
