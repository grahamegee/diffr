from setuptools import setup, find_packages

setup(
    name='differ',
    version='0.1',
    description='Differ for Python objects',
    classifiers=[],
    keywords='',
    author='Grahame Gardiner',
    author_email='',
    license='',
    packages=find_packages(
        exclude=['examples', 'test', 'contrib']),
    package_data={},
    install_requires=['blessings'],
    entry_points={},
    scripts=[])
