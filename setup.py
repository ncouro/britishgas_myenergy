#!/usr/bin/env python

from setuptools import setup

setup(name='myenergy_download',
      version='1.0',
      description='Download energy data from a British Gas myenergy account (smart meters)',
      author='Nic Couro',
      packages=[
          'britishgas_myenergy'],
      install_requires=[
          'lxml',
          'gql',
          'requests'],
      entry_points = {
          'console_scripts': ['download_myenergy=britishgas_myenergy.fetch:main'],
      }
      )
