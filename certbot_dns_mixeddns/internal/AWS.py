from typing import Optional

import boto3
from certbot.plugins import dns_common



class Route53Client(object):
    def __init__(self, access_key_id: Optional[str] = None, secret_access_key: Optional[str] = None):
        self.r53 = boto3.client("route53", aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key)
        self.change_id = None

    def add_txt_record(self, domain: str, validation_name: str, validation: str, ttl: int) -> Optional[str]:
        base_names = set(["{}.".format(d) for d in dns_common.base_domain_name_guesses(domain)])
        r53_zones = []

        paginator = self.r53.get_paginator("list_hosted_zones")
        for page in paginator.paginate():
            for zone in page["HostedZones"]:
                if not zone["Config"]["PrivateZone"]:
                    r53_zones.append(zone)

        zones = set([zone['Name'] for zone in r53_zones])
        print(base_names, zones, r53_zones)
        if len(base_names & zones) > 0:
            zone_name = list(base_names & zones)[0]
            print(zone_name)
            # zone_info = self.cloudflare.zones.post(data={'jump_start': False, 'name': zone_name})
            zone_id = [z['Id'] for z in r53_zones if z['Name'] == zone_name][0]
            print(zone_id)

            response = self.r53.change_resource_record_sets(
                HostedZoneId=zone_id,
                ChangeBatch={
                    "Comment": "certbot-dns-mixeddns certificate validation",
                    "Changes": [
                        {
                            "Action": "CREATE",
                            "ResourceRecordSet": {
                                "Name": validation_name,
                                "Type": "TXT",
                                "TTL": ttl,
                                "ResourceRecords": [{"Value": '"{0}"'.format(validation)}],
                            }
                        }
                    ]
                }
            )
            print(response)
            self.change_id = response["ChangeInfo"]["Id"]
            return response["ChangeInfo"]["Id"]
