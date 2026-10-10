from secrets import compare_digest

import jwt
from allauth.socialaccount.providers.oauth2.client import OAuth2Error


ID_TOKEN_ALGORITHMS = ("RS256", "RS512")


def validate_id_token(id_token, jwks, *, audience, issuer, nonce):
    try:
        header = jwt.get_unverified_header(id_token)
        algorithm = header["alg"]
        key_id = header["kid"]
        if algorithm not in ID_TOKEN_ALGORITHMS:
            raise ValueError("Unsupported signing algorithm")

        signing_key = next(key for key in jwks["keys"] if key["kid"] == key_id)
        key = jwt.PyJWK.from_dict(signing_key).key
        claims = jwt.decode(
            id_token,
            key,
            algorithms=ID_TOKEN_ALGORITHMS,
            audience=audience,
            issuer=issuer,
            options={"require": ["aud", "exp", "iss", "nonce", "sub"]},
        )
    except (jwt.PyJWTError, KeyError, StopIteration, TypeError, ValueError):
        raise OAuth2Error("Invalid GOV.BR ID token") from None

    if not claims["sub"] or not nonce:
        raise OAuth2Error("Invalid GOV.BR ID token")
    if (
        isinstance(claims["aud"], list)
        and len(claims["aud"]) > 1
        and claims.get("azp") != audience
    ):
        raise OAuth2Error("Invalid GOV.BR ID token")
    try:
        nonce_matches = compare_digest(claims["nonce"], nonce)
    except TypeError:
        nonce_matches = False
    if not nonce_matches:
        raise OAuth2Error("Invalid GOV.BR ID token")
    return claims
