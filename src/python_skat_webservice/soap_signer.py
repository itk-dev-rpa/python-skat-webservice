"""This module is responsible for signing SOAP envelopes."""

import uuid
from datetime import datetime, timedelta

from lxml import etree
import xmlsec


NSMAP = {
    'soap': "http://schemas.xmlsoap.org/soap/envelope/",
    'wsse': "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd",
    'wsu': "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd",
    'ds': "http://www.w3.org/2000/09/xmldsig#"
}


class SOAPSigner:
    """The SOAPSigner class is responsible for signing SOAP envelopes
    with a certificate.
    It adds a timestamp, binary security token and signatures for both
    and a signature for the body.
    """
    _cert: bytes
    _key: bytes

    def __init__(self, cert_file: str | bytes, key_file: str | bytes):
        """Create a new SOAPSigner with the given certificate and key files.

        Args:
            cert_file: The public certificate in pem format.
            key_file: The private certificate key in pem format.
        """
        if isinstance(cert_file, str):
            with open(cert_file, 'rb') as file:
                self._cert = file.read()
        elif isinstance(cert_file, bytes):
            self._cert = cert_file
        else:
            raise TypeError("Certificate file must be a path string or bytes object.")

        if isinstance(key_file, str):
            with open(key_file, 'rb') as file:
                self._key = file.read()
        elif isinstance(key_file, bytes):
            self._key = key_file
        else:
            raise TypeError("Key file must be a path string or bytes object.")


    def sign_soap_envelope(self, envelope: etree.ElementBase):
        """Sign the given SOAP envelope with the SOAPSigner's
        certificate.
        Add a timestamp that's valid from now and 5 minutes forward.

        Args:
            envelope: The SOAP envelope to sign.

        Raises:
            ValueError: If no SOAP body is found in the envelope.

        Returns:
            The signed envelope.
        """
        created = datetime.now()
        expires = created + timedelta(minutes=5)
        created_str = created.strftime('%Y-%m-%dT%H:%M:%SZ')
        expires_str = expires.strftime('%Y-%m-%dT%H:%M:%SZ')

        timestamp_id = "Timestamp-" + str(uuid.uuid4())
        token_id = "SecurityToken-" + str(uuid.uuid4())

        # Find or create the Header
        header = envelope.find(f".//{{{NSMAP['soap']}}}Header")
        if header is None:
            header = etree.Element(f"{{{NSMAP['soap']}}}Header")
            envelope.insert(0, header)

        body = envelope.find(f".//{{{NSMAP['soap']}}}Body")
        if body is None:
            raise ValueError("SOAP Body not found")

        # Ensure Body has wsu:Id for signing
        body_id = "Body-" + str(uuid.uuid4())
        body.attrib[f"{{{NSMAP['wsu']}}}Id"] = body_id

        # Add <wsse:Security>
        security = etree.SubElement(header, f"{{{NSMAP['wsse']}}}Security", attrib={
            f"{{{NSMAP['soap']}}}mustUnderstand": "1"
        })

        # Add <wsu:Timestamp>
        timestamp = etree.SubElement(security, f"{{{NSMAP['wsu']}}}Timestamp", attrib={
            f"{{{NSMAP['wsu']}}}Id": timestamp_id
        })
        etree.SubElement(timestamp, f"{{{NSMAP['wsu']}}}Created").text = created_str
        etree.SubElement(timestamp, f"{{{NSMAP['wsu']}}}Expires").text = expires_str

        # Add <wsse:BinarySecurityToken>
        binary_token = etree.SubElement(security, f"{{{NSMAP['wsse']}}}BinarySecurityToken", attrib={
            "EncodingType": "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary",
            "ValueType": "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3",
            f"{{{NSMAP['wsu']}}}Id": token_id
        })

        # Extract certificate
        delimiters = ("-----BEGIN CERTIFICATE-----", "-----END CERTIFICATE-----")
        cert_text = self._cert.decode()
        if delimiters[0] not in cert_text or delimiters[1] not in cert_text:
            raise ValueError(f"Couldn't read certificate. Make sure '{delimiters[0]}' and '{delimiters[1]}' is in the file.")
        binary_token.text = cert_text.split(delimiters[0], 1)[1].split(delimiters[1], 1)[0].replace("\n", "")

        # Add <ds:Signature>
        signature = xmlsec.template.create(
            envelope,
            xmlsec.Transform.EXCL_C14N,
            xmlsec.Transform.RSA_SHA1,
            ns='ds'
        )
        security.append(signature)

        # Add references to Timestamp, Body, BinarySecurityToken
        for uri in [timestamp_id, body_id, token_id]:
            ref = xmlsec.template.add_reference(signature, xmlsec.Transform.SHA1, uri="#" + uri)
            xmlsec.template.add_transform(ref, xmlsec.Transform.EXCL_C14N)

        # KeyInfo and SecurityTokenReference
        key_info = xmlsec.template.ensure_key_info(signature)
        sec_token_ref = etree.SubElement(
            key_info,
            f"{{{NSMAP['wsse']}}}SecurityTokenReference"
        )
        etree.SubElement(
            sec_token_ref,
            f"{{{NSMAP['wsse']}}}Reference",
            URI="#" + token_id,
            ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3"
        )

        # Register wsu:Id as an ID attribute so xmlsec can resolve them
        xmlsec.tree.add_ids(envelope, ["Id"])

        # Sign
        ctx = xmlsec.SignatureContext()
        ctx.key = xmlsec.Key.from_memory(self._key, xmlsec.KeyFormat.PEM)
        ctx.sign(signature)

        return envelope
