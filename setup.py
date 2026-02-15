from setuptools import setup

setup(
    name="oops-cli",
    version="0.1.0",
    description="Your command-line error memory bank. Never Google the same error twice.",
    py_modules=["oops_cli"],
    install_requires=["click>=8.0"],
    entry_points={"console_scripts": ["oops=oops_cli:cli"]},
    python_requires=">=3.8",
    license="MIT",
    classifiers=[
        "Environment :: Console",
        "Topic :: Software Development",
        "Programming Language :: Python :: 3",
    ],
)
