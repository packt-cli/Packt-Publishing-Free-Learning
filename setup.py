from setuptools import find_packages, setup

package_version = '1.0.3'

requirements = [
    'beautifulsoup4==4.6.3',
    'click==7.0',
    'google-api-python-client==1.6.3',
    'requests==2.20.0',
    'python-slugify==1.2.6'
]

dev_requirements = [
    'mccabe==0.6.1',
    'pycodestyle==2.4.0',
    'pyflakes==2.0.0',
    'pylama==7.6.5'
]

setup(
    name='packt',
    version=package_version,
    license='MIT',
    description='Script for grabbing daily Packt Free Learning ebooks',
    author='Łukasz Uszko',
    author_email='lukasz.uszko@gmail.com',
    url='https://github.com/luk6xff/Packt-Publishing-Free-Learning',
    package_dir={'': 'src'},
    packages=find_packages('src'),
    py_modules=['packtPublishingFreeEbook', 'api'],
    install_requires=requirements,
    extras_require={'dev': dev_requirements},
    entry_points={
        'console_scripts': [
            'packt-cli = packtPublishingFreeEbook:packt_cli',
        ],
    },
    download_url='https://github.com/luk6xff/Packt-Publishing-Free-Learning/archive/v1.0.3.tar.gz'
)
