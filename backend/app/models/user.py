#imports 
import uuid
import datetime as dt
from pydantic import BaseModel,EmailStr,Field
# classes and objects
class User(BaseModel):
      user_id : str = Field(default_factory=lambda:str(uuid.uuid4()))
      full_name : str
      email : EmailStr
      password : str = Field(
            min_length = 8,
            max_length = 12,
            pattern=r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]+$"
         )
      profile_pic_url : str
      is_online :bool = False
      last_seen_at : dt.datetime = Field(default_factory=lambda: dt.datetime.now())
      created_at : dt.datetime = Field(default_factory=lambda: dt.datetime.now())
      contacts : list = Field(default_factory=list)
      fcm_tokens : dict = Field(default_factory=dict)
      is_deleted : bool = False
      deleted_at : dt.datetime | None = None