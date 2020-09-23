import os
from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as f:
    long_description = f.read()

package_version = '1.5.3'

requirements = [
    'click==7.1.1',
    'google-api-python-client==1.8.0',
    'oauth2client==4.1.3',
    'requests==2.23.0',
    'python-slugify==4.0.0'
]

dev_requirements = [
    'bumpversion==0.5.3',
    'mccabe==0.6.1',
    'pycodestyle==2.5.0',
    'pyflakes==2.2.0',
    'pylama==7.7.1',
    'twine<2; python_version < "3.6"',
    'twine==3.1.1; python_version >= "3.6"'
]

setup(
    name='packt',
    version=package_version,
    packages=find_packages(),
    license='MIT',
    description='Script for grabbing daily Packt Free Learning ebooks',
    author='Łukasz Uszko',
    author_email='lukasz.uszko@gmail.com',
    url='https://github.com/luk6xff/Packt-Publishing-Free-Learning',
    long_description=long_description,
    long_description_content_type='text/markdown',
    py_modules=['packt'],
    install_requires=requirements,
    extras_require={'dev': dev_requirements},
    entry_points={
        'console_scripts': [
            'packt-cli = packt.packtPublishingFreeEbook:packt_cli',
        ],
    },
    download_url='https://github.com/luk6xff/Packt-Publishing-Free-Learning/archive/v1.5.3.tar.gz',
    classifiers=[
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8'
    ]
)
