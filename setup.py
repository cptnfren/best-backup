"""
Setup script for bbackup package.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

setup(
    name="bbackup",
    version="1.0.0",
    description="Docker Backup Tool with Rich TUI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Linux Tools Project",
    packages=find_packages(),
    install_requires=[
        "rich>=13.7.0",
        "pyyaml>=6.0.1",
        "docker>=7.0.0",
        "click>=8.1.7",
        "paramiko>=3.4.0",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "bbackup=bbackup.cli:cli",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: System :: Archiving :: Backup",
    ],
)
