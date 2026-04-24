from __future__ import annotations

import json
import math
import secrets
from dataclasses import dataclass
from pathlib import Path


def _lcm(left: int, right: int) -> int:
    return abs(left * right) // math.gcd(left, right)


def _is_probable_prime(candidate: int, rounds: int = 24) -> bool:
    if candidate < 2:
        return False
    small_primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37]
    for prime in small_primes:
        if candidate == prime:
            return True
        if candidate % prime == 0:
            return False

    d = candidate - 1
    s = 0
    while d % 2 == 0:
        s += 1
        d //= 2

    for _ in range(rounds):
        base = secrets.randbelow(candidate - 3) + 2
        value = pow(base, d, candidate)
        if value in {1, candidate - 1}:
            continue
        for _ in range(s - 1):
            value = pow(value, 2, candidate)
            if value == candidate - 1:
                break
        else:
            return False
    return True


def _generate_prime(bits: int) -> int:
    while True:
        candidate = secrets.randbits(bits)
        candidate |= (1 << (bits - 1)) | 1
        if _is_probable_prime(candidate):
            return candidate


def _random_coprime(modulus: int) -> int:
    while True:
        value = secrets.randbelow(modulus - 1) + 1
        if math.gcd(value, modulus) == 1:
            return value


@dataclass(frozen=True, slots=True)
class PaillierPublicKey:
    n: int
    g: int

    @property
    def n_square(self) -> int:
        return self.n * self.n

    @property
    def bits(self) -> int:
        return self.n.bit_length()

    def encode_signed(self, value: int) -> int:
        return value % self.n

    def decode_signed(self, encoded: int) -> int:
        return encoded - self.n if encoded > self.n // 2 else encoded

    def encrypt(self, value: int) -> int:
        encoded = self.encode_signed(value)
        randomizer = _random_coprime(self.n)
        return (pow(self.g, encoded, self.n_square) * pow(randomizer, self.n, self.n_square)) % self.n_square

    def add(self, left_ciphertext: int, right_ciphertext: int) -> int:
        return (left_ciphertext * right_ciphertext) % self.n_square

    def negate(self, ciphertext: int) -> int:
        return pow(ciphertext, -1, self.n_square)

    def subtract(self, left_ciphertext: int, right_ciphertext: int) -> int:
        return self.add(left_ciphertext, self.negate(right_ciphertext))

    def to_dict(self) -> dict[str, str | int]:
        return {
            "scheme": "paillier",
            "key_bits": self.bits,
            "n": str(self.n),
            "g": str(self.g),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, str | int]) -> "PaillierPublicKey":
        if payload.get("scheme") != "paillier":
            raise ValueError("Unsupported public key scheme.")
        return cls(n=int(payload["n"]), g=int(payload["g"]))


@dataclass(frozen=True, slots=True)
class PaillierPrivateKey:
    public_key: PaillierPublicKey
    lambda_value: int
    mu: int

    def decrypt(self, ciphertext: int) -> int:
        value = pow(ciphertext, self.lambda_value, self.public_key.n_square)
        l_value = (value - 1) // self.public_key.n
        encoded = (l_value * self.mu) % self.public_key.n
        return self.public_key.decode_signed(encoded)

    def to_dict(self) -> dict[str, str | int | dict[str, str | int]]:
        return {
            "scheme": "paillier",
            "public_key": self.public_key.to_dict(),
            "lambda": str(self.lambda_value),
            "mu": str(self.mu),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "PaillierPrivateKey":
        if payload.get("scheme") != "paillier":
            raise ValueError("Unsupported private key scheme.")
        public_key = PaillierPublicKey.from_dict(payload["public_key"])  # type: ignore[arg-type]
        return cls(
            public_key=public_key,
            lambda_value=int(payload["lambda"]),  # type: ignore[arg-type]
            mu=int(payload["mu"]),  # type: ignore[arg-type]
        )


def generate_keypair(bits: int = 1024) -> PaillierPrivateKey:
    if bits < 256:
        raise ValueError("Paillier key size must be at least 256 bits for this demo.")
    half_bits = bits // 2
    p = _generate_prime(half_bits)
    q = _generate_prime(bits - half_bits)
    while p == q:
        q = _generate_prime(bits - half_bits)
    n = p * q
    public_key = PaillierPublicKey(n=n, g=n + 1)
    lambda_value = _lcm(p - 1, q - 1)
    value = pow(public_key.g, lambda_value, public_key.n_square)
    l_value = (value - 1) // public_key.n
    mu = pow(l_value, -1, public_key.n)
    return PaillierPrivateKey(public_key=public_key, lambda_value=lambda_value, mu=mu)


def load_private_key(path: str | Path) -> PaillierPrivateKey:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return PaillierPrivateKey.from_dict(payload)


def write_private_key(path: str | Path, private_key: PaillierPrivateKey) -> Path:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(private_key.to_dict(), indent=2) + "\n", encoding="utf-8")
    file_path.chmod(0o600)
    return file_path


def load_or_create_private_key(path: str | Path, bits: int = 1024) -> PaillierPrivateKey:
    file_path = Path(path)
    if file_path.exists():
        return load_private_key(file_path)
    private_key = generate_keypair(bits=bits)
    write_private_key(file_path, private_key)
    return private_key
