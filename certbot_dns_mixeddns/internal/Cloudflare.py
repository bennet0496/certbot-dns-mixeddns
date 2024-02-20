from typing import Optional

import CloudFlare
from certbot.plugins import dns_common


class CloudflareClient(object):
    def __init__(self, api_email: Optional[str] = None, api_key: Optional[str] = None, api_token: Optional[str] = None):
        self.dns_record_id = None
        if api_email:
            # If an email was specified, we're using an email/key combination and not a token.
            # We can't use named arguments in this case, as it would break compatibility with
            # the Cloudflare library since version 2.10.1, as the `token` argument was used for
            # tokens and keys alike and the `key` argument did not exist in earlier versions.
            self.cloudflare = CloudFlare.CloudFlare(api_email, api_key)
        else:
            # If no email was specified, we're using just a token. Let's use the named argument
            # for simplicity, which is compatible with all (current) versions of the Cloudflare
            # library.
            self.cloudflare = CloudFlare.CloudFlare(token=api_token)

    def add_txt_record(self, domain: str, validation_name: str, validation: str, ttl: int) -> Optional[str]:
        base_names = set(dns_common.base_domain_name_guesses(domain))
        cf_zones = None
        try:
            cf_zones = self.cloudflare.zones.get()
        except CloudFlare.exceptions.CloudFlareAPIError:
            for z in base_names:
                params = {'name': z, 'per_page': 1}
                try:
                    cf_zones = self.cloudflare.zones.get(params=params)
                except CloudFlare.exceptions.CloudFlareAPIError:
                    pass

        zones = set([zone['name'] for zone in cf_zones])
        print(base_names, zones, cf_zones)
        if len(base_names & zones) > 0:
            zone_name = list(base_names & zones)[0]
            print(zone_name)
            # zone_info = self.cloudflare.zones.post(data={'jump_start': False, 'name': zone_name})
            zone_id = [z['id'] for z in cf_zones if z['name'] == zone_name][0]
            print(zone_id)

            dns_record = {
                'name': validation_name, 'type': 'TXT', 'content': validation, 'ttl': ttl
            }

            print(dns_record)
            res = self.cloudflare.zones.dns_records.post(zone_id, data=dns_record)
            print(res)
            self.dns_record_id = res['id']

            return self.dns_record_id
