import os
import logging
import firebase_admin
from firebase_admin import credentials

logger = logging.getLogger(__name__)

def initialize_firebase():
    """
    Firebase Admin SDK ko safely start karne ka engine.
    Ye khud root folder mein jakar JSON chaabi dhoondhega.
    """
    # 1. Current file ka address nikalo (app/core/firebase_config.py)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 2. Do level upar jao (app -> root)
    root_dir = os.path.dirname(os.path.dirname(current_dir))
    
    # 3. JSON file ka exact production-safe path banao
    cred_path = os.path.join(root_dir, "firebase-credentials.json")

    try:
        # 4. Check karo ki uvicorn reload ki wajah se Firebase pehle se start toh nahi hai
        if not firebase_admin._apps:
            if not os.path.exists(cred_path):
                logger.error(f"FCM ERROR: Firebase chaabi nahi mili at {cred_path}")
                return
            
            # 5. Chaabi lagao aur engine start karo
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            logger.info("🔥 FCM (Firebase Admin) Zinda Ho Gaya Hai! Ready for Push Notifications.")
            print("FCM (Firebase Admin) Zinda Ho Gaya Hai! Ready for Push Notifications.")
            
    except Exception as e:
        logger.error(f"FCM Start hone mein fail hua: {str(e)}", exc_info=True)