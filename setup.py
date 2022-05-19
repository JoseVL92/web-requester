from setuptools import setup, find_packages

setup(
    name="web-requester",
    version=0.3,
    author="Jose Alberto Varona Labrada",
    author_email="jovalab92@gmail.com",
    description="Easily and efficiently perform concurrent http requests",
    python_requires=">=3.8",
    url="https://github.com/JoseVL92/web-requester",
    download_url="https://github.com/JoseVL92/web-requester/archive/refs/tags/v0.3.tar.gz",
    packages=find_packages(),
    data_files=[
        ("", ["LICENSE.txt", "README.md"])
    ],
    install_requires=['aiohttp', 'requests'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
    license='MIT',
    keywords=['http', 'asynchronous', 'request']
)
