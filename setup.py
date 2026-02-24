from setuptools import setup, find_packages

setup(
    name='football-alert',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Click',
        # requests: used for querying the *local* mock server (stdlib alternative possible but retained for simplicity)
        'requests',
        'rich',  # For live-updating terminal dashboard
    ],
    entry_points='''
        [console_scripts]
        football-alert=football_alert.cli:main
    ''',
)