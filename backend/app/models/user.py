#imports 
import uuid
import datetime as dt
# classes and objects
class User:
   def __init__(self,full_name,email,password,profile_pic_url):
      self.user_id = str(uuid.uuid4())
      self.full_name = full_name
      self.email = email
      self.password = password
      self.profile_pic_url = profile_pic_url
      self.is_online = False
      self.last_seen_at = dt.datetime.now()
      self.created_at =  dt.datetime.now()
      self.contacts = []
      self.fcm_tokens = {}
      self.is_deleted = False
      self.deleted_at = None
