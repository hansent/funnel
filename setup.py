from distutils.core import setup

setup(
    name = 'funnel',
    version = '0.0.2',
    author = 'Thomas Hansen',
    author_email = 'thomas.hansen@gmail.com',
    packages = ['funnel', 'funnel.db', 'funnel.handlers', 'funnel.util'],
    description = 'flask inspired micro framework for tornado.',
    long_description = open('README.md').read(),
    install_requires = open('requirements.txt').readlines(),
)
