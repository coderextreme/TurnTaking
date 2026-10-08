from setuptools import setup, find_packages

setup(
    name="turnprog",
    version="1.0.0",
    description="Player progression engine in multi-client multi-server game environments based on Carlson (1986)",
    author="TurnProg Engine Authors",
    packages=find_packages(),
    python_requires=">=3.8",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Topic :: Games/Entertainment",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Distributed Computing",
    ],
)
