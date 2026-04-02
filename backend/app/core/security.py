# imports
import bcrypt

class PasswordHelper:
    @staticmethod
    def hash_password(passwordhashing):
        password_hash = passwordhashing.encode('utf-8')
        password_salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password_hash, password_salt)
        return  hashed_password.decode('utf-8')

