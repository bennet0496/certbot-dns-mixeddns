import configparser
import json
import logging
import re
import time
from typing import List, Callable, Optional, Dict, Mapping

from dns import resolver

from certbot import errors
from certbot import interfaces
from certbot.plugins import dns_common

from .internal.Cloudflare import CloudflareClient
from .internal.AWS import Route53Client

logger = logging.getLogger(__name__)

CF_ACCOUNT_URL = 'https://dash.cloudflare.com/?to=/:account/profile/api-tokens'


# @zope.interface.implementer(interfaces.IAuthenticator)
# @zope.interface.provider(interfaces.IPluginFactory)
class Authenticator(dns_common.DNSAuthenticator):
    """DNS Authenticator for ISPConfig

    This Authenticator uses the ISPConfig Remote REST API to fulfill a dns-01 challenge.
    """

    description = "Obtain certificates using a DNS TXT record (if you are using ISPConfig for DNS)."
    ttl = 60

    credentials: configparser.ConfigParser | None

    def __init__(self, *args, **kwargs):
        super(Authenticator, self).__init__(*args, **kwargs)
        self.credentials = None
        self.providers: Dict[str, List[str]] = {}
        self._provider_class: Dict[str, any] = {}

    @classmethod
    def add_parser_arguments(cls, add: Callable[..., None],
                             default_propagation_seconds: int = 10) -> None:
        super().add_parser_arguments(add, default_propagation_seconds)
        add('credentials', help='Cloudflare credentials INI file.')

    def more_info(self):  # pylint: disable=missing-docstring,no-self-use
        return (
                "This plugin configures a DNS TXT record to respond to a dns-01 challenge using "
                + "the appropriate provider API in a mixed DNS environment."
        )

    def _setup_credentials(self):
        filename = self.conf("credentials")

        self.credentials = configparser.ConfigParser()
        print(self.credentials.read_file(open(filename)))
        print(filename, self.credentials.sections())

    def _perform(self, domain, validation_name, validation):
        guesses = dns_common.base_domain_name_guesses(domain)
        print(domain, validation_name, validation, guesses)
        for dom in guesses:
            if dom in self.credentials.sections():
                # Use configured provider
                print("domain in config")
                break

            print("resolving {}:NS".format(dom))
            ans = resolver.resolve(dom, "NS", raise_on_no_answer=False).rrset
            print(ans)
            if ans is not None:
                ns_records = [dns_record.to_text() for dns_record in ans]
                print(ns_records)
                self._detect_providers(domain, ns_records)
                break

        for provider in self._get_providers(domain):
            provider.add_txt_record(
                domain, validation_name, validation, self.ttl
            )

    def _cleanup(self, domain, validation_name, validation):
        # self._get_ispconfig_client().del_txt_record(
        #     domain, validation_name, validation, self.ttl
        # )
        pass

    def _detect_providers(self, domain: str, nameservers: List[str]):
        if domain not in self.providers.keys():
            self.providers[domain] = []
        for ns in nameservers:
            if ns in self.credentials.sections():
                try:
                    pstrings = [p.strip(' ') for p in self.credentials[ns]['provider'].split(',')]
                    for pstring in pstrings:
                        if pstring not in self.providers:
                            self.providers[domain].append(pstring)
                except IndexError:
                    print("No provider for NS {}, skipping".format(ns))
            elif ns.endswith("ns.cloudflare.com."):
                if 'cloudflare' not in self.credentials.sections():
                    print("Cloudflare not configured")
                elif 'cloudflare' not in self.providers:
                    self.providers[domain].append('cloudflare')
            elif re.match(r"ns-[0-9]+\.awsdns-[0-9]+\.(?:com|net|org|co\.uk)\.", ns):
                if 'route53' not in self.credentials.sections():
                    print("Route53 not configured")
                elif 'route53' not in self.providers:
                    self.providers[domain].append('route53')
            else:
                print("Unknown Provider for NS {}".format(ns))

    def _get_providers(self, domain: str):

        for provider in self.providers[domain]:
            if provider == "cloudflare" or self.credentials[provider].get('type') == "cloudflare":
                token = self.credentials[provider].get('api_token')
                email = self.credentials[provider].get('api_email')
                key = self.credentials[provider].get('api_key')
                if token:
                    if email or key:
                        raise errors.PluginError('{}: dns_cloudflare_email and dns_cloudflare_api_key are '
                                                 'not needed when using an API Token'
                                                 .format(self.conf("credentials")))
                elif email or key:
                    if not email:
                        raise errors.PluginError('{}: dns_cloudflare_email is required when using a Global '
                                                 'API Key. (should be email address associated with '
                                                 'Cloudflare account)'.format(self.conf("credentials")))
                    if not key:
                        raise errors.PluginError('{}: dns_cloudflare_api_key is required when using a '
                                                 'Global API Key. (see {})'
                                                 .format(self.conf("credentials"), CF_ACCOUNT_URL))
                else:
                    raise errors.PluginError('{}: Either dns_cloudflare_api_token (recommended), or '
                                             'dns_cloudflare_email and dns_cloudflare_api_key are required.'
                                             ' (see {})'.format(self.conf("credentials"), CF_ACCOUNT_URL))

                if provider not in self._provider_class.keys():
                    if token:
                        self._provider_class[provider] = CloudflareClient(api_token=token)
                    else:
                        self._provider_class[provider] = CloudflareClient(api_email=email, api_key=key)

            elif provider == "route53" or self.credentials[provider].get('type') == "route53":
                if provider not in self._provider_class.keys():
                    self._provider_class[provider] = Route53Client(self.credentials[provider].get("access_key_id"),
                                                                   self.credentials[provider].get("secret_access_key"))
        return [c for (p, c) in self._provider_class.items() if p in self.providers[domain]]
