import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="wiperf_poller",
    version="0.1.23",
    author="Nigel Bowden",
    author_email="wifinigel@gmail.com",
    description="Poller for the wiperf utlity",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/wifinigel/wiperf_poller",
    packages=setuptools.find_packages(),
    install_requires=['speedtest-cli', 'influxdb', 'influxdb_client'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: Free for non-commercial use",
        "Operating System :: POSIX :: Linux",
    ],
    include_package_data=True,
    python_requires='>=3.6',
    entry_points={
        "console_scripts": [
            "wiperf_poller=wiperf_poller.__main__:main",
        ]
    },
)