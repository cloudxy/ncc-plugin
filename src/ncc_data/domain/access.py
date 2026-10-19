"""Direct-interface envelopes; business changes still use the existing ChangeInput."""

from pydantic import Field

from ncc_data.domain.contracts import ChangeInput


class DirectChange(ChangeInput):
    request_id: str = Field(min_length=8, max_length=128, pattern=r"^[\w:.-]+$")
