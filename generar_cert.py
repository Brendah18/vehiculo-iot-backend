from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import datetime

key = rsa.generate_private_key(65537, 2048)
name = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, 'localhost')])

cert = x509.CertificateBuilder().subject_name(
    name
).issuer_name(
    name
).public_key(
    key.public_key()
).serial_number(
    x509.random_serial_number()
).not_valid_before(
    datetime.datetime.now(datetime.timezone.utc)
).not_valid_after(
    datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365)
).sign(key, hashes.SHA256())

with open('key.pem', 'wb') as f:
    f.write(key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption()
    ))

with open('cert.pem', 'wb') as f:
    f.write(cert.public_bytes(serialization.Encoding.PEM))

print("Certificados creados correctamente")
