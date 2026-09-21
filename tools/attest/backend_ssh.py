"""Fail-closed ``ssh-keygen -Y`` signature backend for Trinity attestations."""

from __future__ import annotations

import base64
import binascii
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from . import backend

SignatureBackendError = backend.SignatureBackendError
VerificationFailureReason = backend.VerificationFailureReason
VerificationResult = backend.VerificationResult

# SECURITY BOUNDARY: every Trinity attestation uses this namespace. Changing it changes the
# signed purpose and invalidates cross-purpose replay protection.
TRINITY_ATTESTATION_NAMESPACE = "trinity.attestation.v1"
GIT_SIGNATURE_NAMESPACE = "git"
ALLOWED_NAMESPACES = frozenset({TRINITY_ATTESTATION_NAMESPACE, GIT_SIGNATURE_NAMESPACE})

# DSSE keyid scheme name for OpenSSH's armored SSHSIG format, not a raw Ed25519 signature.
SSH_KEYID_SCHEME = "ssh-keygen:sshsig:v1"

DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_SSH_KEYGEN_EXECUTABLE = Path("/usr/bin/ssh-keygen")
MIN_ARMOR_LINES = 3
SSH_SIGNATURE_HEADER = b"-----BEGIN SSH SIGNATURE-----"
SSH_SIGNATURE_FOOTER = b"-----END SSH SIGNATURE-----"
OPENSSH_PRIVATE_KEY_HEADER = b"-----BEGIN OPENSSH PRIVATE KEY-----"
OPENSSH_PRIVATE_KEY_FOOTER = b"-----END OPENSSH PRIVATE KEY-----"
OPENSSH_PRIVATE_KEY_MAGIC = b"openssh-key-v1\x00"
SSHSIG_MAGIC = b"SSHSIG"
SSHSIG_VERSION = 1
MAX_PRIVATE_KEY_BYTES = 1024 * 1024
MAX_SIGNATURE_BYTES = 256 * 1024
MAX_ALLOWED_SIGNERS_BYTES = 1024 * 1024
MAX_BINARY_FIELD_BYTES = 256 * 1024
MAX_ALLOWED_SIGNERS_LINE_BYTES = 16 * 1024
MAX_KEY_ALGORITHM_BYTES = 128
MAX_PRIVATE_PUBLIC_KEYS = 1
MIN_ALLOWED_SIGNERS_KEY_INDEX = 2
SOFTWARE_KEY_ALGORITHMS = frozenset(
    {
        "ecdsa-sha2-nistp256",
        "ecdsa-sha2-nistp384",
        "ecdsa-sha2-nistp521",
        "ssh-ed25519",
        "ssh-rsa",
    }
)
SOFTWARE_CERTIFICATE_ALGORITHMS = frozenset(
    {f"{algorithm}-cert-v01@openssh.com" for algorithm in SOFTWARE_KEY_ALGORITHMS}
)
SOFTWARE_PUBLIC_KEY_ALGORITHMS = SOFTWARE_KEY_ALGORITHMS | SOFTWARE_CERTIFICATE_ALGORITHMS
SOFTWARE_SIGNATURE_ALGORITHMS = frozenset(
    {
        "ecdsa-sha2-nistp256",
        "ecdsa-sha2-nistp384",
        "ecdsa-sha2-nistp521",
        "rsa-sha2-256",
        "rsa-sha2-512",
        "ssh-ed25519",
    }
)
SECURITY_KEY_ALGORITHMS = frozenset(
    {
        "sk-ecdsa-sha2-nistp256@openssh.com",
        "sk-ecdsa-sha2-nistp256-cert-v01@openssh.com",
        "sk-ssh-ed25519@openssh.com",
        "sk-ssh-ed25519-cert-v01@openssh.com",
    }
)
PRINCIPAL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._@:+/-]{0,254}", re.ASCII)


def _verified_output(namespace: str) -> re.Pattern[str]:
    return re.compile(
        rf'Good "{re.escape(namespace)}" signature for '
        r"(?P<principal>[A-Za-z0-9][A-Za-z0-9._@:+/-]{0,254}) with "
        r"[A-Z0-9-]+ key SHA256:[A-Za-z0-9+/]{43,}={0,2}",
        re.ASCII,
    )


VERIFIED_OUTPUT_BY_NAMESPACE = {
    namespace: _verified_output(namespace) for namespace in ALLOWED_NAMESPACES
}


class _InvocationError(Exception):
    def __init__(self, reason: VerificationFailureReason, detail: str) -> None:
        self.reason = reason
        self.detail = detail
        super().__init__(detail)


class _AlgorithmPolicyError(ValueError):
    """A parsed SSH carrier selected an algorithm outside software-only policy."""


class _BinaryReader:
    """Read bounded SSH binary fields without exposing their contents in errors."""

    def __init__(self, data: bytes) -> None:
        self._data = data
        self._offset = 0

    def read_exact(self, length: int) -> bytes:
        if length < 0 or self._offset + length > len(self._data):
            raise ValueError("truncated SSH binary carrier")
        value = self._data[self._offset : self._offset + length]
        self._offset += length
        return value

    def read_u32(self) -> int:
        return int.from_bytes(self.read_exact(4), "big")

    def read_string(self) -> bytes:
        length = self.read_u32()
        if length > MAX_BINARY_FIELD_BYTES:
            raise ValueError("SSH binary field exceeds policy limit")
        return self.read_exact(length)

    def require_end(self) -> None:
        if self._offset != len(self._data):
            raise ValueError("SSH binary carrier has trailing bytes")


class SshKeygenBackend:
    """Sign and verify exact payload bytes through a pinned ``ssh-keygen`` executable.

    ``executable`` must be absolute so subprocess execution never consults an
    attacker-influenced ``PATH``. The default is Trinity's conventional POSIX
    system path; deployments whose system binary lives elsewhere must supply
    that administrator-pinned absolute path explicitly.
    """

    keyid_scheme = SSH_KEYID_SCHEME
    namespace = TRINITY_ATTESTATION_NAMESPACE

    def __init__(
        self,
        *,
        executable: str | Path = DEFAULT_SSH_KEYGEN_EXECUTABLE,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        namespace: str = TRINITY_ATTESTATION_NAMESPACE,
    ) -> None:
        if namespace not in ALLOWED_NAMESPACES:
            raise ValueError(f"unsupported signature namespace: {namespace}")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        executable_path = Path(executable)
        if not executable_path.is_absolute():
            raise ValueError("ssh-keygen executable path must be absolute")
        self.executable = executable_path
        self.timeout_seconds = timeout_seconds
        self.namespace = namespace

    def sign(self, payload: bytes, *, key_path: Path) -> bytes:
        """Return the armored SSHSIG emitted for ``payload`` using ``key_path``."""

        temporary_path: Path | None = None
        try:
            self._validate_private_key_policy(key_path)
            temporary_path = Path(tempfile.mkdtemp(prefix="trinity-attest-"))
            payload_path = temporary_path / "payload"
            signature_path = payload_path.with_name(f"{payload_path.name}.sig")
            payload_path.write_bytes(payload)
            completed = self._run(
                [
                    str(self.executable),
                    "-Y",
                    "sign",
                    "-f",
                    str(key_path),
                    "-n",
                    self.namespace,
                    str(payload_path),
                ],
                payload,
            )
            stdout, stderr = self._decode_output(completed)
            if completed.returncode != 0:
                detail = self._failure_detail(completed.returncode, stdout, stderr)
                raise SignatureBackendError(VerificationFailureReason.TOOL_FAILURE, detail)
            try:
                signature = signature_path.read_bytes()
            except OSError as error:
                detail = f"ssh-keygen did not leave a readable signature: {error}"
                raise SignatureBackendError(
                    VerificationFailureReason.OUTPUT_UNPARSEABLE,
                    detail,
                ) from error
            if not self._has_armor(signature):
                raise SignatureBackendError(
                    VerificationFailureReason.OUTPUT_UNPARSEABLE,
                    "ssh-keygen returned success without a complete armored SSH signature",
                )
            return signature
        except _InvocationError as error:
            raise SignatureBackendError(error.reason, error.detail) from error
        except OSError as error:
            raise SignatureBackendError(
                VerificationFailureReason.TOOL_FAILURE,
                f"could not stage payload bytes for ssh-keygen: {error}",
            ) from error
        finally:
            if temporary_path is not None:
                try:
                    shutil.rmtree(temporary_path)
                except OSError as error:
                    raise SignatureBackendError(
                        VerificationFailureReason.TEMPORARY_FILE_CLEANUP_FAILURE,
                        f"could not remove temporary signing workspace: {error}",
                    ) from error

    def verify(
        self,
        payload: bytes,
        *,
        signature_path: Path,
        allowed_signers_path: Path,
        evaluation_time: object = None,
    ) -> VerificationResult:
        """Verify ``payload`` at an explicit UTC instant and return its principal."""

        verification_time = self._verification_time(evaluation_time)
        if isinstance(verification_time, VerificationResult):
            return verification_time
        signature = self._read_signature(signature_path)
        if isinstance(signature, VerificationResult):
            return signature
        if not self._has_armor(signature):
            return VerificationResult.failure(
                VerificationFailureReason.SIGNATURE_MALFORMED,
                f"{signature_path} is not a complete armored SSH signature",
            )
        carrier_policy = self._validate_signature_policy(signature)
        if carrier_policy is not None:
            return carrier_policy
        if not allowed_signers_path.is_file():
            return VerificationResult.failure(
                VerificationFailureReason.TRUST_POLICY_MISSING,
                f"allowed signers file is missing: {allowed_signers_path}",
            )
        trust_policy = self._validate_allowed_signers_policy(allowed_signers_path)
        if trust_policy is not None:
            return trust_policy

        try:
            checked = self._run(
                [
                    str(self.executable),
                    "-Y",
                    "check-novalidate",
                    "-n",
                    self.namespace,
                    "-s",
                    str(signature_path),
                ],
                payload,
            )
            checked_stdout, checked_stderr = self._decode_output(checked)
            if checked.returncode != 0:
                return self._failed_process(checked, checked_stdout, checked_stderr)

            found = self._run(
                [
                    str(self.executable),
                    "-Y",
                    "find-principals",
                    "-O",
                    f"verify-time={verification_time}",
                    "-s",
                    str(signature_path),
                    "-f",
                    str(allowed_signers_path),
                ],
                payload,
            )
            found_stdout, found_stderr = self._decode_output(found)
            if found.returncode != 0:
                return self._failed_process(found, found_stdout, found_stderr)
            principals = self._parse_principals(found_stdout, found_stderr)

            for principal in principals:
                verified = self._run(
                    [
                        str(self.executable),
                        "-Y",
                        "verify",
                        "-O",
                        f"verify-time={verification_time}",
                        "-f",
                        str(allowed_signers_path),
                        "-I",
                        principal,
                        "-n",
                        self.namespace,
                        "-s",
                        str(signature_path),
                    ],
                    payload,
                )
                verified_stdout, verified_stderr = self._decode_output(verified)
                if verified.returncode != 0:
                    return self._failed_process(verified, verified_stdout, verified_stderr)
                return self._parse_verified_principal(
                    principal,
                    verified_stdout,
                    verified_stderr,
                )
            return VerificationResult.failure(
                VerificationFailureReason.OUTPUT_UNPARSEABLE,
                "ssh-keygen returned success without any principal",
            )
        except _InvocationError as error:
            return VerificationResult.failure(error.reason, error.detail)

    def _run(self, argv: list[str], payload: bytes) -> subprocess.CompletedProcess[bytes]:
        try:
            return subprocess.run(
                argv,
                input=payload,
                capture_output=True,
                check=False,
                shell=False,
                timeout=self.timeout_seconds,
                env={"LC_ALL": "C"},
            )
        except FileNotFoundError as error:
            raise _InvocationError(
                VerificationFailureReason.TOOL_ABSENT,
                f"signature tool is absent: {self.executable}",
            ) from error
        except subprocess.TimeoutExpired as error:
            raise _InvocationError(
                VerificationFailureReason.TOOL_TIMEOUT,
                f"ssh-keygen exceeded the {self.timeout_seconds:g} second timeout",
            ) from error
        except OSError as error:
            raise _InvocationError(
                VerificationFailureReason.TOOL_FAILURE,
                f"could not execute ssh-keygen: {error}",
            ) from error

    @classmethod
    def _validate_private_key_policy(cls, key_path: Path) -> None:
        try:
            armored = cls._read_bounded(key_path, MAX_PRIVATE_KEY_BYTES, "private key")
            decoded = cls._decode_armor(
                armored,
                OPENSSH_PRIVATE_KEY_HEADER,
                OPENSSH_PRIVATE_KEY_FOOTER,
                MAX_PRIVATE_KEY_BYTES,
            )
            reader = _BinaryReader(decoded)
            if reader.read_exact(len(OPENSSH_PRIVATE_KEY_MAGIC)) != OPENSSH_PRIVATE_KEY_MAGIC:
                raise ValueError("private key is not OpenSSH key-v1 data")
            reader.read_string()  # cipher name
            reader.read_string()  # KDF name
            reader.read_string()  # KDF options
            key_count = reader.read_u32()
            if key_count != MAX_PRIVATE_PUBLIC_KEYS:
                raise ValueError("private key must contain exactly one public key")
            public_algorithm = cls._public_blob_algorithm(reader.read_string())
            cls._require_software_algorithm(public_algorithm, "private key public header")
        except (OSError, ValueError) as error:
            raise SignatureBackendError(
                VerificationFailureReason.KEY_ALGORITHM_FORBIDDEN,
                f"software-key policy refused the signing key: {error}",
            ) from error

    @classmethod
    def _validate_signature_policy(cls, signature: bytes) -> VerificationResult | None:
        try:
            decoded = cls._decode_armor(
                signature,
                SSH_SIGNATURE_HEADER,
                SSH_SIGNATURE_FOOTER,
                MAX_SIGNATURE_BYTES,
            )
            reader = _BinaryReader(decoded)
            if reader.read_exact(len(SSHSIG_MAGIC)) != SSHSIG_MAGIC:
                raise ValueError("signature carrier has invalid magic")
            if reader.read_u32() != SSHSIG_VERSION:
                raise ValueError("signature carrier has unsupported version")
            public_algorithm = cls._public_blob_algorithm(reader.read_string())
            cls._require_software_algorithm(public_algorithm, "SSHSIG public key")
            reader.read_string()  # namespace
            reader.read_string()  # reserved
            reader.read_string()  # hash algorithm
            signature_reader = _BinaryReader(reader.read_string())
            signature_algorithm = cls._decode_algorithm(signature_reader.read_string())
            cls._require_signature_algorithm(signature_algorithm, public_algorithm)
            signature_reader.read_string()
            signature_reader.require_end()
            reader.require_end()
        except _AlgorithmPolicyError as error:
            return VerificationResult.failure(
                VerificationFailureReason.KEY_ALGORITHM_FORBIDDEN,
                f"software-key policy refused the SSHSIG carrier: {error}",
            )
        except ValueError as error:
            return VerificationResult.failure(
                VerificationFailureReason.SIGNATURE_MALFORMED,
                f"could not parse the SSHSIG carrier: {error}",
            )
        return None

    @classmethod
    def _validate_allowed_signers_policy(cls, path: Path) -> VerificationResult | None:
        try:
            policy = cls._read_bounded(path, MAX_ALLOWED_SIGNERS_BYTES, "allowed signers policy")
            for line_number, raw_line in enumerate(policy.splitlines(), start=1):
                if len(raw_line) > MAX_ALLOWED_SIGNERS_LINE_BYTES:
                    raise ValueError(f"allowed signers line {line_number} exceeds policy limit")
                line = raw_line.strip()
                if not line or line.startswith(b"#"):
                    continue
                cls._validate_allowed_signers_line(line, line_number)
        except (OSError, ValueError) as error:
            return VerificationResult.failure(
                VerificationFailureReason.KEY_ALGORITHM_FORBIDDEN,
                f"software-key policy refused allowed signers: {error}",
            )
        return None

    @classmethod
    def validate_group_allowed_signers_policy(cls, path: Path) -> VerificationResult | None:
        """Refuse signer aliases that could turn one key into a v3 group quorum."""

        try:
            policy = cls._read_bounded(path, MAX_ALLOWED_SIGNERS_BYTES, "allowed signers policy")
            principals_by_key: dict[bytes, str] = {}
            for line_number, raw_line in enumerate(policy.splitlines(), start=1):
                if len(raw_line) > MAX_ALLOWED_SIGNERS_LINE_BYTES:
                    raise ValueError(f"allowed signers line {line_number} exceeds policy limit")
                line = raw_line.strip()
                if not line or line.startswith(b"#"):
                    continue
                principal_field, options, algorithm, public_blob = (
                    cls._validate_allowed_signers_line(line, line_number)
                )
                if b"cert-authority" in b",".join(options).split(b","):
                    raise ValueError(
                        f"allowed signers line {line_number} uses cert-authority, which group "
                        "authorization does not support"
                    )
                if algorithm in SOFTWARE_CERTIFICATE_ALGORITHMS:
                    raise ValueError(
                        f"allowed signers line {line_number} uses an SSH certificate, which "
                        "group authorization does not support"
                    )
                try:
                    principal = principal_field.decode("ascii")
                except UnicodeDecodeError as error:
                    raise ValueError(
                        f"allowed signers line {line_number} has a non-ASCII principal"
                    ) from error
                if PRINCIPAL.fullmatch(principal) is None:
                    raise ValueError(
                        f"allowed signers line {line_number} must name exactly one explicit "
                        "principal for group authorization"
                    )
                previous = principals_by_key.setdefault(public_blob, principal)
                if previous != principal:
                    raise ValueError(
                        "allowed signers maps the same public key material to distinct "
                        f'principals "{previous}" and "{principal}"'
                    )
        except (OSError, ValueError) as error:
            return VerificationResult.failure(
                VerificationFailureReason.KEY_ALGORITHM_FORBIDDEN,
                f"group signer policy refused allowed signers: {error}",
            )
        return None

    @classmethod
    def _validate_allowed_signers_line(
        cls, line: bytes, line_number: int
    ) -> tuple[bytes, tuple[bytes, ...], str, bytes]:
        fields = line.split()
        candidates: list[tuple[int, str, bytes]] = []
        for index in range(1, len(fields)):
            try:
                blob = base64.b64decode(fields[index], validate=True)
                algorithm = cls._public_blob_algorithm(blob)
            except (binascii.Error, UnicodeDecodeError, ValueError):
                continue
            candidates.append((index, algorithm, blob))
        if len(candidates) != 1:
            raise ValueError(f"allowed signers line {line_number} has no unique SSH public key")
        index, algorithm, blob = candidates[0]
        if index < MIN_ALLOWED_SIGNERS_KEY_INDEX:
            raise ValueError(f"allowed signers line {line_number} omits its principal or key type")
        try:
            declared_algorithm = fields[index - 1].decode("ascii")
        except UnicodeDecodeError as error:
            detail = f"allowed signers line {line_number} has a non-ASCII key type"
            raise ValueError(detail) from error
        if declared_algorithm != algorithm:
            raise ValueError(
                f"allowed signers line {line_number} key type does not match its public blob"
            )
        cls._require_software_algorithm(algorithm, f"allowed signers line {line_number}")
        return fields[0], tuple(fields[1 : index - 1]), algorithm, blob

    @staticmethod
    def _read_bounded(path: Path, limit: int, carrier: str) -> bytes:
        with path.open("rb") as stream:
            data = stream.read(limit + 1)
        if len(data) > limit:
            raise ValueError(f"{carrier} exceeds {limit} bytes")
        return data

    @staticmethod
    def _decode_armor(data: bytes, header: bytes, footer: bytes, limit: int) -> bytes:
        lines = data.splitlines()
        if len(lines) < MIN_ARMOR_LINES or lines[0] != header or lines[-1] != footer:
            raise ValueError("carrier does not have the required armor")
        try:
            decoded = base64.b64decode(b"".join(lines[1:-1]), validate=True)
        except binascii.Error as error:
            raise ValueError("carrier armor is not canonical base64") from error
        if len(decoded) > limit:
            raise ValueError(f"decoded carrier exceeds {limit} bytes")
        return decoded

    @classmethod
    def _public_blob_algorithm(cls, blob: bytes) -> str:
        reader = _BinaryReader(blob)
        return cls._decode_algorithm(reader.read_string())

    @staticmethod
    def _decode_algorithm(value: bytes) -> str:
        try:
            algorithm = value.decode("ascii")
        except UnicodeDecodeError as error:
            raise ValueError("key algorithm is not ASCII") from error
        if not algorithm or len(algorithm) > MAX_KEY_ALGORITHM_BYTES:
            raise ValueError("key algorithm has invalid length")
        return algorithm

    @staticmethod
    def _require_software_algorithm(algorithm: str, carrier: str) -> None:
        if algorithm in SECURITY_KEY_ALGORITHMS:
            raise _AlgorithmPolicyError(
                f"{carrier} uses forbidden hardware security-key algorithm {algorithm}"
            )
        if algorithm not in SOFTWARE_PUBLIC_KEY_ALGORITHMS:
            raise _AlgorithmPolicyError(
                f"{carrier} uses unsupported software key algorithm {algorithm}"
            )

    @staticmethod
    def _require_signature_algorithm(signature_algorithm: str, public_algorithm: str) -> None:
        if signature_algorithm in SECURITY_KEY_ALGORITHMS:
            detail = (
                "SSHSIG signature uses forbidden hardware security-key algorithm "
                f"{signature_algorithm}"
            )
            raise _AlgorithmPolicyError(detail)
        if signature_algorithm not in SOFTWARE_SIGNATURE_ALGORITHMS:
            raise _AlgorithmPolicyError(
                f"SSHSIG signature uses unsupported software algorithm {signature_algorithm}"
            )
        base_public_algorithm = public_algorithm.removesuffix("-cert-v01@openssh.com")
        compatible = signature_algorithm == base_public_algorithm or (
            base_public_algorithm == "ssh-rsa"
            and signature_algorithm in {"rsa-sha2-256", "rsa-sha2-512"}
        )
        if not compatible:
            raise _AlgorithmPolicyError("SSHSIG public key and signature algorithms do not match")

    @staticmethod
    def _verification_time(evaluation_time: object) -> str | VerificationResult:
        if evaluation_time is None:
            return VerificationResult.failure(
                VerificationFailureReason.EVALUATION_TIME_INVALID,
                "signature verification requires a caller-supplied UTC evaluation instant",
            )
        if (
            not isinstance(evaluation_time, datetime)
            or evaluation_time.tzinfo is None
            or evaluation_time.utcoffset() != timedelta(0)
        ):
            return VerificationResult.failure(
                VerificationFailureReason.EVALUATION_TIME_INVALID,
                "signature verification evaluation time must be timezone-aware UTC",
            )
        return evaluation_time.strftime("%Y%m%d%H%M%S")

    @staticmethod
    def _read_signature(path: Path) -> bytes | VerificationResult:
        try:
            with path.open("rb") as stream:
                signature = stream.read(MAX_SIGNATURE_BYTES + 1)
            if len(signature) > MAX_SIGNATURE_BYTES:
                return VerificationResult.failure(
                    VerificationFailureReason.SIGNATURE_MALFORMED,
                    f"signature file exceeds {MAX_SIGNATURE_BYTES} bytes: {path}",
                )
            return signature
        except FileNotFoundError:
            return VerificationResult.failure(
                VerificationFailureReason.SIGNATURE_FILE_MISSING,
                f"signature file is missing: {path}",
            )
        except OSError as error:
            return VerificationResult.failure(
                VerificationFailureReason.SIGNATURE_FILE_UNREADABLE,
                f"signature file is unreadable: {path}: {error}",
            )

    @staticmethod
    def _has_armor(signature: bytes) -> bool:
        lines = signature.splitlines()
        return (
            len(lines) >= MIN_ARMOR_LINES
            and lines[0] == SSH_SIGNATURE_HEADER
            and lines[-1] == SSH_SIGNATURE_FOOTER
            and all(lines)
        )

    @staticmethod
    def _decode_output(completed: subprocess.CompletedProcess[bytes]) -> tuple[str, str]:
        try:
            return completed.stdout.decode("utf-8"), completed.stderr.decode("utf-8")
        except UnicodeDecodeError as error:
            raise _InvocationError(
                VerificationFailureReason.OUTPUT_UNPARSEABLE,
                "ssh-keygen emitted output that was not UTF-8",
            ) from error

    @staticmethod
    def _parse_principals(stdout: str, stderr: str) -> list[str]:
        if stderr:
            raise _InvocationError(
                VerificationFailureReason.OUTPUT_UNPARSEABLE,
                "ssh-keygen emitted unexpected diagnostics while finding principals",
            )
        principals = stdout.splitlines()
        invalid_principal = any(PRINCIPAL.fullmatch(principal) is None for principal in principals)
        if not principals or invalid_principal:
            raise _InvocationError(
                VerificationFailureReason.OUTPUT_UNPARSEABLE,
                "ssh-keygen returned an invalid principal list",
            )
        return list(dict.fromkeys(principals))

    def _parse_verified_principal(
        self,
        expected_principal: str,
        stdout: str,
        stderr: str,
    ) -> VerificationResult:
        lines = stdout.splitlines()
        pattern = VERIFIED_OUTPUT_BY_NAMESPACE[self.namespace]
        match = pattern.fullmatch(lines[0]) if len(lines) == 1 and not stderr else None
        if match is None or match.group("principal") != expected_principal:
            return VerificationResult.failure(
                VerificationFailureReason.OUTPUT_UNPARSEABLE,
                "ssh-keygen returned success with unparseable signer output",
            )
        return VerificationResult.success(match.group("principal"))

    @classmethod
    def _failed_process(
        cls,
        completed: subprocess.CompletedProcess[bytes],
        stdout: str,
        stderr: str,
    ) -> VerificationResult:
        output = "\n".join(part.strip() for part in (stdout, stderr) if part.strip())
        lowered = output.lower()
        if any(
            marker in lowered
            for marker in (
                "key has expired",
                "not yet valid",
                "outside validity",
                "outside its validity",
                "valid-after",
                "valid-before",
            )
        ):
            reason = VerificationFailureReason.SIGNER_OUTSIDE_VALIDITY_WINDOW
        elif any(
            marker in lowered
            for marker in (
                "couldn't parse signature",
                "invalid format",
                "invalid signature file",
                "missing ssh signature",
            )
        ):
            reason = VerificationFailureReason.SIGNATURE_MALFORMED
        elif any(
            marker in lowered
            for marker in (
                "signature verification failed",
                "incorrect signature",
                "namespace does not match",
            )
        ):
            reason = VerificationFailureReason.SIGNATURE_INVALID
        elif lowered in {
            "no principal matched.",
            "could not verify signature.\nno principal matched.",
        }:
            reason = VerificationFailureReason.NO_MATCHING_PRINCIPAL
        else:
            reason = VerificationFailureReason.TOOL_FAILURE
        detail = cls._failure_detail(completed.returncode, stdout, stderr)
        return VerificationResult.failure(reason, detail)

    @staticmethod
    def _failure_detail(returncode: int, stdout: str, stderr: str) -> str:
        output = "\n".join(part.strip() for part in (stdout, stderr) if part.strip())
        if not output:
            return f"ssh-keygen exited with status {returncode} without diagnostics"
        return f"ssh-keygen exited with status {returncode}: {output}"
