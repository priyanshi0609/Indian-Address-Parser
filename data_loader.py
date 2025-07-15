# Loads CSV files and prepares lookups
import pandas as pd
from config import logger

def load_datasets():
    try:
        addresses_df = pd.read_csv("addresses.csv")
        pin_df = pd.read_csv("pincodes.csv")
        pin_df['Pincode'] = pin_df['Pincode'].astype(str)

        city_df = pd.read_csv("Cities_Towns_District_State_India.csv")
        city_df.columns = [col.strip() for col in city_df.columns]
        city_df.dropna(subset=["City/Town", "District", "State/Union territory*"], inplace=True)

        city_lookup = {
            row["City/Town"].strip().lower(): {
                "district": row["District"].strip(),
                "state": row["State/Union territory*"].strip()
            }
            for _, row in city_df.iterrows()
        }

        pin_lookup = {
            row['Pincode']: {
                'city': row['City'],
                'district': row['District'],
                'state': row['State']
            }
            for _, row in pin_df.iterrows()
        }

        logger.info("All datasets loaded successfully.")
        return addresses_df, pin_df, city_lookup, pin_lookup

    except Exception as e:
        logger.error(f"Dataset load error: {e}")
        return None, None, {}, {}
