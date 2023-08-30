import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="zoro-dl",
    version="1.0.0",
    author="aditya76-git",
    author_email="cdr.aditya.76@gmail.com",
    description="ZORO-DL - Download DUAL-AUDIO Multi SUBS Anime from ZORO",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/aditya76-git/zoro-dl",
    project_urls={
        "Tracker": "https://github.com/aditya76-git/zoro-dl/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "requests",
    ],
    packages=setuptools.find_packages(),
    python_requires=">=3.6",
)
