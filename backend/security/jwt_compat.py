"""JWT signing and verification backed by maintained PyJWT.

The app's callers continue to supply an explicit algorithm allowlist.
Unverified claims are used only to explain an already rejected session token.
"""
import jwt as _jwt
from jwt import InvalidTokenError as JWTError


class JWT:
    encode = staticmethod(_jwt.encode)
    decode = staticmethod(_jwt.decode)

    @staticmethod
    def get_unverified_claims(token):
        if not isinstance(token, str) or len(token) > 65536:
            raise JWTError("Invalid token size")
        return _jwt.decode(token, options={"verify_signature": False})


jwt = JWT()
