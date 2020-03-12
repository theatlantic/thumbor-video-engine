from setuptools import setup, find_packages
from os import path

from io import open


CURR_DIR = path.abspath(path.dirname(__file__))


def read(rel_path):
    with open(path.join(CURR_DIR, rel_path), encoding='utf-8') as f:
        return f.read()


def get_long_description():
    readme_rst = read('README.rst')
    lines = readme_rst.split(u"\n")
    return u"\n".join(lines[12:])


def get_version():
    for line in read('src/thumbor_video_engine/__init__.py').splitlines():
        if line.startswith('__version__'):
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    else:
        raise RuntimeError("Unable to find version string.")


setup(
    name='thumbor-video-engine',
    version=get_version(),
    description='An engine and tools for manipulating videos with thumbor using ffmpeg',
    long_description=get_long_description(),
    long_description_content_type='text/x-rst',
    url='https://github.com/theatlantic/thumbor-video-engine',
    author='Frankie Dintino',
    author_email='fdintino@gmail.com',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development',
        'Environment :: Web Environment',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ],
    packages=find_packages('src'),
    package_dir={'': 'src'},
    install_requires=['thumbor'],
    zip_safe=False)
