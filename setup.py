import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="wiperf_poller",
    version="0.0.1",
    author="Nigel Bowden",
    author_email="wifinigel@gmail.com",
    description="Poller for the wiperf utlity",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/wifinigel/wiperf_poller",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)