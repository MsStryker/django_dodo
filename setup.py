import os
from setuptools import setup, find_packages

from django_dodo import __version__


with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
    README = readme.read()


setup(
    name='Django Dodo',
    version=__version__,
    description='Django Admin Email Utility',
    long_description=README,
    author='Morgyn Stryker',
    author_email='hey@morgynstryker.com',
    url='https://github.com/MsStryker/django_dodo',
    license='MIT',
    packages=find_packages(exclude=['tests', 'tests.*']),
    install_requires=[
        'django>=1.11',
        'django-colorfield',
        'django-sortedm2m',
    ],
    extras_require={
        'test': [
            'factory_boy',
        ]
    },
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 1.11',
        'Framework :: Django :: 2.0',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: WWW/HTTP',
    ],
)
