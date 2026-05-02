import enum


class Stream(str, enum.Enum):
    """
    Commercial counterparty taxonomy. The stream value is part of the
    canonical hash payload, so values must never be renamed in place —
    new streams may be added, but existing values are immutable for
    chain-verification reasons.
    """

    REIT = "reit"
    LENDER = "lender"
    INDIVIDUAL = "individual"
    INSURER = "insurer"
    GOVERNMENT = "government"
    FAMILY_OFFICE = "family_office"
    DEVELOPER = "developer"


class KycStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
