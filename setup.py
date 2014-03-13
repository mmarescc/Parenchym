import os
import re
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.txt')).read()
CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()

requires = [x.rstrip() for x in
    open(os.path.join(here, 'requirements.txt')).readlines()
    if not x.startswith('-e')]
tests_requires = requires

from pprint import pprint; pprint(tests_requires)

setup(
    name='Parenchym',
    version='0.3',
    description='Parenchym Application Framework',
    long_description=README + '\n\n' + CHANGES,
    classifiers=[
        "Programming Language :: Python", "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
    ],
    author='Dirk Makowski',
    author_email='johndoe@example.com',
    url='http://parenchym.com',
    keywords='web pyramid pylons',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=requires,
    tests_require=tests_requires,
    test_suite="pym",
    entry_points="""\
      [paste.app_factory]
      main = pym:main
      [console_scripts]
      pym-init-db = pym.scripts.initialisedb:main
      pym = pym.scripts.pym:main
      """,
)
