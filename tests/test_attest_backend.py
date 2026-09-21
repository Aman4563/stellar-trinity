import base64
import shutil
import struct
import subprocess
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path

import pytest
from tools.attest.backend import (
    SignatureBackendError,
    VerificationFailureReason,
    VerificationResult,
)
from tools.attest.backend_ssh import SOFTWARE_KEY_ALGORITHMS, SshKeygenBackend

FIXTURES = Path(__file__).parent / "fixtures" / "attest"
ALLOWED_SIGNERS = FIXTURES / "allowed_signers"
VALID_KEY = "TEST_ONLY_valid_ed25519"
UNTRUSTED_KEY = "TEST_ONLY_untrusted_ed25519"
EXPIRED_KEY = "TEST_ONLY_expired_ed25519"
PAYLOAD = b'{"artifact":"sha256:0123456789abcdef","predicateType":"trinity.test"}\n'
EVALUATION_TIME = datetime(2027, 1, 1, tzinfo=UTC)
OUTSIDE_VALIDITY_TIME = datetime(2029, 1, 1, tzinfo=UTC)
VALID_VERIFICATION_LINE = (
    b'Good "trinity.attestation.v1" signature for valid-signer@trinity.test with '
    b"ED25519 key SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\n"
)
HARDWARE_KEY_ALGORITHMS = (
    "sk-ssh-ed25519@openssh.com",
    "sk-ssh-ed25519-cert-v01@openssh.com",
    "sk-ecdsa-sha2-nistp256@openssh.com",
    "sk-ecdsa-sha2-nistp256-cert-v01@openssh.com",
)


@pytest.fixture
def ssh_keygen_path() -> Path:
    executable = shutil.which("ssh-keygen")
    if executable is None:
        pytest.skip("ssh-keygen is required for backend integration tests")
    return Path(executable).resolve()


@pytest.fixture
def backend(ssh_keygen_path: Path) -> SshKeygenBackend:
    return SshKeygenBackend(executable=ssh_keygen_path, timeout_seconds=5.0)


def copy_private_key(tmp_path: Path, name: str) -> Path:
    target = tmp_path / name
    target.write_bytes((FIXTURES / name).read_bytes())
    target.chmod(0o600)
    return target


def sign_to_file(
    backend: SshKeygenBackend,
    tmp_path: Path,
    key_name: str,
    payload: bytes = PAYLOAD,
) -> Path:
    key_path = copy_private_key(tmp_path, key_name)
    signature_path = tmp_path / f"{key_name}.sig"
    signature_path.write_bytes(backend.sign(payload, key_path=key_path))
    return signature_path


def assert_failure(result: VerificationResult, reason: VerificationFailureReason) -> None:
    assert result.verified is False
    assert result.principal is None
    assert result.reason is reason
    assert result.detail


def staged_signature(tmp_path: Path) -> Path:
    signature_path = tmp_path / "staged.sig"
    signature_path.write_bytes(signature_with_algorithms("ssh-ed25519", "ssh-ed25519"))
    return signature_path


def ssh_string(value: bytes) -> bytes:
    return struct.pack(">I", len(value)) + value


def public_blob(algorithm: str, material: bytes = b"test-public-fields") -> bytes:
    return ssh_string(algorithm.encode("ascii")) + material


def allowed_signer_line(
    principal: str,
    *,
    material: bytes = b"test-public-fields",
    options: str = "",
    algorithm: str = "ssh-ed25519",
) -> str:
    encoded = base64.b64encode(public_blob(algorithm, material)).decode("ascii")
    option_field = f" {options}" if options else ""
    return f"{principal}{option_field} {algorithm} {encoded}\n"


def armor(header: bytes, footer: bytes, payload: bytes) -> bytes:
    return header + b"\n" + base64.b64encode(payload) + b"\n" + footer + b"\n"


def private_key_with_public_algorithm(algorithm: str) -> bytes:
    payload = b"openssh-key-v1\x00"
    payload += ssh_string(b"none") + ssh_string(b"none") + ssh_string(b"")
    payload += struct.pack(">I", 1) + ssh_string(public_blob(algorithm))
    return armor(
        b"-----BEGIN OPENSSH PRIVATE KEY-----",
        b"-----END OPENSSH PRIVATE KEY-----",
        payload,
    )


def signature_with_algorithms(public_algorithm: str, signature_algorithm: str) -> bytes:
    signature_blob = ssh_string(signature_algorithm.encode("ascii")) + ssh_string(b"signature")
    payload = b"SSHSIG" + struct.pack(">I", 1)
    payload += ssh_string(public_blob(public_algorithm))
    payload += ssh_string(b"trinity.attestation.v1")
    payload += ssh_string(b"") + ssh_string(b"sha512") + ssh_string(signature_blob)
    return armor(
        b"-----BEGIN SSH SIGNATURE-----",
        b"-----END SSH SIGNATURE-----",
        payload,
    )


def mock_verification_processes(
    monkeypatch: pytest.MonkeyPatch,
    *,
    verification_stdout: bytes,
    verification_stderr: bytes = b"",
) -> None:
    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        assert kwargs["env"] == {"LC_ALL": "C"}
        if "find-principals" in argv:
            stdout = b"valid-signer@trinity.test\n"
        elif "verify" in argv:
            stdout = verification_stdout
        else:
            stdout = b""
        stderr = verification_stderr if "verify" in argv else b""
        return subprocess.CompletedProcess(argv, 0, stdout=stdout, stderr=stderr)

    monkeypatch.setattr(subprocess, "run", fake_run)


def test_verify_fails_when_ssh_keygen_is_absent(
    backend: SshKeygenBackend,
    tmp_path: Path,
) -> None:
    signature_path = sign_to_file(backend, tmp_path, VALID_KEY)
    absent_backend = SshKeygenBackend(executable=tmp_path / "missing-ssh-keygen")

    result = absent_backend.verify(
        PAYLOAD,
        signature_path=signature_path,
        allowed_signers_path=ALLOWED_SIGNERS,
        evaluation_time=EVALUATION_TIME,
    )

    assert_failure(result, VerificationFailureReason.TOOL_ABSENT)


@pytest.mark.parametrize("algorithm", HARDWARE_KEY_ALGORITHMS)
def test_sign_refuses_hardware_key_public_header_before_subprocess(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    algorithm: str,
) -> None:
    key_path = tmp_path / "forged-armored-private-key"
    key_path.write_bytes(private_key_with_public_algorithm(algorithm))

    def physical_discovery_forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        pytest.fail("hardware tooling or subprocess discovery was invoked")

    monkeypatch.setattr(subprocess, "run", physical_discovery_forbidden)
    signing_backend = SshKeygenBackend(executable=tmp_path / "pinned-ssh-keygen")

    with pytest.raises(SignatureBackendError) as raised:
        signing_backend.sign(PAYLOAD, key_path=key_path)

    assert raised.value.reason is VerificationFailureReason.KEY_ALGORITHM_FORBIDDEN
    assert "forbidden hardware security-key algorithm" in raised.value.detail


@pytest.mark.parametrize("algorithm", sorted(SOFTWARE_KEY_ALGORITHMS))
def test_private_key_policy_explicitly_accepts_supported_software_algorithms(
    tmp_path: Path,
    algorithm: str,
) -> None:
    key_path = tmp_path / algorithm
    key_path.write_bytes(private_key_with_public_algorithm(algorithm))

    SshKeygenBackend._validate_private_key_policy(key_path)


@pytest.mark.parametrize("algorithm", HARDWARE_KEY_ALGORITHMS)
def test_verify_refuses_hardware_algorithm_inside_sshsig_before_subprocess(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    algorithm: str,
) -> None:
    signature_path = tmp_path / "forged-header.sig"
    signature_path.write_bytes(signature_with_algorithms(algorithm, "ssh-ed25519"))

    def physical_discovery_forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        pytest.fail("hardware tooling or subprocess discovery was invoked")

    monkeypatch.setattr(subprocess, "run", physical_discovery_forbidden)
    verification_backend = SshKeygenBackend(executable=tmp_path / "pinned-ssh-keygen")

    result = verification_backend.verify(
        PAYLOAD,
        signature_path=signature_path,
        allowed_signers_path=ALLOWED_SIGNERS,
        evaluation_time=EVALUATION_TIME,
    )

    assert_failure(result, VerificationFailureReason.KEY_ALGORITHM_FORBIDDEN)
    assert "forbidden hardware security-key algorithm" in result.detail


@pytest.mark.parametrize("algorithm", HARDWARE_KEY_ALGORITHMS)
def test_verify_refuses_hardware_signature_algorithm_with_software_public_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    algorithm: str,
) -> None:
    signature_path = tmp_path / "hardware-signature-field.sig"
    signature_path.write_bytes(signature_with_algorithms("ssh-ed25519", algorithm))

    def physical_discovery_forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        pytest.fail("hardware tooling or subprocess discovery was invoked")

    monkeypatch.setattr(subprocess, "run", physical_discovery_forbidden)
    verification_backend = SshKeygenBackend(executable=tmp_path / "pinned-ssh-keygen")

    result = verification_backend.verify(
        PAYLOAD,
        signature_path=signature_path,
        allowed_signers_path=ALLOWED_SIGNERS,
        evaluation_time=EVALUATION_TIME,
    )

    assert_failure(result, VerificationFailureReason.KEY_ALGORITHM_FORBIDDEN)
    assert "forbidden hardware security-key algorithm" in result.detail


@pytest.mark.parametrize("algorithm", HARDWARE_KEY_ALGORITHMS)
def test_verify_refuses_hardware_algorithm_in_allowed_signers_before_subprocess(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    algorithm: str,
) -> None:
    signature_path = tmp_path / "software.sig"
    signature_path.write_bytes(signature_with_algorithms("ssh-ed25519", "ssh-ed25519"))
    allowed_signers = tmp_path / "allowed_signers"
    encoded = base64.b64encode(public_blob(algorithm)).decode("ascii")
    allowed_signers.write_text(f"signer@example.test {algorithm} {encoded}\n", encoding="ascii")

    def physical_discovery_forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        pytest.fail("hardware tooling or subprocess discovery was invoked")

    monkeypatch.setattr(subprocess, "run", physical_discovery_forbidden)
    verification_backend = SshKeygenBackend(executable=tmp_path / "pinned-ssh-keygen")

    result = verification_backend.verify(
        PAYLOAD,
        signature_path=signature_path,
        allowed_signers_path=allowed_signers,
        evaluation_time=EVALUATION_TIME,
    )

    assert_failure(result, VerificationFailureReason.KEY_ALGORITHM_FORBIDDEN)
    assert "forbidden hardware security-key algorithm" in result.detail


def test_group_policy_refuses_one_key_as_producer_and_approver_aliases_before_subprocess(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    allowed_signers = tmp_path / "allowed_signers"
    allowed_signers.write_text(
        allowed_signer_line("producer@trinity.test") + allowed_signer_line("approver@trinity.test"),
        encoding="ascii",
    )

    def signing_verification_forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        pytest.fail("signing verification subprocess was invoked")

    monkeypatch.setattr(subprocess, "run", signing_verification_forbidden)
    result = SshKeygenBackend.validate_group_allowed_signers_policy(allowed_signers)

    assert result is not None
    assert_failure(result, VerificationFailureReason.KEY_ALGORITHM_FORBIDDEN)
    assert "same public key material" in result.detail
    assert "producer@trinity.test" in result.detail
    assert "approver@trinity.test" in result.detail


def test_group_policy_refuses_one_key_as_two_threshold_principals(tmp_path: Path) -> None:
    allowed_signers = tmp_path / "allowed_signers"
    allowed_signers.write_text(
        allowed_signer_line("producer-a@trinity.test")
        + allowed_signer_line("producer-b@trinity.test"),
        encoding="ascii",
    )

    result = SshKeygenBackend.validate_group_allowed_signers_policy(allowed_signers)

    assert result is not None
    assert_failure(result, VerificationFailureReason.KEY_ALGORITHM_FORBIDDEN)
    assert "distinct principals" in result.detail


def test_group_policy_refuses_comma_separated_aliases_on_one_line(tmp_path: Path) -> None:
    allowed_signers = tmp_path / "allowed_signers"
    allowed_signers.write_text(
        allowed_signer_line("producer@trinity.test,approver@trinity.test"),
        encoding="ascii",
    )

    result = SshKeygenBackend.validate_group_allowed_signers_policy(allowed_signers)

    assert result is not None
    assert_failure(result, VerificationFailureReason.KEY_ALGORITHM_FORBIDDEN)
    assert "exactly one explicit principal" in result.detail


@pytest.mark.parametrize("principal", ["*@trinity.test", "operator?@trinity.test"])
def test_group_policy_refuses_wildcard_principals(tmp_path: Path, principal: str) -> None:
    allowed_signers = tmp_path / "allowed_signers"
    allowed_signers.write_text(allowed_signer_line(principal), encoding="ascii")

    result = SshKeygenBackend.validate_group_allowed_signers_policy(allowed_signers)

    assert result is not None
    assert_failure(result, VerificationFailureReason.KEY_ALGORITHM_FORBIDDEN)
    assert "exactly one explicit principal" in result.detail


@pytest.mark.parametrize(
    ("options", "algorithm", "expected"),
    [
        ("cert-authority", "ssh-ed25519", "cert-authority"),
        ("", "ssh-ed25519-cert-v01@openssh.com", "SSH certificate"),
    ],
)
def test_group_policy_refuses_ca_and_certificate_forms_without_changing_v2_policy(
    tmp_path: Path,
    options: str,
    algorithm: str,
    expected: str,
) -> None:
    allowed_signers = tmp_path / "allowed_signers"
    allowed_signers.write_text(
        allowed_signer_line("signer@trinity.test", options=options, algorithm=algorithm),
        encoding="ascii",
    )

    assert SshKeygenBackend._validate_allowed_signers_policy(allowed_signers) is None
    result = SshKeygenBackend.validate_group_allowed_signers_policy(allowed_signers)

    assert result is not None
    assert_failure(result, VerificationFailureReason.KEY_ALGORITHM_FORBIDDEN)
    assert expected in result.detail


def test_group_policy_accepts_distinct_software_keys_for_normal_quorum(tmp_path: Path) -> None:
    allowed_signers = tmp_path / "allowed_signers"
    allowed_signers.write_text(
        allowed_signer_line("producer@trinity.test", material=b"producer-key")
        + allowed_signer_line("approver@trinity.test", material=b"approver-key"),
        encoding="ascii",
    )

    assert SshKeygenBackend.validate_group_allowed_signers_policy(allowed_signers) is None


def test_verify_fails_when_signature_file_is_missing(
    backend: SshKeygenBackend,
    tmp_path: Path,
) -> None:
    result = backend.verify(
        PAYLOAD,
        signature_path=tmp_path / "missing.sig",
        allowed_signers_path=ALLOWED_SIGNERS,
        evaluation_time=EVALUATION_TIME,
    )

    assert_failure(result, VerificationFailureReason.SIGNATURE_FILE_MISSING)


def test_verify_fails_when_signature_armor_is_malformed(
    backend: SshKeygenBackend,
    tmp_path: Path,
) -> None:
    signature_path = sign_to_file(backend, tmp_path, VALID_KEY)
    signature_path.write_bytes(
        signature_path.read_bytes().replace(b"BEGIN SSH SIGNATURE", b"BEGIN SSH CORRUPTED", 1)
    )

    result = backend.verify(
        PAYLOAD,
        signature_path=signature_path,
        allowed_signers_path=ALLOWED_SIGNERS,
        evaluation_time=EVALUATION_TIME,
    )

    assert_failure(result, VerificationFailureReason.SIGNATURE_MALFORMED)


def test_verify_fails_when_key_has_no_allowed_principal(
    backend: SshKeygenBackend,
    tmp_path: Path,
) -> None:
    signature_path = sign_to_file(backend, tmp_path, UNTRUSTED_KEY)

    result = backend.verify(
        PAYLOAD,
        signature_path=signature_path,
        allowed_signers_path=ALLOWED_SIGNERS,
        evaluation_time=EVALUATION_TIME,
    )

    assert_failure(result, VerificationFailureReason.NO_MATCHING_PRINCIPAL)


def test_verify_fails_when_payload_does_not_match_signature(
    backend: SshKeygenBackend,
    tmp_path: Path,
) -> None:
    signature_path = sign_to_file(backend, tmp_path, VALID_KEY)
    mutated_payload = PAYLOAD.replace(b"abcdef", b"abcdeg")

    result = backend.verify(
        mutated_payload,
        signature_path=signature_path,
        allowed_signers_path=ALLOWED_SIGNERS,
        evaluation_time=EVALUATION_TIME,
    )

    assert_failure(result, VerificationFailureReason.SIGNATURE_INVALID)


def test_verify_fails_when_signer_is_expired(
    backend: SshKeygenBackend,
    tmp_path: Path,
) -> None:
    signature_path = sign_to_file(backend, tmp_path, EXPIRED_KEY)

    result = backend.verify(
        PAYLOAD,
        signature_path=signature_path,
        allowed_signers_path=ALLOWED_SIGNERS,
        evaluation_time=EVALUATION_TIME,
    )

    assert_failure(result, VerificationFailureReason.SIGNER_OUTSIDE_VALIDITY_WINDOW)


def test_verify_returns_the_allowed_principal(
    backend: SshKeygenBackend,
    tmp_path: Path,
) -> None:
    signature_path = sign_to_file(backend, tmp_path, VALID_KEY)

    result = backend.verify(
        PAYLOAD,
        signature_path=signature_path,
        allowed_signers_path=ALLOWED_SIGNERS,
        evaluation_time=EVALUATION_TIME,
    )

    assert result == VerificationResult.success("valid-signer@trinity.test")


def test_verify_requires_an_explicit_utc_evaluation_time(
    backend: SshKeygenBackend,
    tmp_path: Path,
) -> None:
    signature_path = sign_to_file(backend, tmp_path, VALID_KEY)

    result = backend.verify(
        PAYLOAD,
        signature_path=signature_path,
        allowed_signers_path=ALLOWED_SIGNERS,
    )

    assert_failure(result, VerificationFailureReason.EVALUATION_TIME_INVALID)


def test_verify_refuses_non_datetime_evaluation_input(
    backend: SshKeygenBackend,
    tmp_path: Path,
) -> None:
    signature_path = sign_to_file(backend, tmp_path, VALID_KEY)

    result = backend.verify(
        PAYLOAD,
        signature_path=signature_path,
        allowed_signers_path=ALLOWED_SIGNERS,
        evaluation_time=0,
    )

    assert_failure(result, VerificationFailureReason.EVALUATION_TIME_INVALID)


def test_verify_uses_supplied_time_instead_of_machine_clock(
    backend: SshKeygenBackend,
    tmp_path: Path,
) -> None:
    signature_path = sign_to_file(backend, tmp_path, VALID_KEY)

    result = backend.verify(
        PAYLOAD,
        signature_path=signature_path,
        allowed_signers_path=ALLOWED_SIGNERS,
        evaluation_time=OUTSIDE_VALIDITY_TIME,
    )

    assert_failure(result, VerificationFailureReason.SIGNER_OUTSIDE_VALIDITY_WINDOW)


def test_verify_time_option_is_passed_to_both_authorization_invocations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invocations: list[list[str]] = []

    def record_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        del kwargs
        invocations.append(argv)
        if "find-principals" in argv:
            stdout = b"valid-signer@trinity.test\n"
        elif "verify" in argv:
            stdout = VALID_VERIFICATION_LINE
        else:
            stdout = b""
        return subprocess.CompletedProcess(argv, 0, stdout=stdout, stderr=b"")

    monkeypatch.setattr(subprocess, "run", record_run)
    backend = SshKeygenBackend(executable=tmp_path / "pinned-ssh-keygen")

    result = backend.verify(
        PAYLOAD,
        signature_path=staged_signature(tmp_path),
        allowed_signers_path=ALLOWED_SIGNERS,
        evaluation_time=EVALUATION_TIME,
    )

    find_principals_argv = next(argv for argv in invocations if "find-principals" in argv)
    verify_argv = next(argv for argv in invocations if "verify" in argv)
    expected_option = "verify-time=20270101000000"
    assert ("-O", expected_option) in pairwise(find_principals_argv)
    assert ("-O", expected_option) in pairwise(verify_argv)
    assert result == VerificationResult.success("valid-signer@trinity.test")


def test_verify_fails_closed_on_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def time_out(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        del kwargs
        raise subprocess.TimeoutExpired(argv, 0.01)

    monkeypatch.setattr(subprocess, "run", time_out)
    backend = SshKeygenBackend(executable=tmp_path / "pinned-ssh-keygen", timeout_seconds=0.01)

    result = backend.verify(
        PAYLOAD,
        signature_path=staged_signature(tmp_path),
        allowed_signers_path=ALLOWED_SIGNERS,
        evaluation_time=EVALUATION_TIME,
    )

    assert_failure(result, VerificationFailureReason.TOOL_TIMEOUT)


def test_verify_refuses_hostile_success_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_verification_processes(
        monkeypatch,
        verification_stdout=b"Signature verified successfully\n",
    )
    backend = SshKeygenBackend(executable=tmp_path / "pinned-ssh-keygen")

    result = backend.verify(
        PAYLOAD,
        signature_path=staged_signature(tmp_path),
        allowed_signers_path=ALLOWED_SIGNERS,
        evaluation_time=EVALUATION_TIME,
    )

    assert_failure(result, VerificationFailureReason.OUTPUT_UNPARSEABLE)


def test_verify_refuses_success_output_for_wrong_principal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_verification_processes(
        monkeypatch,
        verification_stdout=VALID_VERIFICATION_LINE.replace(
            b"valid-signer@trinity.test",
            b"wrong-signer@trinity.test",
        ),
    )
    backend = SshKeygenBackend(executable=tmp_path / "pinned-ssh-keygen")

    result = backend.verify(
        PAYLOAD,
        signature_path=staged_signature(tmp_path),
        allowed_signers_path=ALLOWED_SIGNERS,
        evaluation_time=EVALUATION_TIME,
    )

    assert_failure(result, VerificationFailureReason.OUTPUT_UNPARSEABLE)


def test_verify_refuses_trailing_output_after_valid_line(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_verification_processes(
        monkeypatch,
        verification_stdout=VALID_VERIFICATION_LINE + b"attacker-controlled trailing line\n",
    )
    backend = SshKeygenBackend(executable=tmp_path / "pinned-ssh-keygen")

    result = backend.verify(
        PAYLOAD,
        signature_path=staged_signature(tmp_path),
        allowed_signers_path=ALLOWED_SIGNERS,
        evaluation_time=EVALUATION_TIME,
    )

    assert_failure(result, VerificationFailureReason.OUTPUT_UNPARSEABLE)


def test_verify_refuses_non_utf8_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_verification_processes(monkeypatch, verification_stdout=b"\xff")
    backend = SshKeygenBackend(executable=tmp_path / "pinned-ssh-keygen")

    result = backend.verify(
        PAYLOAD,
        signature_path=staged_signature(tmp_path),
        allowed_signers_path=ALLOWED_SIGNERS,
        evaluation_time=EVALUATION_TIME,
    )

    assert_failure(result, VerificationFailureReason.OUTPUT_UNPARSEABLE)


def test_sign_reports_temporary_file_cleanup_failure(
    backend: SshKeygenBackend,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    key_path = copy_private_key(tmp_path, VALID_KEY)

    def fail_cleanup(path: Path) -> None:
        del path
        raise OSError("injected cleanup failure")

    monkeypatch.setattr(shutil, "rmtree", fail_cleanup)

    with pytest.raises(SignatureBackendError) as raised:
        backend.sign(PAYLOAD, key_path=key_path)

    assert raised.value.reason is VerificationFailureReason.TEMPORARY_FILE_CLEANUP_FAILURE


def test_pinned_executable_ignores_hostile_ssh_keygen_earlier_in_path(
    backend: SshKeygenBackend,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    signature_path = sign_to_file(backend, tmp_path, VALID_KEY)
    hostile_directory = tmp_path / "hostile-bin"
    hostile_directory.mkdir()
    marker = tmp_path / "hostile-ran"
    hostile = hostile_directory / "ssh-keygen"
    hostile.write_text(
        "#!/bin/sh\n"
        f"/usr/bin/touch '{marker}'\n"
        "printf '%s\\n' 'valid-signer@trinity.test'\n"
        "printf '%s\\n' 'Good \"trinity.attestation.v1\" signature for "
        "valid-signer@trinity.test with ED25519 key "
        "SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'\n"
        "exit 0\n"
    )
    hostile.chmod(0o755)
    monkeypatch.setenv("PATH", str(hostile_directory))

    result = backend.verify(
        PAYLOAD,
        signature_path=signature_path,
        allowed_signers_path=ALLOWED_SIGNERS,
        evaluation_time=EVALUATION_TIME,
    )

    assert result == VerificationResult.success("valid-signer@trinity.test")
    assert not marker.exists()


def test_backend_refuses_a_namespace_outside_the_closed_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delattr(subprocess, "run")

    with pytest.raises(ValueError, match="namespace"):
        SshKeygenBackend(namespace="evil")


def test_git_namespace_backend_verifies_a_git_namespace_signature(
    ssh_keygen_path: Path,
    tmp_path: Path,
) -> None:
    backend = SshKeygenBackend(executable=ssh_keygen_path, namespace="git")
    signature_path = sign_to_file(backend, tmp_path, VALID_KEY)
    allowed_signers = tmp_path / "allowed_signers"
    allowed_signers.write_text(
        ALLOWED_SIGNERS.read_text(encoding="ascii").replace(
            'namespaces="trinity.attestation.v1"', 'namespaces="trinity.attestation.v1,git"'
        ),
        encoding="ascii",
    )

    result = backend.verify(
        PAYLOAD,
        signature_path=signature_path,
        allowed_signers_path=allowed_signers,
        evaluation_time=EVALUATION_TIME,
    )

    assert result == VerificationResult.success("valid-signer@trinity.test")


def test_trinity_namespace_backend_refuses_a_git_namespace_signature(
    ssh_keygen_path: Path,
    tmp_path: Path,
) -> None:
    git_backend = SshKeygenBackend(executable=ssh_keygen_path, namespace="git")
    signature_path = sign_to_file(git_backend, tmp_path, VALID_KEY)
    backend = SshKeygenBackend(executable=ssh_keygen_path, namespace="trinity.attestation.v1")
    allowed_signers = tmp_path / "allowed_signers"
    allowed_signers.write_text(
        ALLOWED_SIGNERS.read_text(encoding="ascii").replace(
            'namespaces="trinity.attestation.v1"', 'namespaces="trinity.attestation.v1,git"'
        ),
        encoding="ascii",
    )

    result = backend.verify(
        PAYLOAD,
        signature_path=signature_path,
        allowed_signers_path=allowed_signers,
        evaluation_time=EVALUATION_TIME,
    )

    assert_failure(result, VerificationFailureReason.SIGNATURE_INVALID)


def test_default_namespace_is_unchanged_for_existing_callers(
    ssh_keygen_path: Path,
    tmp_path: Path,
) -> None:
    backend = SshKeygenBackend()
    explicit_backend = SshKeygenBackend(
        executable=ssh_keygen_path, namespace="trinity.attestation.v1"
    )
    signature_path = sign_to_file(explicit_backend, tmp_path, VALID_KEY)

    result = backend.verify(
        PAYLOAD,
        signature_path=signature_path,
        allowed_signers_path=ALLOWED_SIGNERS,
        evaluation_time=EVALUATION_TIME,
    )

    assert SshKeygenBackend.namespace == backend.namespace == "trinity.attestation.v1"
    assert result == VerificationResult.success("valid-signer@trinity.test")


def test_executable_path_must_be_absolute() -> None:
    with pytest.raises(ValueError, match="absolute"):
        SshKeygenBackend(executable="ssh-keygen")
