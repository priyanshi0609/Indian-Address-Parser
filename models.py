# ParsedAddress dataclass

from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class ParsedAddress:
    care_of: Optional[str] = None
    house_number: Optional[str] = None
    building_name: Optional[str] = None
    street: Optional[str] = None
    locality: Optional[str] = None
    landmark: Optional[str] = None
    city: Optional[str] = None
    village: Optional[str] = None
    district: Optional[str] = None
    subdistrict: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None

    def to_dict(self) -> Dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}
