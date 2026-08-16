from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()


def hash_secret(value: str) -> str:
    return password_hash.hash(value)


def verify_secret(value: str, hashed_value: str) -> bool:
    return password_hash.verify(value, hashed_value)
