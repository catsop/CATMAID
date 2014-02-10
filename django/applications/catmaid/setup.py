import os
from setuptools import setup

README = open(os.path.join(os.path.dirname(__file__), 'README.rst')).read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='catmaid',
    version='0.24',
    package_dir={'':'../'},
    packages=['catmaid'],
    include_package_data=True,
    license='GPL3 License',
    description='Collaborative Annotation Toolkit for Massive Amounts of Image Data',
    long_description=README,
    url='https://github.com/acardona/CATMAID',
    author='Tom Kazimiers',
    author_email='tom@voodoo-arts.net',
    classifiers=[],
)
