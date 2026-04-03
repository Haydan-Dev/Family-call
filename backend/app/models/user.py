#imports 
import uuid
import datetime as dt
from pydantic import BaseModel,EmailStr,Field
from typing import Optional

# classes and objects
class User(BaseModel):
      full_name : Optional["str"] | None = None
      email : EmailStr  
      password : str    
      profile_pic_url : Optional["str"] | None = None
      is_online :bool = False
      last_seen_at : dt.datetime = Field(default_factory=lambda: dt.datetime.now())
      created_at : dt.datetime = Field(default_factory=lambda: dt.datetime.now())
      contacts : list = Field(default_factory=list)
      fcm_tokens : dict = Field(default_factory=dict)
      is_deleted : bool = False
      deleted_at : dt.datetime | None = None
      # last_login_at : dt.datetime # abhi kaam baaki hai 
      

