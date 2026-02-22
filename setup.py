from setuptools import setup, find_packages

setup(
    name="ags",
    version="0.1.0",
    description="Agent Services for PDF processing and other utilities",
    author="AGS Team",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "requests>=2.28.0",
    ],
    entry_points={
        "console_scripts": [
            "gpu-infra=ags.gpu_infra.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
    ],
) 