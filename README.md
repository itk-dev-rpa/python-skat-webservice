# python-skat-webservice

This Python library is used to call the Danish SKAT eIndkomst SOAP webservice.

<https://info.skat.dk/data.aspx?oid=4247>

Currently the following services are supported:

- IndkomstOplysningPersonHent

## Prerequisites

### Service agreement

Before using the webservices you need to setup a service agreement with SKAT.

Read more here: <https://info.skat.dk/data.aspx?oid=2248828>

In the service agreement you will receive 3 codes that is used when calling the services:

- AbonnentTypeKode
- AbonnementTypeKode
- AdgangFormaalTypeKode

All three codes are numbers 3-5 digits long.

### Certificates

The OCES3 P12 certificate you use to register with SKAT needs to be converted to two PEM
certificates before being used in the code. You can use openssl for this:

```bash
openssl pkcs12 -in Certificate.p12 -out Certificate.crt.pem -clcerts -nokeys
openssl pkcs12 -in Certificate.p12 -out Certificate.key.pem -nocerts -nodes
```

## IndkomstOplysningPersonHent

### Usage

The IndkomstOplysningPersonHent allows you to get income information about a single person for a given
range of months.

```python
from python_skat_webservice.soap_signer import SOAPSigner
from python_skat_webservice.common import CallerInfo
from python_skat_webservice.soap_signer import SOAPSigner
from python_skat_webservice.indkomst_oplysning_person_hent import search_income

if __name__ == '__main__':
    signer = SOAPSigner("something/certifcate.crt.pem", "something/certificate.key.pem")

    caller = CallerInfo(
        se_number="12345678", # Your company's SE number
        abonnent_type_kode="123",
        abonnement_type_kode="4567",
        adgang_formaal_type_kode="456",
        caller_id="My caller id" # Any id to identify you with SKAT. Can be anything.
    )

    result = search_income(
        cpr="1234567890",
        month_from="202401", # yyyymm
        month_to="202401", # yyyymm
        transaction_id="My transaction id", # Any id to identify the transaction. Can be anything.
        caller_info=caller,
        soap_signer=signer
    )

    print(result)
```

### Output

The output is a SOAP xml envelope with the search results in the body.
The body is structured something like this:

```text
Person
├── Company
│   ├── Period
│   │   ├── Form
│   │   │   ├── Form ID
│   │   │   ├── Field
│   │   │   │   ├── Field ID
│   │   │   │   ├── Type
│   │   │   │   └── Value
│   │   │   └── Field
│   │   │       └── ...
│   │   ├── Form
│   │   │   └── ...
│   │   └── ...
│   └── Period
│       └── ...
└── Company
    └── ...
```

The income information is first grouped by the paying company.
Then by period (usually by month).
Then in forms (blanket) with fields.

Forms can be layered so a form may contain multiple subforms.

Descriptions of the forms and fields can be found in 'underbilag 1' here: <https://info.skat.dk/data.aspx?oid=2248828&chk=220344>

Example: The form 16001 field 100000000000000057 is "A-indkomst, hvoraf der betales AM-bidrag".
