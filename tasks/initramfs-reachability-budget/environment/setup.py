from setuptools import find_packages, setup

setup(
    name="q7-workspace",
    version="0.1.0",
    packages=find_packages(exclude=["tools*"]),
    entry_points={
        "console_scripts": [
            "drv_q7=drv_q7:main",
        ],
    },
)
