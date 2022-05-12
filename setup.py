from setuptools import setup, find_packages

setup(
    name="web-requester",
    version=0.2,
    author="Jose Alberto Varona Labrada",
    author_email="jovalab92@gmail.com",
    description="HTTP sync / async python (>=3.6) library that works with requests and aiohttp libraries",
    python_requires=">=3.6",
    url="https://github.com/JoseVL92/web-requester",
    download_url="https://github.com/JoseVL92/web-requester/archive/refs/tags/v0.2.tar.gz",
    packages=find_packages(),
    data_files=[
        ("", ["LICENSE.txt", "README.md"])
    ],
    install_requires=['aiohttp', 'requests'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
    license='MIT',
    keywords=['http', 'asynchronous', 'request']
)
