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
