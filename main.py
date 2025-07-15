from parser import IndianAddressParser

def main():
    print("🚀 Starting Address Parser...")
    parser = IndianAddressParser()
    
    if parser.addresses_df is None:
        print("❌ Could not load addresses.csv")
        return

    print(f"📄 Total addresses: {len(parser.addresses_df)}")

    results = parser.parse_all_addresses()
    print(f"✅ Parsed {len(results)} addresses")

    parser.export_results_json(results)
    print("📤 Results written to parsed_output.json")

if __name__ == "__main__":
    main()
