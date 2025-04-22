from lxml import etree
import requests

from python_skat_webservice.soap_signer import SOAPSigner
from python_skat_webservice.common import CallerInfo


def create_envelope(cpr: str, month_from: str, month_to: str, transaction_id: str, caller_info: CallerInfo, soap_signer: SOAPSigner) -> str:
    """Create a SOAP envelope for calling the service.

    Args:
        cpr: The cpr-number to search on.
        month_from: The beginning of the search interval. Formatted as "yyyymm"
        month_to: The end of the search interval. Formatted as "yyyymm"
        transaction_id: An id to identify the transaction. Can be anything.
        caller_info: A CallerInfo object that describes the caller.
        soap_signer: The SOAPSigner object used to sign the call.

    Returns:
        The signed SOAP envelope as a string.
    """
    # Define namespaces
    NSMAP = {
        'soap-env': 'http://schemas.xmlsoap.org/soap/envelope/',
        'ns0': 'http://rep.oio.dk/skat.dk/eindkomst/',
        'ns1': 'http://rep.oio.dk/skat.dk/basis/kontekst/xml/schemas/2006/09/01/',
        'ns2': 'http://rep.oio.dk/skat.dk/eindkomst/class/abonnenttype/xml/schemas/20071202/',
        'ns3': 'http://rep.oio.dk/skat.dk/eindkomst/class/abonnementtype/xml/schemas/20071202/',
        'ns4': 'http://rep.oio.dk/skat.dk/eindkomst/class/adgangformaaltype/xml/schemas/20071202/',
        'ns5': 'http://rep.oio.dk/skat.dk/motor/class/virksomhed/xml/schemas/20080401/',
        'ns6': 'http://rep.oio.dk/skat.dk/eindkomst/class/indkomstoplysningadgangmedarbejderidentifikator/xml/schemas/20071202/',
        'ns7': 'http://rep.oio.dk/cpr.dk/xml/schemas/core/2005/03/18/',
        'ns8': 'http://rep.oio.dk/skat.dk/eindkomst/class/soegeaarmaanedfrakode/xml/schemas/20071202/',
        'ns9': 'http://rep.oio.dk/skat.dk/eindkomst/class/soegeaarmaanedtilkode/xml/schemas/20071202/',
        'ns10': 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd',
    }

    # Create envelope
    envelope = etree.Element(f"{{{NSMAP['soap-env']}}}Envelope", nsmap=NSMAP)

    # Create SOAP Body
    body = etree.SubElement(envelope, f"{{{NSMAP['soap-env']}}}Body")

    # Main request structure
    request = etree.SubElement(body, f"{{{NSMAP['ns0']}}}IndkomstOplysningPersonHent_I")

    # HovedOplysninger
    hoved = etree.SubElement(request, f"{{{NSMAP['ns1']}}}HovedOplysninger")
    tid = etree.SubElement(hoved, f"{{{NSMAP['ns1']}}}TransaktionIdentifikator")
    tid.text = transaction_id

    # IndkomstOplysningPersonInddata
    inddata = etree.SubElement(request, f"{{{NSMAP['ns0']}}}IndkomstOplysningPersonInddata")

    # AbonnentAdgangStruktur
    adgang = etree.SubElement(inddata, f"{{{NSMAP['ns0']}}}AbonnentAdgangStruktur")
    etree.SubElement(adgang, f"{{{NSMAP['ns2']}}}AbonnentTypeKode").text = caller_info.abonnent_type_kode
    etree.SubElement(adgang, f"{{{NSMAP['ns3']}}}AbonnementTypeKode").text = caller_info.abonnement_type_kode
    etree.SubElement(adgang, f"{{{NSMAP['ns4']}}}AdgangFormaalTypeKode").text = caller_info.adgang_formaal_type_kode

    # AbonnentStruktur
    abonnent = etree.SubElement(inddata, f"{{{NSMAP['ns0']}}}AbonnentStruktur")
    virk_struct = etree.SubElement(abonnent, f"{{{NSMAP['ns0']}}}AbonnentVirksomhedStruktur")
    virk = etree.SubElement(virk_struct, f"{{{NSMAP['ns0']}}}AbonnentVirksomhed")
    etree.SubElement(virk, f"{{{NSMAP['ns5']}}}VirksomhedSENummerIdentifikator").text = caller_info.se_number
    etree.SubElement(abonnent, f"{{{NSMAP['ns6']}}}IndkomstOplysningAdgangMedarbejderIdentifikator").text = caller_info.caller_id

    # IndkomstOplysningValg
    valg = etree.SubElement(inddata, f"{{{NSMAP['ns0']}}}IndkomstOplysningValg")
    samling = etree.SubElement(valg, f"{{{NSMAP['ns0']}}}IndkomstPersonSamling")
    soege = etree.SubElement(samling, f"{{{NSMAP['ns0']}}}PersonIndkomstSoegeStruktur")
    etree.SubElement(soege, f"{{{NSMAP['ns7']}}}PersonCivilRegistrationIdentifier").text = cpr
    lukket = etree.SubElement(soege, f"{{{NSMAP['ns0']}}}SoegeAarMaanedLukketStruktur")
    etree.SubElement(lukket, f"{{{NSMAP['ns8']}}}SoegeAarMaanedFraKode").text = month_from
    etree.SubElement(lukket, f"{{{NSMAP['ns9']}}}SoegeAarMaanedTilKode").text = month_to

    # Sign envelope and create xml string
    soap_signer.sign_soap_envelope(envelope)
    return etree.tostring(envelope, pretty_print=False, xml_declaration=True, encoding="utf-8").decode()




def search_income(cpr: str, month_from: str, month_to: str, transaction_id: str, caller_info: CallerInfo, soap_signer: SOAPSigner) -> str:
    """Search the income information on the given cpr-number for the given month interval.

    Args:
        cpr: The cpr-number to search on.
        month_from: The beginning of the search interval. Formatted as "yyyymm"
        month_to: The end of the search interval. Formatted as "yyyymm"
        transaction_id: An id to identify the transaction. Can be anything.
        caller_info: A CallerInfo object that describes the caller.
        soap_signer: The SOAPSigner object used to sign the call.

    Raises:
        HTTPError: If the server didn't return a 200 status code.

    Returns:
        The raw xml response from the server.
    """
    msg = create_envelope(cpr, month_from, month_to, transaction_id, caller_info, soap_signer)

    # Call service
    url = "https://services.extranet.skat.dk/vericert/services/IndkomstOplysningPersonHentV2ServicePort"

    headers = {
        'content-type': 'text/xml',
        'SOAPAction': 'IndkomstOplysningPersonHent'
    }

    response = requests.post(url=url, data=msg, headers=headers)
    response.raise_for_status()

    return response.text
