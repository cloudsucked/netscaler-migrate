## NEEDS "Liberate the Zone" Account level entitlement to work
## NEEDS to be an "Enterprise Account" or else limited to 50 pending zones
## SET the following Environment Variables:
## CLOUDFLARE_EMAIL: Your Cloudflare Email
## CLOUDFLARE_API_KEY: Your Cloudflare API Key
## CLOUDFLARE_ACCOUNT_ID: Your Cloudflare Account ID


import httpx
import os
import json


def load_existing_zones(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as infile:
            try:
                data = json.load(infile)
            except:
                data = []
            return data
    return []


def read_file(file_path):
    existing_zones = load_existing_zones('zones_output.json')
    zones = []
    a_records = []
    aaaa_records = []
    cname_records = []
    with open(file_path, 'r') as file:
        for line in file:
            ## Create new Zones where SOA records existed
            if line.startswith("add dns soaRec"):
                words = line.split()
                if len(words) >= 4:
                    zone_name = words[3]
                    print(f"Zone: {zone_name}")
                    if not any(zone['zone_name'] == zone_name for zone in existing_zones):
                        existing_zone_id = zone_exists(zone_name)
                        if not existing_zone_id:
                            print(f"Zone does not exist: {zone_name}")
                            zone_id = create_zone(zone_name)
                            if zone_id:
                                zones.append({"zone_name": zone_name, "zone_id": zone_id})
                        else:
                            print(f"Zone already exists: {zone_name}")
                            existing_zones.append({"zone_name": zone_name, "zone_id": existing_zone_id})
            ## Do nothing where NS records existed
            if line.startswith("add dns nsRec"):
                words = line.split()
                if len(words) >= 5:
                    print(f"domain: {words[3]} --> nameserver: {words[4]}")
            ## Create new A record for addRec
            if line.startswith("add dns addRec"):
                words = line.split()
                if len(words) >= 5:
                    print(f"a-record: {words[3]} --> target: {words[4]}")
                    a_records.append({"name": words[3], "content": words[4], "type": "A"})
            ## Create new AAAA record for aaaaRec
            if line.startswith("add dns aaaaRec"):
                words = line.split()
                if len(words) >= 5:
                    print(f"aaaa-record: {words[3]} --> target: {words[4]}")
                    aaaa_records.append({"name": words[3], "content": words[4], "type": "AAAA"})
            ## Create new CNAME record for cnameRec
            if line.startswith("add dns cnameRec"):
                words = line.split()
                if len(words) >= 5:
                    print(f"cname: {words[3]} --> target: {words[4]}")
                    cname_records.append({"name": words[3], "content": words[4], "type": "CNAME"})
    parsed_file = {
        "zones": zones + existing_zones,
        "a_records": a_records,
        "aaaa_records": aaaa_records,
        "cname_records": cname_records
    }
    return parsed_file


def zone_exists(zone_name):
    url = f"https://api.cloudflare.com/client/v4/zones?account.id={cloudflare_account_id}&name={zone_name}"
    headers = {
        "Content-Type": "application/json",
        "X-Auth-Email": cloudflare_email,
        "X-Auth-Key": clouflare_api_key
    }
    response = httpx.get(url, headers=headers)
    if response.status_code == 200 and response.json().get('success'):
        result = response.json().get('result', {})
        if not result:
            return False
        zone_id = result[0].get('id')
        return zone_id
    else:
        print(f"Failed to check if zone exists: {zone_name}, Status Code: {response.status_code}, Response: {response.text}")
        return False
    

def create_zone(zone_name):
    url = "https://api.cloudflare.com/client/v4/zones"
    headers = {
        "Content-Type": "application/json",
        "X-Auth-Email": cloudflare_email,
        "X-Auth-Key": clouflare_api_key
    }
    data = {
        "account": {"id": cloudflare_account_id},
        "name": zone_name,
        "jump_start": False,
        "type": "full"    }
    response = httpx.post(url, headers=headers, json=data)
    if response.status_code == 200 and response.json().get('success'):
        result = response.json().get('result', {})
        zone_id = result.get('id')
        print(f"Successfully created zone: {zone_name}, Zone ID: {zone_id}")
        return zone_id
    else:
        print(f"Failed to create zone: {zone_name}, Status Code: {response.status_code}, Response: {response.text}")
        return None


def write_zones_to_file(zones):
    output_file = 'zones_output.json'
    with open(output_file, 'w') as outfile:
        json.dump(zones, outfile, indent=4)        
    
    return None


def add_record(record, zones):
    print(f"Adding record: {record}")
    matched_zones = []
    for zone in zones:
        if zone['zone_name'] in record['name']:
            matched_zones.append(zone)
    matched_zones.sort(key=lambda x: len(x['zone_name']), reverse=True)
    if len(matched_zones) > 0:
        print(matched_zones[0])

        url = f"https://api.cloudflare.com/client/v4/zones/{matched_zones[0].get('zone_id')}/dns_records"
        headers = {
            "Content-Type": "application/json",
            "X-Auth-Email": cloudflare_email,
            "X-Auth-Key": clouflare_api_key
        }
        data = {
            "comment": "Added via Python script",
            "name": record['name'],
            "content": record['content'],
            "proxied": False,
            "type": record['type']
            }
        response = httpx.post(url, headers=headers, json=data)
        if response.status_code == 200 and response.json().get('success'):
            result = response.json().get('result', {})
            print(f"Successfully created record: {record['name']}, Record ID: {result.get('id')}")
            return None
        else:
            print(f"Failed to create record: {record['name']}, Status Code: {response.status_code}, Response: {response.text}")
            return None
    else:
        print(f"Failed to find zone for record: {record['name']}")
        return None


if __name__ == "__main__":
    cloudflare_account_id = os.getenv('CLOUDFLARE_ACCOUNT_ID')
    cloudflare_email = os.getenv('CLOUDFLARE_EMAIL')
    clouflare_api_key = os.getenv('CLOUDFLARE_API_KEY')

    file_path = 'data'
    parsed_file = read_file(file_path)
    zones = parsed_file.get('zones')
    write_zones_to_file(zones)

    for a_record in parsed_file.get('a_records'):
        add_record(a_record, zones)

    for aaaa_record in parsed_file.get('aaaa_records'):
        add_record(aaaa_record, zones)

    for cname_record in parsed_file.get('cname_records'):
        add_record(cname_record, zones)

