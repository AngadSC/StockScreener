from pydantic_settings import BaseSettings
from typing import List
import os

class Setting(BaseSettings): 
    DATABASE_URL: 
    REDIS_URL: 

    #JWT
    SECRET_KEY : 
    ALGORITHM: 