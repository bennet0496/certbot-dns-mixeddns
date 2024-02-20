import os
import sys

from setuptools import find_packages
from setuptools import setup

version = '0.0.1'

install_requires = [
    'setuptools>=68.2.0',
    'boto3>=1.34.45',
    'cloudflare>=2.19.0',
    'dnspython>=2.6.1'
]

if os.environ.get('SNAP_BUILD'):
    install_requires.append('packaging')
else:
    install_requires.extend([
        # We specify the minimum acme and certbot version as the current plugin
        # version for simplicity. See
        # https://github.com/certbot/certbot/issues/8761 for more info.
        f'acme>={version}',
        f'certbot>={version}',
    ])

docs_extras = [
    'Sphinx>=1.0',  # autodoc_member_order = 'bysource', autodoc_default_flags
    'sphinx_rtd_theme',
]

test_extras = [
    'pytest',
]

setup(
    name='certbot-dns-mixeddns',
    version=version,
    description="DNS Authenticator for Domain across multiple DNS providers",
    url='https://github.com/bennet0496/certbot-dns-mixeddns',
    author="Bennet Becker",
    author_email='dev@bennet.cc',
    license='MIT',
    python_requires='>=3.10',
    classifiers=[
        'Development Status :: 1 - Planning',
        'Environment :: Plugins',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Security',
        'Topic :: System :: Installation/Setup',
        'Topic :: System :: Networking',
        'Topic :: System :: Systems Administration',
        'Topic :: Utilities',
    ],

    packages=find_packages(),
    include_package_data=True,
    install_requires=install_requires,
    # extras_require={
    #     'docs': docs_extras,
    #     'test': test_extras,
    # },
    entry_points={
        'certbot.plugins': [
            'dns-mixeddns = certbot_dns_mixeddns.dns_mixeddns:Authenticator',
        ],
    },
)
