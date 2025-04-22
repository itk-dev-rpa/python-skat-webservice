from dataclasses import dataclass

@dataclass
class CallerInfo:
    """A dataclass that describes the caller of a webservice.
    caller_id: The id of the caller used to trace usage of the service. Can be anything.
    se_number: The SE-number of the caller.
    abonnent_type_kode: The AbonnentTypeKode from the service agreement.
    abonnement_type_kode: The AbonnementTypeKode from the service agreement.
    adgang_formaal_type_kode: The AdgangFormaalTypeKode from the service agreement.
    """
    caller_id: str
    se_number: str
    abonnent_type_kode: str
    abonnement_type_kode: str
    adgang_formaal_type_kode: str