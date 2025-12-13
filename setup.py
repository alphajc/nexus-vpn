#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="nexus-vpn",
    version="0.1.0",
    author="Jerry",
    author_email="jerry@example.com",
    description="一键部署 VLESS-Reality + IKEv2 VPN 的综合代理工具",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/alphajc/nexus-vpn",
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Internet :: Proxy Servers",
        "Topic :: System :: Networking",
    ],
    python_requires=">=3.8",
    install_requires=[
        "click>=8.1.0",
        "rich>=13.0.0",
        "qrcode>=7.4.0",
        "jinja2>=3.1.0",
    ],
    entry_points={
        "console_scripts": [
            "nexus-vpn=nexus_vpn.cli:cli",
        ],
    },
    include_package_data=True,
    keywords=["vpn", "proxy", "vless", "reality", "ikev2", "xray", "strongswan"],
)
