from setuptools import setup, find_packages

setup(
    name="http_requests",
    version=0.1,
    author="Jose Alberto Varona Labrada",
    author_email="jovalab92@gmail.com",
    description="HTTP sync / async python (>=3.6) library that works with requests and aiohttp libraries, exploiting the best of each one",
    python_requires=">=3.6",
    url="https://github.com/JoseVL92/http-requests",
    download_url="https://github.com/JoseVL92/http-requests/archive/v_01.tar.gz",
    packages=find_packages(),
    data_files=[
        ("", ["LICENSE.txt", "README.md"])
    ],
    install_requires=['requests', 'aiohttp'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    license='MIT',
    keywords=['http', 'asynchronous', 'request']
)
