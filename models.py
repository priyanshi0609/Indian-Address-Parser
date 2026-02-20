from dataclasses import dataclass, field
from typing import Dict, Optional, List


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

    # 🔥 NEW FIELDS
    confidence_score: float = 0.0
    validation_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """
        Convert parsed address to dictionary.
        Keeps confidence + validation info.
        Removes only None fields (except metadata).
        """
        result = {}

        for key, value in self.__dict__.items():
            if key in ["confidence_score", "validation_errors"]:
                result[key] = value
            elif value is not None:
                result[key] = value

        return result