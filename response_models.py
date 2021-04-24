from typing import Dict, Optional

from pydantic import BaseModel


class AuthCodes(BaseModel):
    auth_codes: Dict[str, Optional[int]]

    class Config:
        schema_extra = {
            "example": {
                "auth_codes": {"+123456789": 12345, "+987654321": 67890}
            }
        }


class AuthCode(BaseModel):
    auth_code: int

    class Config:
        schema_extra = {
            "example": {
                "auth_code": 12345
            }
        }


class SimpleError(BaseModel):
    detail: str


class MyTimeoutError(BaseModel):
    processing_time: float

    class Config:
        schema_extra = {
            "example": {
                "detail": "Request processing time excedeed limit",
                "processing_time": 	89.99175810813904
            }
        }
