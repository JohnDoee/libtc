import os

from setuptools import find_packages, setup

from libtc import __version__


def readme():
    with open("README.rst") as f:
        return f.read()


setup(
    name="libtc",
    version=__version__,
    url="https://github.com/JohnDoee/libtc",
    author="Anders Jensen",
    author_email="jd@tridentstream.org",
    description="Bittorrent client library",
    long_description=readme(),
    long_description_content_type="text/x-rst",
    license="MIT",
    packages=find_packages(),
    install_requires=[
        "deluge-client==1.9.0",
        "pytz==2020.1",
        "requests==2.23.0",
    ],
    tests_require=[
        "pytest==5.4.2",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
)
