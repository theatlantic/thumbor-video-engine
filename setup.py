from setuptools import setup, find_packages
from os import path

from io import open


CURR_DIR = path.abspath(path.dirname(__file__))


def get_long_description():
    with open(path.join(CURR_DIR, 'README.rst'), encoding='utf-8') as f:
        readme_rst = f.read()
        lines = readme_rst.split(u"\n")
        return u"\n".join(lines[10:])


setup(
    name='thumbor-video-engine',
    version='1.0.2',
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
    python_requires='>=2.7, <3',
    zip_safe=False)
