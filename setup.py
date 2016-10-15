from setuptools import setup, find_packages

setup(
    name='diffr',
    version='1.1',
    description='Diff and patch Python data structures',
    keywords=['diff', 'diffing', 'test'],
    author='Grahame Gardiner',
    author_email='grahamegee@gmail.com',
    url='https://github.com/grahamegee/differ',
    download_url='https://github.com/grahamegee/diffr/releases/tag/1.1',
    license='MIT',
    packages=find_packages(
        exclude=['examples', 'test', 'contrib']),
    install_requires=['blessings'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Testing'
    ])
