# coding: utf-8
import os, re
from setuptools import setup, find_packages, find_namespace_packages

with open(os.path.join("pkvenv", "__init__.py"), encoding="utf8") as f:
  version = re.search(r'__version__ = "(.*?)"', f.read()).group(1)

setup(
  name='pkvenv',
  version=version,
  python_requires='>=3.6',
  description='Pack your Virtualenv to anywhere.',
  url='http://gitlab.testplus.cn/sandin/pkvenv',
  author='lds2012',
  author_email='lds2012@gmail.com',
  license='Apache License 2.0',
  include_package_data=True, 
  packages=find_namespace_packages(include=['pkvenv.*', "pkvenv"]),
  entry_points = {
      'console_scripts': [
          'pkvenv = pkvenv.main:main'
      ]
  },
  install_requires=[
    "requests"
  ],
  zip_safe=False)
