from setuptools import setup, find_packages

setup(
    name="http_requests",
    version=1.0,
    author="Jose Alberto Varona Labrada",
    author_email="jovalab92@gmail.com",
    description="HTTP sync / async python (>=3.6) library that works with both: requests and aiohttp, exploiting the best of each one",
    python_requires=">=3.6",
    project_urls={
        "Source Code": "https://github.com/JoseVL92/http-requests"
    },
    url="https://github.com/JoseVL92/http-requests",
    packages=find_packages(),
    package_data={
        '': [
            'LICENSE',
            'README.md'
        ],
    },
    install_requires=['requests', 'aiohttp'],
    classifiers=[
            'License :: MIT'
        ],
    license='MIT'
)
