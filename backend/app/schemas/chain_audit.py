from pydantic import BaseModel


class ChainAuditOut(BaseModel):
    total_entries: int
    broken_links: list[str]
    chain_valid: bool
